> Historical research. OpenCodex was removed on 2026-10-21. Claude Desktop
> uses Magpie; Codex integration is pending explicit request. Do not replay the
> setup suggestions below as current operating instructions.

Your diagnosis is correct. Codex CLI's poor performance with DeepSeek is a **protocol mismatch problem**, not a model weakness. Fortunately, there are several effective workarounds, and using Claude Code is one of the best.

### 🔧 The Root Cause: Protocol Mismatch

As you observed, Codex CLI is not a universal harness. It's built around OpenAI's specific API contract, and when you swap in DeepSeek, the transport layer breaks. The core issues are:

*   **Tool Schema Mismatch**: Codex wraps MCP tools in a proprietary `type: "namespace"` format that DeepSeek's OpenAI-compatible endpoint cannot unwrap, causing tools to be silently dropped before they ever reach the model.
*   **Thinking Mode Incompatibility**: DeepSeek's reasoning models require the previous `reasoning_content` to be passed back in subsequent requests during tool calls. Codex's API translator often fails to preserve this, breaking multi-turn tool use.
*   **Official Setup Pitfalls**: DeepSeek's own setup script for Codex can silently disable MCP tools by setting `supports_search_tool: true`, which defers all MCP tools and makes them invisible to the model.

### 🛠️ Workaround 1: Use a Local Proxy (For Codex CLI)

The most direct solution is to run a **local proxy** between Codex CLI and DeepSeek. These tools translate the protocols in real-time, fixing the schema and thinking-mode issues transparently.
 
| Proxy Tool | Key Features | Best For |
|:---|:---|:---|
| **opencodex** | Universal proxy for Codex & Claude Code. Translates Responses API, handles streaming, tool calls, and reasoning tokens. Manages ChatGPT account pools. | General-purpose solution for using *any* LLM with Codex or Claude Code. |
| **dsv4-cc-proxy-tray** | DeepSeek V4 specialist. Fixes 12+ compatibility bugs for both Claude Code and Codex CLI. Auto-detects request path and applies correct fixes. Has a Windows GUI. | If DeepSeek V4 is your primary model and you want a zero-config, stable setup. |
| **codex-bridge** | Zero-dependency local proxy. Specifically caches and replays `reasoning_content` for DeepSeek's thinking mode to survive multi-turn tool calls. Also has a tool-call circuit breaker. | A lightweight, focused fix for the thinking-mode round-trip issue. |
| **CLIProxyAPI** | Converts Codex's Responses API to Chat Completions. Flattens namespace tools correctly. Has a specific fix for DeepSeek returning bare function names. | If you want a more configurable, general-purpose translation gateway. |

**How to use it:**
1.  Install and start the proxy locally (e.g., `opencodex` runs on `localhost:10100`).
2.  Edit your `~/.codex/config.toml` to point `openai_base_url` to the proxy's address.
3.  Set the model name to your DeepSeek model (e.g., `deepseek-v4-pro`).
4.  Run Codex normally. The proxy handles all protocol translation.

### 🚀 Workaround 2: Use Claude Code (The Better Harness)

Your instinct to try **Claude Code** is well-founded. The community consensus is that **Claude Code's compatibility path is generally easier for running DeepSeek** than Codex's native path. The reason is architectural:

*   **Claude Code uses a prompt-driven tool-calling approach**, which is more forgiving of models that don't perfectly adhere to a strict API schema.
*   **DeepSeek officially supports the Anthropic API format**. Their documentation provides a direct, supported way to use DeepSeek models with Claude Code by simply setting environment variables.

**How to set it up (Official Method):**
1.  Get your DeepSeek API key.
2.  Set the following environment variables in your shell profile:
    ```bash
    export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
    export ANTHROPIC_AUTH_TOKEN=<your DeepSeek API Key>
    export ANTHROPIC_MODEL=deepseek-flash[1m]
    export ANTHROPIC_DEFAULT_OPUS_MODEL=deepseek-flash[1m]
    export ANTHROPIC_DEFAULT_SONNET_MODEL=deepseek-flash[1m]
    ```
    
3.  Run `claude` as you normally would. It will now use DeepSeek.

**Note:** You may still need a proxy like `dsv4-cc-proxy-tray` to fix specific thinking-mode bugs (e.g., missing `thinking` blocks causing 400 errors) that can occur with DeepSeek V4.

### 💡 Workaround 3: Use DeepSeek's Native Harness

DeepSeek has released its own agent harness, **DeepSeek Harness (DSH)**, which is built on an "everything is a plugin" architecture. It includes an **experimental Claude Code Mods compatibility layer**, allowing some Claude Code extensions to run within DSH. This is a promising direction, but the compatibility layer is still in alpha and not all mods work seamlessly yet. It's worth watching but not yet a drop-in replacement for your existing workflow.

### 💎 Recommendation

| Your Goal | Recommended Solution |
|:---|:---|
| **Keep using Codex CLI** with DeepSeek | **Use a local proxy** like `opencodex` or `dsv4-cc-proxy-tray`. This is the least disruptive change. |
| **Switch to a better harness for DeepSeek** | **Use Claude Code** with DeepSeek's official Anthropic API endpoint. This is the most stable and supported path. |
| **Stay up-to-date with DeepSeek's ecosystem** | **Follow DeepSeek Harness (DSH)**. Its Claude Code Mods compatibility layer could eventually offer a unified solution. |

**The bottom line:** You are not stuck with a bad combination. By using a proxy or switching to Claude Code, you can get reliable, high-performance agentic coding with DeepSeek. The protocol mismatch is a solvable engineering problem, not a fundamental limitation.