import { createInterface } from "node:readline";

const model = "free/gemini-3.8-flash";
const versions = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"];
const { FREE_FIRST_GATEWAY_URL: url, FREE_FIRST_GATEWAY_KEY: key } = process.env;
const base = new URL(url);
if (base.protocol !== "https:" || base.pathname !== "/v1" || base.username ||
    base.password || base.search || base.hash || !key) {
  throw Error("Expected an HTTPS /v1 URL and a gateway credential");
}

const tools = [
  {
    name: "gateway_models",
    description: "List the models allowed by the Free-First gateway key.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
    annotations: { readOnlyHint: true },
  },
  {
    name: "gateway_chat",
    description: "Send a bounded text prompt to the approved Free-First model and return its answer.",
    inputSchema: {
      type: "object",
      required: ["prompt"],
      properties: { prompt: { type: "string", minLength: 1, maxLength: 12000 } },
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true, openWorldHint: true },
  },
];

const resultText = (text, isError = false) => ({ content: [{ type: "text", text }], isError });

async function gateway(path, body) {
  const response = await fetch(base.href + path, {
    method: body ? "POST" : "GET",
    headers: { Authorization: "Bearer " + key, "Content-Type": "application/json", Accept: "application/json" },
    body: body && JSON.stringify(body),
    signal: AbortSignal.timeout(125000),
    redirect: "error",
  });
  if (!response.ok) throw Error(`Gateway returned HTTP ${response.status}`);
  return response.json();
}

async function callTool({ name, arguments: args = {} }) {
  try {
    if (name === "gateway_models" && Object.keys(args).length === 0) {
      const catalog = (await gateway("/models")).data.map((entry) => entry.id);
      if (catalog.length !== 1 || catalog[0] !== model) return resultText("Unexpected gateway catalog", true);
      return resultText(model);
    }
    if (name !== "gateway_chat" || Object.keys(args).length !== 1 ||
        typeof args.prompt !== "string" || args.prompt.length > 12000 || !args.prompt.trim()) {
      return resultText("Unsupported tool or arguments", true);
    }
    const response = await gateway("/chat/completions", {
      model, messages: [{ role: "user", content: args.prompt }], max_tokens: 1024, stream: false,
    });
    const content = response.choices?.[0]?.message?.content;
    return typeof content === "string" && content.trim()
      ? resultText(content)
      : resultText("The approved model returned no text", true);
  } catch (error) {
    const message = /^Gateway returned HTTP \d{3}$/.test(error.message)
      ? error.message : "Gateway request failed";
    return resultText(message, true);
  }
}

const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
const reply = (payload) => process.stdout.write(JSON.stringify({ jsonrpc: "2.0", ...payload }) + "\n");

input.on("line", async (line) => {
  let id = null;
  try {
    const request = JSON.parse(line);
    if (!Object.hasOwn(request, "id")) return;
    id = request.id;
    const { method, params = {} } = request;
    if (method === "initialize") {
      const protocolVersion = versions.includes(params.protocolVersion) ? params.protocolVersion : versions[0];
      reply({ id, result: { protocolVersion, capabilities: { tools: {} },
        serverInfo: { name: "free-first-gateway", version: "1.0.0" } } });
    } else if (method === "ping") {
      reply({ id, result: {} });
    } else if (method === "tools/list") {
      reply({ id, result: { tools } });
    } else if (method === "tools/call") {
      reply({ id, result: await callTool(params) });
    } else {
      reply({ id, error: { code: -32601, message: "Method not found" } });
    }
  } catch {
    reply({ id, error: { code: -32600, message: "Invalid request" } });
  }
});
