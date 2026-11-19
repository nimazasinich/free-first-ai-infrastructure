import assert from "node:assert/strict";
import test from "node:test";
import { translateEvent, translateFrame, translateRequest } from "../client/codex-transport.mjs";

const namespace = "mcp__free_first_gateway";

test("flatten and restore only registered Free-First namespace calls", () => {
  const body = translateRequest({
    tools: [
      { type: "namespace", name: namespace, tools: [
        { type: "function", name: "gateway_models", parameters: { type: "object" } },
        { type: "function", name: "unexpected" },
      ] },
      { type: "function", name: "shell" },
    ],
    input: [
      { type: "function_call", namespace, name: "gateway_models", call_id: "call-1" },
      { type: "function_call_output", call_id: "call-1", output: "model" },
    ],
  });
  assert.deepEqual(body.tools.map((tool) => tool.name), ["free_first_mcp_gateway_models", "shell"]);
  assert.deepEqual(body.input[0], { type: "function_call", name: "free_first_mcp_gateway_models", call_id: "call-1" });
  assert.equal(body.input[1].call_id, "call-1");
  const event = translateEvent({ item: { type: "function_call", name: "free_first_mcp_gateway_models", call_id: "call-1" } });
  assert.deepEqual(event.item, { type: "function_call", namespace, name: "gateway_models", call_id: "call-1" });
});

test("SSE preserves plain deltas and restores a tool in the completion", () => {
  const unchanged = 'event: response.output_text.delta\ndata: {"delta":"hello"}';
  assert.equal(translateFrame(unchanged), unchanged);
  const input = 'event: response.completed\ndata: {"response":{"output":[{"type":"function_call","name":"free_first_mcp_gateway_chat"}]}}';
  const frame = translateFrame(input);
  assert.match(frame, /^event: response.completed\n/);
  const result = JSON.parse(frame.split("\ndata: ")[1]);
  assert.deepEqual(result.response.output[0], { type: "function_call", namespace, name: "gateway_chat" });
});
