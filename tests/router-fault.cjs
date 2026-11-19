// Run inside a disposable, network-disabled official 9Router with an empty tmpfs.
const assert = require("node:assert/strict");
const http = require("node:http");
const { setTimeout: sleep } = require("node:timers/promises");

const calls = [];
const stub = http.createServer(async (request, response) => {
  let raw = "";
  for await (const part of request) raw += part;
  const { model } = JSON.parse(raw);
  calls.push(model);
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
}

main().catch((error) => { console.error(error.message); process.exitCode = 1; })
  .finally(() => stub.close());
