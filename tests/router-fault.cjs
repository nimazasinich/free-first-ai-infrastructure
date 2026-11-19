// Run inside a disposable, network-disabled official 9Router with an empty tmpfs.
const assert = require("node:assert/strict");
const http = require("node:http");
const { setTimeout: sleep } = require("node:timers/promises");

const calls = [];
let receivedToolResult = false;
let receivedToolDefinitions = false;

function streamFrame(model, delta, finishReason = null) {
  return "data: " + JSON.stringify({
    id: "chatcmpl-fixture", object: "chat.completion.chunk", model,
    choices: [{ index: 0, delta, finish_reason: finishReason }],
  }) + "\n\n";
}
const stub = http.createServer(async (request, response) => {
  let raw = "";
  for await (const part of request) raw += part;
  const body = JSON.parse(raw);
  const { model } = body;
  calls.push(model);
  if (model === "partial") {
    response.writeHead(200, { "Content-Type": "text/event-stream" });
    response.write(streamFrame(model, { content: "partial-output" }));
    await sleep(300);
    response.destroy();
    return;
  }
  if (model === "secondary" || model === "text-only") {
    receivedToolDefinitions = Array.isArray(body.tools) && body.tools.length > 0;
    receivedToolResult = body.messages.some((message) => message.role === "tool");
    const message = { role: "assistant", content: receivedToolResult ? "cerulean" : "fixture-ok" };
    let finish = "stop";
    if (model === "secondary" && body.tools?.length && !receivedToolResult) {
      message.content = null;
      message.tool_calls = [{
        id: "call_fixture", type: "function",
        function: { name: "lookup", arguments: '{"item":"sky"}' },
      }];
      finish = "tool_calls";
    }
    if (body.stream) {
      response.writeHead(200, { "Content-Type": "text/event-stream" });
      response.write(streamFrame(model, message));
      response.end(streamFrame(model, {}, finish) + "data: [DONE]\n\n");
    } else {
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end(JSON.stringify({
        id: "chatcmpl-fixture", object: "chat.completion", model,
        choices: [{ index: 0, message, finish_reason: finish }],
        usage: { prompt_tokens: 2, completion_tokens: 2, total_tokens: 4 },
      }));
    }
    return;
  }
  const status = model === "limited" ? 429 : model === "raw-unavailable" ? 503 : 500;
  response.writeHead(status, {
    "Content-Type": "application/json",
    "Retry-After": "5",
  });
  response.end(JSON.stringify({
    error: {
      message: status === 429 ? "Fixture rate limit" : "Fixture unavailable",
      type: status === 429 ? "rate_limit_error" : "server_error",
    },
  }));
});

