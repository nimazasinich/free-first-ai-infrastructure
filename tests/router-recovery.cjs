// Run in an isolated, network-disabled router restored from a local clean snapshot.
const assert = require("node:assert/strict");
const { DatabaseSync } = require("node:sqlite");
const { setTimeout: sleep } = require("node:timers/promises");

const base = "http://127.0.0.1:20128";
const proxyHeaders = { "X-Forwarded-For": "192.0.2.20" };

async function main() {
  for (let attempt = 0; attempt < 25; attempt++) {
    const health = await fetch(base + "/api/health", { signal: AbortSignal.timeout(1000) }).catch(() => null);
    if (health?.status === 200) break;
    if (attempt === 24) throw Error("Recovery container health check failed");
    await sleep(500);
  }

  const database = new DatabaseSync("/app/data/db/data.sqlite", { readOnly: true });
  const { key } = database.prepare("SELECT key FROM apiKeys WHERE isActive=1").get();
  database.close();
  const anon = await fetch(base + "/v1/models", {
    headers: proxyHeaders, signal: AbortSignal.timeout(4000),
  });
  assert.equal(anon.status, 401);
  const authenticated = { ...proxyHeaders, Authorization: "Bearer " + key };
  const catalog = await fetch(base + "/v1/models", {
    headers: authenticated, signal: AbortSignal.timeout(5000),
  });
  assert.equal(catalog.status, 200);
  assert.deepEqual((await catalog.json()).data.map((entry) => entry.id), ["free/gemini-3.8-flash"]);
  const denied = await fetch(base + "/v1/chat/completions", {
    method: "POST",
    headers: { ...authenticated, "Content-Type": "application/json" },
    body: JSON.stringify({ model: "free/forbidden", messages: [{ role: "user", content: "fixture" }] }),
    signal: AbortSignal.timeout(5000),
  });
  assert.equal(denied.status, 403);
  console.log("Isolated Docker restore: health 200; missing key 401; one approved model; forbidden model 403.");
}

main().catch((error) => { console.error(error.message); process.exitCode = 1; });
