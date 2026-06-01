/**
 * `@sardis/agent-tools/mcp` — expose the Sardis verbs in the
 * `sardis-mcp-server` tool shape: a `ToolDefinition[]` (JSON-Schema input) plus
 * a `ToolHandler` record (`(args) => Promise<ToolResult>`). The MCP server can
 * mount these alongside its existing `sardis_*` tools.
 *
 * Each handler runs through the governance gate, so the MCP `ToolResult` text
 * is the governed JSON (`status` / `outcome` / `commitHash` / `result`). A
 * blocked or awaiting-approval verb sets `isError: false` but reports the
 * non-`executed` status so the calling model can react.
 *
 * To keep the core dependency-free we derive the JSON Schema from each verb's
 * flat zod object by hand (the verb schemas are simple string/number/record
 * objects); no zod-to-json-schema dependency is pulled in.
 */
import { z } from 'zod';
import type { GovernedResult, SardisToolContext } from '../types.js';
import { ALL_VERBS } from '../tools/verbs.js';
import { buildRegistry, runGoverned } from '../index.js';

export interface McpToolResult {
  content: Array<{ type: 'text'; text: string }>;
  isError?: boolean;
  [key: string]: unknown;
}

export interface McpToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: 'object';
    properties: Record<string, unknown>;
    required: string[];
  };
}

export type McpToolHandler = (args: unknown) => Promise<McpToolResult>;

/** Minimal JSON Schema for a single zod field used by the verb schemas. */
function fieldToJsonSchema(schema: z.ZodTypeAny): { node: Record<string, unknown>; required: boolean } {
  let s = schema;
  let required = true;
  // Unwrap optionals/defaults.
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const def = (s as { _def?: { typeName?: string; innerType?: z.ZodTypeAny } })._def;
    const typeName = def?.typeName;
    if (typeName === 'ZodOptional' || typeName === 'ZodDefault') {
      required = false;
      s = def!.innerType as z.ZodTypeAny;
      continue;
    }
    break;
  }
  const description = (s as { description?: string }).description;
  const def = (s as { _def?: { typeName?: string } })._def;
  let node: Record<string, unknown>;
  switch (def?.typeName) {
    case 'ZodString':
      node = { type: 'string' };
      break;
    case 'ZodNumber':
      node = { type: 'number' };
      break;
    case 'ZodBoolean':
      node = { type: 'boolean' };
      break;
    case 'ZodRecord':
      node = { type: 'object' };
      break;
    default:
      node = {};
  }
  if (description) node.description = description;
  return { node, required };
}

function zodObjectToJsonSchema(schema: z.ZodTypeAny): McpToolDefinition['inputSchema'] {
  const properties: Record<string, unknown> = {};
  const required: string[] = [];
  const shape =
    (schema as { _def?: { shape?: () => Record<string, z.ZodTypeAny> } })._def?.shape?.() ?? {};
  for (const [key, field] of Object.entries(shape)) {
    const { node, required: isReq } = fieldToJsonSchema(field);
    properties[key] = node;
    if (isReq) required.push(key);
  }
  return { type: 'object', properties, required };
}

function asToolResult(result: GovernedResult): McpToolResult {
  return {
    content: [{ type: 'text', text: JSON.stringify(result) }],
    // A governed block / awaiting-approval is a valid, expected outcome, not an
    // MCP transport error — surface the status in the body instead.
    isError: false,
  };
}

/** Build the MCP definitions + handler record for the Sardis verbs. */
export function createMcpTools(ctx: SardisToolContext): {
  definitions: McpToolDefinition[];
  handlers: Record<string, McpToolHandler>;
} {
  const registry = buildRegistry();
  const definitions: McpToolDefinition[] = [];
  const handlers: Record<string, McpToolHandler> = {};

  for (const tool of ALL_VERBS) {
    definitions.push({
      name: tool.name,
      description: tool.description,
      inputSchema: zodObjectToJsonSchema(tool.schema),
    });
    handlers[tool.name] = async (args: unknown): Promise<McpToolResult> => {
      const result = await runGoverned(tool.name, args, ctx, { registry });
      return asToolResult(result);
    };
  }

  return { definitions, handlers };
}
