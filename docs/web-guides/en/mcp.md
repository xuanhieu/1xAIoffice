---
title: 1xAIoffice and MCP: outside tools and assistants
description: Connect outside MCP servers for Ask AI, or let Claude Desktop and Cursor read and edit 1xAIoffice documents. Every tool and assistant needs your approval.
headline: Use MCP with 1xAIoffice
lead: MCP works both ways. MCP Tools lets Ask AI use outside tools; Share with Assistants lets Claude Desktop or Cursor work on your open documents. Both ask you first.
order: 4
---

MCP is the standard way for AI assistants to use tools. 1xAIoffice supports it in both directions: MCP Tools lets Ask AI call tools from outside MCP servers, and Share with Assistants turns 1xAIoffice into an MCP server so Claude Desktop or Cursor can read and edit your open documents. Both stay off until you approve them.

## Connect outside MCP servers {#outside-tools}

1. **Click MCP Tools** on the AI tab. Without a configuration the app shows the path of `mcp_servers.json` in the app profile, with an example.
2. **List your servers in `mcp_servers.json`.** Same format as `claude_desktop_config.json` (an `mcpServers` section, each server with `command`/`args` or a `url`). For a server that needs a fixed access token, set `token_ref` to the name of a Keychain item instead of writing the token in the file.
3. **Open MCP Tools again** to see each tool and its status: allowed, denied, or ask when used.
4. **Ask AI as usual.** The first time AI wants a tool, the app asks whether to allow it from now on. If a tool's description or parameters change, it asks again.

For servers that need a sign-in, the browser opens and nothing is sent until you agree there. Only Ask AI uses MCP tools.

## Let outside assistants use 1xAIoffice {#assistants}

1. **Click Share with Assistants** (Vietnamese menu ▸ Let Assistants Use 1xAIoffice). The first time, the app asks whether to turn it on.
2. **Copy the configuration it shows** into Claude Desktop, Cursor or another MCP client, then restart that assistant.
3. **Approve the assistant.** When it asks to connect, click Share with Assistants again: the app asks whether that assistant may read and edit your documents from now on. This is also where you see approved assistants and turn the server off.

An approved assistant can list open documents, read their content and outline, read cell ranges in 1xSheet, run the Decree 30 format check, convert Vietnamese encodings, and insert or replace text. Every change is shown to you and waits for your approval.

## What it does not do {#limits}

- The 1xAIoffice MCP server runs over stdio and opens no network port.
- [Bundled skills](/office/en/skill) are not shared; only skills you added yourself are offered to outside assistants.
- MCP Tools only lists tools; it never runs one by itself.
