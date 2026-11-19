import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

const [launcher, cwd] = process.argv.slice(2);
assert.ok(launcher && cwd, "Pass the installed launcher and a clean test directory");
const model = "free/gemini-3.8-flash";

function connect() {
  const child = spawn("powershell.exe", [
    "-NoLogo", "-NoProfile", "-NonInteractive", "-File", launcher, "-Client", "codex", "-AppServer",
  ], { cwd, stdio: ["pipe", "pipe", "pipe"] });
  let id = 0;
  const pending = new Map();
  const events = [];
  let diagnostics = "";
  child.stderr.on("data", (chunk) => {
    diagnostics = (diagnostics + chunk).slice(-6000);
  });
  createInterface({ input: child.stdout }).on("line", (line) => {
    const message = JSON.parse(line);
    if (pending.has(message.id)) {
      pending.get(message.id)(message);
      pending.delete(message.id);
    } else if (message.method && !Object.hasOwn(message, "id")) {
      events.push(message);
    }
  });
  function send(message) {
    child.stdin.write(JSON.stringify({ jsonrpc: "2.0", ...message }) + "\n");
  }
  function request(method, params) {
    const requestId = ++id;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        pending.delete(requestId);
        const hint = diagnostics.split(/\r?\n/).filter((line) => /error|failed/i.test(line))
          .slice(-2).map((line) => line.replace(/https?:\/\/\S+/g, "[URL]"));
        reject(Error(method + " timed out" + (hint.length ? ": " + hint.join(" ") : "")));
      }, 15000);
      pending.set(requestId, (message) => {
        clearTimeout(timer);
        if (message.error) reject(Error(method + " failed: " + message.error.code));
        else resolve(message.result);
      });
      send({ id: requestId, method, params });
    });
  }
  async function initialize() {
    await request("initialize", { clientInfo: { name: "free-first-acceptance", version: "1" } });
    send({ method: "initialized" });
  }
  async function turn(threadId, text) {
    const { turn } = await request("turn/start", { threadId, input: [{ type: "text", text }] });
    const select = (event) => event.params?.turnId === turn.id || event.params?.turn?.id === turn.id;
    for (let ticks = 0; ticks < 400; ticks++) {
      const complete = events.find((event) => select(event) && event.method === "turn/completed");
      if (complete) {
        assert.equal(complete.params.turn.status, "completed");
        return events.filter(select);
      }
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    throw Error("Persistent Codex turn timed out");
  }
  async function stop() {
    child.stdin.end();
    await new Promise((resolve) => {
      if (child.exitCode !== null) return resolve();
      child.once("exit", resolve);
      setTimeout(() => { child.kill(); resolve(); }, 5000).unref();
    });
  }
  return { request, initialize, turn, stop };
}

function checkAnswer(events, expected) {
  const reply = events.filter((event) => event.method === "item/agentMessage/delta")
    .map((event) => event.params.delta).join("");
  assert.ok(reply.includes(expected), "Expected answer was absent from streamed deltas");
  return events.filter((event) => event.method === "item/agentMessage/delta").length;
}

const client = connect();
let threadId;
try {
  await client.initialize();
  const start = await client.request("thread/start", { cwd, approvalPolicy: "never", sandbox: "read-only" });
  assert.equal(start.model, model);
  assert.equal(start.modelProvider, "free_first_gateway");
  threadId = start.thread.id;
  const status = await client.request("mcpServerStatus/list", { threadId });
  const names = status.data.map((server) => server.name);
  assert.ok(names.includes("free-first-gateway"));
  const legacyTools = status.data.filter((server) => /omniroute|9router-candidate/i.test(server.name))
    .reduce((count, server) => count + Object.keys(server.tools ?? {}).length, 0);
  assert.equal(legacyTools, 0, "The scoped Codex profile exposed legacy tools");
  const events = await client.turn(threadId,
    "Call the gateway_models MCP tool once. Then use the actual result to answer with ACCEPTED: followed by the model ID. Use no other tool.");
  const calls = events.filter((event) => event.method === "item/completed")
    .map((event) => event.params.item).filter((item) => item.type === "mcpToolCall");
  assert.equal(calls.length, 1);
  assert.equal(calls[0].server, "free-first-gateway");
  assert.equal(calls[0].tool, "gateway_models");
  assert.equal(calls[0].status, "completed");
  assert.ok(calls[0].result?.content?.some((item) => item.text === model));
  const completion = events.findIndex((event) =>
    event.method === "item/completed" && event.params.item.id === calls[0].id);
  console.log(JSON.stringify({ toolCall: "gateway_models", streamedDeltas: checkAnswer(events.slice(completion + 1), model),
    toolResultContinuation: true, legacyTools }));
} finally {
  await client.stop();
}

const restarted = connect();
try {
  await restarted.initialize();
  const resumed = await restarted.request("thread/resume", {
    threadId, cwd, approvalPolicy: "never", sandbox: "read-only",
  });
  assert.equal(resumed.thread.id, threadId);
  assert.equal(resumed.model, model);
  assert.equal(resumed.modelProvider, "free_first_gateway");
  const events = await restarted.turn(threadId, "Repeat the model ID returned by the tool in the previous turn. Use no tools.");
  console.log(JSON.stringify({ resumedAfterRestart: true, streamedDeltas: checkAnswer(events, model) }));
} finally {
  await restarted.stop();
}
