// Run inside a disposable, network-disabled official 9Router with an empty tmpfs.
const assert = require("node:assert/strict");
const http = require("node:http");
const { setTimeout: sleep } = require("node:timers/promises");

const calls = [];
let receivedToolResult = false;

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
  if (model === "secondary") {
    receivedToolResult = body.messages.some((message) => message.role === "tool");
    const message = { role: "assistant", content: receivedToolResult ? "cerulean" : "fixture-ok" };
    let finish = "stop";
    if (body.tools?.length && !receivedToolResult) {
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
  async function comboRequest(model, stream) {
    return call("/v1/chat/completions", {
      method: "POST", headers: { Authorization: "Bearer " + combo.key },
      body: { model, messages, stream },
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
}

main().catch((error) => { console.error(error.message); process.exitCode = 1; })
  .finally(() => stub.close());
