import { spawn } from "node:child_process";
import { randomBytes, timingSafeEqual } from "node:crypto";
import { once } from "node:events";
import { readFileSync } from "node:fs";
import { createServer } from "node:http";
import { fileURLToPath } from "node:url";

const namespace = "mcp__free_first_gateway";
const prefix = "free_first_mcp_";
const model = "free/gemini-3.8-flash";
const allowedTools = new Set(["gateway_models", "gateway_chat"]);
const maxBytes = 6 * 1024 * 1024;

function matchingCall(item) {
  return item?.namespace === namespace && allowedTools.has(item.name);
}

function flattenCall(item) {
  const { namespace: _, ...call } = item;
  return { ...call, name: prefix + call.name };
}

export function translateRequest(body) {
  if (Array.isArray(body.tools)) {
    body.tools = body.tools.flatMap((tool) => {
      if (tool.type !== "namespace" || tool.name !== namespace) return [tool];
      return (tool.tools ?? []).filter((entry) => entry.type === "function" && allowedTools.has(entry.name))
        .map((entry) => ({ ...entry, name: prefix + entry.name }));
    });
  }
  if (Array.isArray(body.input)) {
    body.input = body.input.map((item) =>
      item.type === "function_call" && matchingCall(item) ? flattenCall(item) : item);
  }
  if (matchingCall(body.tool_choice)) body.tool_choice = flattenCall(body.tool_choice);
  return body;
}

function restoreCall(item) {
  if (item?.type !== "function_call" || typeof item.name !== "string" || !item.name.startsWith(prefix)) return;
  const name = item.name.slice(prefix.length);
  if (allowedTools.has(name)) {
    item.name = name;
    item.namespace = namespace;
  }
}

export function translateEvent(event) {
  restoreCall(event.item);
  for (const item of event.response?.output ?? event.output ?? []) restoreCall(item);
  return event;
}

export function translateFrame(frame) {
  const lines = frame.split(/\r?\n/);
  const data = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trimStart()).join("\n");
  if (!data || data === "[DONE]" || !data.includes(prefix)) return frame;
  return [...lines.filter((line) => !line.startsWith("data:")), "data: " + JSON.stringify(translateEvent(JSON.parse(data)))].join("\n");
}

async function sse(upstream, response) {
  const source = upstream.body.pipeThrough(new TextDecoderStream());
  let buffer = "";
  response.flushHeaders();
  for await (const text of source) {
    buffer += text;
    let separator;
    while ((separator = /\r?\n\r?\n/.exec(buffer))) {
      const frame = translateFrame(buffer.slice(0, separator.index)) + "\n\n";
      if (!response.write(frame)) {
        await once(response, "drain", { signal: AbortSignal.timeout(125000) });
      }
      buffer = buffer.slice(separator.index + separator[0].length);
    }
    if (buffer.length > maxBytes) throw Error("Oversized SSE event");
  }
  if (buffer.trim()) response.write(translateFrame(buffer) + "\n\n");
  response.end();
}

async function serve(req, res, endpoint, gatewayKey, localBearer) {
  const incoming = Buffer.from(req.headers.authorization ?? "");
  if (incoming.length !== localBearer.length || !timingSafeEqual(incoming, localBearer)) {
    res.writeHead(401).end();
    return;
  }
  if (req.method !== "POST" || req.url !== "/v1/responses") {
    res.writeHead(404).end();
    return;
  }
  let length = 0;
  const chunks = [];
  for await (const chunk of req) {
    length += chunk.length;
    if (length > maxBytes) {
      res.writeHead(413).end();
      return;
    }
    chunks.push(chunk);
  }
  let payload;
  try {
    payload = JSON.parse(Buffer.concat(chunks));
  } catch {
    res.writeHead(400).end();
    return;
  }
  if (payload?.model !== model) {
    res.writeHead(403).end();
    return;
  }
  const stopped = new AbortController();
  res.on("close", () => stopped.abort());
  try {
    const upstream = await fetch(endpoint + "/responses", {
      method: "POST", redirect: "error",
      headers: { Authorization: "Bearer " + gatewayKey, "Content-Type": "application/json" },
      body: JSON.stringify(translateRequest(payload)),
      signal: AbortSignal.any([stopped.signal, AbortSignal.timeout(180000)]),
    });
    const contentType = upstream.headers.get("content-type") || "application/json";
    const retryAfter = upstream.headers.get("retry-after");
    res.setHeader("Content-Type", contentType);
    if (retryAfter) res.setHeader("Retry-After", retryAfter);
    res.statusCode = upstream.status;
    if (upstream.ok && contentType.startsWith("text/event-stream")) {
      await sse(upstream, res);
    } else {
      const data = await upstream.text();
      res.end(upstream.ok ? JSON.stringify(translateEvent(JSON.parse(data))) : data);
    }
  } catch {
    if (res.headersSent) res.destroy();
    else res.writeHead(502, { "Content-Type": "application/json" }).end('{"error":{"message":"Gateway transport failed"}}');
  }
}

async function main([mode, ...argv]) {
  const { FREE_FIRST_GATEWAY_URL: url, FREE_FIRST_GATEWAY_KEY: key } = process.env;
  const endpoint = new URL(url);
  if (!key || endpoint.protocol !== "https:" || endpoint.pathname !== "/v1" ||
      endpoint.search || endpoint.hash || endpoint.username || endpoint.password) {
    throw Error("Expected the approved HTTPS endpoint and credential");
  }
  const localKey = randomBytes(24).toString("hex");
  const bearer = Buffer.from("Bearer " + localKey);
  const server = createServer((req, res) => {
    serve(req, res, endpoint.href, key, bearer).catch(() => res.destroy());
  });
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  try {
    const env = { ...process.env, FREE_FIRST_CODEX_LOCAL_KEY: localKey };
    delete env.FREE_FIRST_GATEWAY_KEY;
    const origin = `http://127.0.0.1:${server.address().port}/v1`;
    const overrides = [
      "-c", 'model_provider="free_first_gateway"',
      "-c", `model="${model}"`,
      "-c", `model_providers.free_first_gateway.base_url="${origin}"`,
      "-c", 'model_providers.free_first_gateway.env_key="FREE_FIRST_CODEX_LOCAL_KEY"',
    ];
    let config;
    if (mode === "app-server") {
      const defaults = JSON.parse(readFileSync(new URL("./codex-runtime.json", import.meta.url), "utf8"));
      config = ["app-server", "--listen", "stdio://", ...defaults, ...overrides];
    } else {
      const [profile, ...command] = argv;
      if (!["free-first-gateway", "gemini-gemini-3-8-flash"].includes(profile)) {
        throw Error("Unknown Free-First profile");
      }
      config = ["-p", profile, ...overrides, ...command];
    }
    const codex = readFileSync(new URL("./codex.txt", import.meta.url), "utf8").trim();
    const child = spawn(codex, config, { stdio: "inherit", env });
    const [code] = await once(child, "exit");
    process.exitCode = code ?? 1;
  } finally {
    server.closeAllConnections();
    server.close();
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url).toLowerCase() === process.argv[1].toLowerCase()) {
  main(process.argv.slice(2)).catch(() => { console.error("Free-First Codex transport failed"); process.exitCode = 1; });
}