async function call(path, { method = "GET", body, headers = {} } = {}) {
  return fetch("http://127.0.0.1:20128" + path, {
    method, headers: { "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(10000),
    redirect: "error",
  });
}

async function main() {
  assert.equal(process.env.FREE_FIRST_FIXTURE, "1");
  for (let attempt = 0; attempt < 20; attempt++) {
    const response = await call("/api/health").catch(() => null);
    if (response?.ok) break;
    if (attempt === 19) throw Error("Fixture gateway did not start");
    await sleep(500);
  }
  await new Promise((resolve) => stub.listen(18121, "127.0.0.1", resolve));
  const login = await call("/api/auth/login", {
    method: "POST", body: { password: process.env.INITIAL_PASSWORD },
  });
  assert.equal(login.status, 200);
  const cookie = login.headers.get("set-cookie").split(";")[0];
  async function admin(path, body, method = "POST") {
    const response = await call(path, { method, body, headers: { Cookie: cookie } });
    assert.ok(response.ok, `${method} ${path}: ${response.status}`);
    return response.json();
  }
  const { node } = await admin("/api/provider-nodes", {
    name: "Fixture", prefix: "fixture", apiType: "chat", baseUrl: "http://127.0.0.1:18121/v1",
  });
  await admin("/api/providers", {
    provider: node.id, name: "Fixture", apiKey: "synthetic-local-upstream",
  });
  const { key, id } = await admin("/api/keys", { name: "isolated-fault-probe" });
  await admin("/api/keys/" + id, {
    access: { restricted: true, allow: ["fixture/limited", "fixture/unavailable", "fixture/raw-unavailable"] },
  }, "PUT");

  async function generation(model) {
    const response = await call("/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: "Bearer " + key },
      body: { model, messages: [{ role: "user", content: "fixture" }], stream: false },
    });
    await response.text();
    return { status: response.status, retryAfter: response.headers.get("retry-after") };
  }
  assert.equal((await generation("fixture/forbidden")).status, 403);
  assert.deepEqual(calls, []);
  const limited = await generation("fixture/limited");
  assert.deepEqual(calls, ["limited"]);
  // This release can report 503 when the sole seat enters cooldown.
  assert.ok([429, 503].includes(limited.status));
  const cooldown = await generation("fixture/limited");
  assert.ok([429, 503].includes(cooldown.status));
  assert.ok(Number(cooldown.retryAfter) > 0);
  assert.deepEqual(calls, ["limited"]);
  const unavailable = await generation("fixture/unavailable");
  assert.ok([500, 503].includes(unavailable.status));
  assert.deepEqual(calls, ["limited", "unavailable"]);
  const raw = await generation("fixture/raw-unavailable");
  assert.equal(raw.status, 503);
  assert.deepEqual(calls, ["limited", "unavailable", ...Array(4).fill("raw-unavailable")]);
  console.log(JSON.stringify({ limited, cooldown, unavailable, raw, upstreamCalls: calls.length }));

  await admin("/api/combos", {
    name: "fixture-fallback", models: ["fixture/terminal", "fixture/secondary"],
  });
  await admin("/api/combos", {
    name: "fixture-partial", models: ["fixture/partial", "fixture/secondary"],
  });
  const combo = await admin("/api/keys", { name: "isolated-combo-probe" });
  await admin("/api/keys/" + combo.id, {
    access: { restricted: true, allow: ["fixture-fallback", "fixture-partial"] },
  }, "PUT");
  const messages = [{ role: "user", content: "fixture" }];
  async function comboRequest(model, stream, options = {}) {
    return call("/v1/chat/completions", {
      method: "POST", headers: { Authorization: "Bearer " + combo.key },
      body: { model, messages, stream, ...options },
    });
  }
  const comboStart = calls.length;
  const directMember = await comboRequest("fixture/terminal", false);
  assert.equal(directMember.status, 403);
  await directMember.text();
  assert.equal(calls.length, comboStart);
  const fallback = await comboRequest("fixture-fallback", false);
  assert.equal(fallback.status, 200);
  assert.equal((await fallback.json()).choices[0].message.content, "fixture-ok");
  assert.deepEqual(calls.slice(comboStart), ["terminal", "secondary"]);

  const partial = await comboRequest("fixture-partial", true);
  assert.equal(partial.status, 200);
  const partialSSE = await partial.text();
  assert.match(partialSSE, /partial-output/);
  assert.match(partialSSE, /error|failed/);
  assert.deepEqual(calls.slice(comboStart), ["terminal", "secondary", "partial"]);
  console.log(JSON.stringify({ comboFallback: true, partialReplay: false, memberDenied: true }));

  await admin("/api/keys/" + id, {
    access: { restricted: true, allow: ["fixture/secondary"] },
  }, "PUT");
  const tool = { name: "lookup", description: "Fixture", input_schema: {
    type: "object", properties: { item: { type: "string" } },
  } };
  const anthropicHeaders = { "x-api-key": key, "anthropic-version": "2023-06-01" };
  function anthropic({ model = "fixture/secondary", input = messages, stream = false, headers = anthropicHeaders } = {}) {
    return call("/v1/messages", {
      method: "POST", headers,
      body: { model, messages: input, stream, max_tokens: 40, tools: [tool] },
    });
  }
  const anthropicStart = calls.length;
  for (const [options, expected] of [[{ headers: {} }, 401], [{ model: "fixture/denied" }, 403]]) {
    const response = await anthropic(options);
    assert.equal(response.status, expected);
    await response.text();
  }
  assert.equal(calls.length, anthropicStart);
  const use = await anthropic({ stream: true });
  assert.equal(use.status, 200);
  assert.match(use.headers.get("content-type"), /text\/event-stream/);
  const messageSSE = await use.text();
  assert.match(messageSSE, /tool_use/);
  assert.match(messageSSE, /message_stop/);

  const continuation = await anthropic({ input: [
    ...messages,
    { role: "assistant", content: [{ type: "tool_use", id: "call_fixture", name: "lookup", input: { item: "sky" } }] },
    { role: "user", content: [{ type: "tool_result", tool_use_id: "call_fixture", content: "cerulean" }] },
  ] });
  assert.equal(continuation.status, 200);
  assert.match(await continuation.text(), /cerulean/);
  assert.equal(receivedToolResult, true);
  assert.deepEqual(calls.slice(anthropicStart), ["secondary", "secondary"]);
  console.log(JSON.stringify({ anthropicToolSSE: true, anthropicContinuation: true, rejectedForwards: 0 }));

  const geminiStart = calls.length;
  const geminiBody = {
    contents: [{ role: "user", parts: [{ text: "fixture" }] }],
    generationConfig: { maxOutputTokens: 40 },
  };
  function gemini(model, action, headers = { Authorization: "Bearer " + key }, body = geminiBody) {
    return call("/v1beta/models/fixture/" + model + ":" + action, { method: "POST", headers, body });
  }
  const geminiCatalog = await call("/v1beta/models");
  assert.equal(geminiCatalog.status, 200);
  const staticModels = (await geminiCatalog.json()).models;
  assert.ok(staticModels.length > 1);
  const missing = await gemini("secondary", "generateContent", {});
  const denied = await gemini("denied", "generateContent");
  assert.equal(missing.status, 401);
  assert.equal(denied.status, 403);
  assert.equal(calls.length, geminiStart);
  await missing.text();
  await denied.text();
  const unary = await gemini("secondary", "generateContent");
  assert.equal(unary.status, 200);
  assert.equal((await unary.json()).candidates[0].content.parts[0].text, "fixture-ok");
  const geminiStream = await gemini("secondary", "streamGenerateContent?alt=sse");
  assert.equal(geminiStream.status, 200);
  assert.match(geminiStream.headers.get("content-type"), /text\/event-stream/);
  const geminiSSE = await geminiStream.text();
  assert.doesNotMatch(geminiSSE, /\[DONE\]/);
  const geminiEvents = geminiSSE.split("\n")
    .filter((line) => line.startsWith("data: "))
    .map((line) => JSON.parse(line.slice(6)));
  assert.ok(geminiEvents.some((event) =>
    event.candidates?.some((candidate) => candidate.content?.parts?.some((part) => part.text === "fixture-ok"))));
  assert.ok(geminiEvents.some((event) =>
    event.candidates?.some((candidate) => candidate.finishReason === "STOP")));
  assert.deepEqual(calls.slice(geminiStart), ["secondary", "secondary"]);
  const sdkHeader = await gemini("secondary", "generateContent", { "x-goog-api-key": key });
  assert.equal(sdkHeader.status, 401);
  await sdkHeader.text();
  assert.deepEqual(calls.slice(geminiStart), ["secondary", "secondary"]);
  const geminiTools = await gemini("secondary", "generateContent", undefined, {
    ...geminiBody,
    tools: [{ functionDeclarations: [{
      name: tool.name, description: tool.description, parameters: tool.input_schema,
    }] }],
    toolConfig: { functionCallingConfig: { mode: "ANY" } },
  });
  assert.equal(geminiTools.status, 200);
  const geminiToolResponse = await geminiTools.json();
  assert.equal(receivedToolDefinitions, false);
  assert.equal(geminiToolResponse.candidates[0].content.parts[0].text, "fixture-ok");
  assert.equal(geminiToolResponse.candidates[0].content.parts[0].functionCall, undefined);
  assert.deepEqual(calls.slice(geminiStart), ["secondary", "secondary", "secondary"]);
  console.log(JSON.stringify({
    geminiUnary: true, geminiSSE: true, geminiHeaderStatus: sdkHeader.status,
    geminiToolDefinitionsForwarded: false, staticGeminiCatalogUnscoped: true, rejectedForwards: 0,
  }));

  await admin("/api/combos", {
    name: "fixture-tool-fallback", models: ["fixture/tool-terminal", "fixture/secondary"],
  });
  await admin("/api/combos", {
    name: "fixture-unsafe-tool-fallback", models: ["fixture/text-terminal", "fixture/text-only"],
  });
  await admin("/api/keys/" + combo.id, {
    access: { restricted: true, allow: ["fixture-tool-fallback", "fixture-unsafe-tool-fallback"] },
  }, "PUT");
  const toolOptions = {
    tool_choice: "required",
    tools: [{
      type: "function",
      function: { name: tool.name, description: tool.description, parameters: tool.input_schema },
    }],
  };
  const toolStart = calls.length;
  const compatible = await comboRequest("fixture-tool-fallback", false, toolOptions);
  assert.equal(compatible.status, 200);
  const selected = await compatible.json();
  const generatedCall = selected.choices[0].message.tool_calls[0];
  assert.deepEqual(calls.slice(toolStart), ["tool-terminal", "secondary"]);
  assert.equal(selected.model, "secondary");
  assert.equal(selected.choices[0].finish_reason, "tool_calls");
  assert.equal(generatedCall.function.name, "lookup");
  assert.deepEqual(JSON.parse(generatedCall.function.arguments), { item: "sky" });
  const followStart = calls.length;
  const follow = await comboRequest("fixture-tool-fallback", false, {
    ...toolOptions,
    tool_choice: "none",
    messages: [
      ...messages,
      { role: "assistant", content: null, tool_calls: [generatedCall] },
      { role: "tool", tool_call_id: generatedCall.id, content: "cerulean" },
    ],
  });
  assert.equal(follow.status, 200);
  const followPayload = await follow.json();
  assert.equal(followPayload.model, "secondary");
  assert.equal(followPayload.choices[0].message.content, "cerulean");
  assert.equal(receivedToolResult, true);
  const continuations = calls.slice(followStart);
  assert.equal(continuations.at(-1), "secondary");
  assert.ok(continuations.length <= 2);
  if (continuations.length === 2) assert.equal(continuations[0], "tool-terminal");

  // This control reproduces why stock Combo needs a fail-closed capability gate.
  const unsafeStart = calls.length;
  const unsafe = await comboRequest("fixture-unsafe-tool-fallback", false, toolOptions);
  assert.equal(unsafe.status, 200);
  const downgraded = await unsafe.json();
  assert.deepEqual(calls.slice(unsafeStart), ["text-terminal", "text-only"]);
  assert.equal(receivedToolDefinitions, true);
  assert.equal(downgraded.model, "text-only");
  assert.equal(downgraded.choices[0].finish_reason, "stop");
  assert.equal(downgraded.choices[0].message.tool_calls, undefined);
  console.log(JSON.stringify({
    fallbackToolRoundTrip: true, fallbackReportedModel: selected.model ?? null,
    fallbackContinuationReportedModel: followPayload.model ?? null,
    fallbackContinuationAttempts: continuations.length, incompatibleToolFallbackObserved: true,
  }));
}

main().catch((error) => { console.error(error.message); process.exitCode = 1; })
  .finally(() => stub.close());
