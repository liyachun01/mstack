Here is an organized, categorized, and tagged knowledge base of all the tools discussed, formatted for direct use in your documentation.

---

## 🧠 Groq: What It Is

**Groq** is a company that designs **Language Processing Units (LPUs)** — specialized inference accelerators optimized for running large language models at extremely high speed. Unlike GPUs designed for training, LPUs are purpose-built for **inference** (the act of running a model to generate output). Their latest hardware, the **NVIDIA Groq 3 LPX**, pairs with NVIDIA's Vera Rubin NVL72 platform and can achieve **3,400 output tokens per second** on a 31B parameter model with 100K token context. Each LPX rack contains 256 interconnected LPU accelerators, each delivering 500 MB SRAM and 150 TB/s SRAM bandwidth.

**In your stack:** Groq is a **hosted inference provider**. You would use it via its API when you need maximum speed for a specific model and are willing to send data to their cloud. It is not a local runtime.

---

## 📚 Tool Knowledge Base

### 🖥️ Category: Model Runtime & Inference

Tools that run models locally and expose them via an API.

| Tool | What It Is | Key Detail | Tags |
|:---|:---|:---|:---|
| **llama.app** | Official macOS menu bar app for `llama.cpp` | Runs a local server at `http://localhost:9931/v1`. Simplest local model runner. | `local-llm` `openai-compatible` `macos` `minimal` |
| **Ollama** | Headless local model runner | CLI + daemon; vast model library; zero-to-API in one command. No native MCP host. | `local-llm` `cli` `headless` `mcp-bridge-needed` |
| **llama.cpp** | Raw C++ inference engine | Same engine LM Studio and Ollama wrap. Maximum control. | `local-llm` `engine` `gguf` `low-level` |
| **vLLM** | High-throughput serving engine | Production-grade inference; serves models to many concurrent clients. | `serving` `high-throughput` `production` |
| **SGLang** | Multi-turn tool-calling serving engine | Automatic tool execution; optimized for agentic serving. | `serving` `agentic` `mcp-native` |
| **KoboldCpp** | Single-file portable runner | Native MCP bridge; faster than LM Studio on identical hardware; exposes OpenAI + Ollama + A1111 endpoints. | `portable` `single-file` `mcp-host` `fast` |
| **LM Studio** | Desktop model runner + MCP Host | Built-in MCP client (v0.3.17+); OpenAI-compatible API on `localhost:1234/v1`. Closed binary. | `desktop` `mcp-host` `local-llm` `closed-source` |
| **Jan** | Open-source desktop MCP Host | Apache-2.0; native MCP host; connects to local **and** hosted models (OpenAI, Anthropic, OpenRouter). | `desktop` `mcp-host` `open-source` `hosted-bridge` |
| **GPT4All** | Simple desktop local chat + LocalDocs | Excellent built-in RAG (LocalDocs) over local folders. **No native MCP support.** | `desktop` `rag` `no-mcp` `beginner-friendly` |
| **LocalAI** | Full agentic platform + MCP | Drop-in OpenAI/Claude replacement; MCP apps; autonomous agents; terminal agent. | `platform` `mcp-native` `agentic` `api-server` |
| **text-generation-webui** | Gradio web UI for all model formats | Supports GGUF, EXL2, AWQ; OpenAI/Anthropic-compatible API; MCP extension. | `web-ui` `multi-format` `mcp-extension` |
| **llamafile** | Single-file executable | No install; runs on any OS; OpenAI-compatible API on port 8080. | `portable` `single-file` `air-gapped` |

---

### 🔌 Category: MCP Infrastructure & Gateways

Tools that manage, route, aggregate, or host MCP connections.

| Tool | What It Is | Key Detail | Tags |
|:---|:---|:---|:---|
| **MetaMCP** | MCP aggregator + middleware gateway | Federates multiple MCP servers under one endpoint; auth, logging, rate limiting, schema transformation. | `mcp-gateway` `aggregator` `middleware` `deprecated-in-favor-of-agentgateway` |
| **AgentGateway** | LLM + MCP gateway | Centralized routing, security, observability. Can route to LM Studio as upstream provider. | `mcp-gateway` `llm-gateway` `governance` `observability` |
| **MCPHost** (`mark3labs/mcphost`) | Go CLI MCP host bridge | Connects any Ollama model to any MCP server. Supports OpenAI, Anthropic, Google, Ollama. | `mcp-host` `cli` `ollama-bridge` `multi-provider` |
| **mcp-proxy** | Lightweight MCP proxy | Bridges stdio to HTTP/SSE; aggregates servers behind one endpoint. | `proxy` `bridge` `stdio-to-http` |
| **mcp-local-tunnel** | Secure MCP tunnel | Creates tunnel to remote MCP servers without opening ports. | `tunnel` `secure` `remote-access` |
| **mcptp** | MCP "teleport" proxy | Forwards MCP traffic to remote destinations. | `proxy` `remote` `tunnel` |

---

### 🧠 Category: Memory Systems

Tools that give agents persistent memory across sessions.

| Tool | What It Is | Storage | Human-Readable? | Tags |
|:---|:---|:---|:---|:---|
| **basic-memory** | Markdown knowledge base + SQLite index | Markdown files | ✅ Yes | `markdown` `human-readable` `obsidian-compatible` `mcp-native` `your-current-choice` |
| **agentmemory** | Agent-native memory engine + MCP server | Proprietary store | ❌ No | `agent-native` `37-tools` `auto-capture` `multi-agent` `hybrid-search` |
| **Graphiti** (Zep) | Temporal knowledge graph | Neo4j + vector store | ❌ No | `temporal` `graph` `fact-evolution` `bi-temporal` `llm-extraction` |
| **Anthropic Knowledge Graph Memory** | Canonical reference implementation | Flat JSON | ❌ No | `reference` `minimal` `flat-json` `not-production-ready` |
| **doobidoo/mcp-memory-service** | Multi-backend memory MCP | SQLite + sqlite-vec + FTS5 | ❌ No | `multi-backend` `causal-graph` `rest-api` `security-grade-F` |
| **ai-memory** (akitaonrails) | Portable memory for coding agents | Git-backed Markdown wiki | ✅ Yes | `portable` `git-backed` `markdown` `rust` `cross-agent` `handoff` |
| **Context Teleport** | Portable, git-backed context store | Git-backed `.context-teleport/` | ✅ Yes | `portable` `git-backed` `32-mcp-tools` `session-history` `skills` |
| **PACK** (Percona-Lab) | Standalone MCP server backed by GitHub | Private GitHub repo (Markdown) | ✅ Yes | `portable` `github-backed` `markdown` `low-stars` `4-tools` |

---

### 💻 Category: Remote Workstation & Browser

Tools that serve your machine or browser to any device.

| Tool | What It Is | Key Detail | Tags |
|:---|:---|:---|:---|
| **Open WebUI Computer** (`cptr`) | Serves your real machine to any browser | Files, editor, terminal, git, AI chat, coding agents. Sessions survive tab close. `pip install cptr`. | `remote-workstation` `browser` `persistent-sessions` `real-machine` |
| **Open WebUI** | Self-hosted AI control layer | Model choice, chat, knowledge, users, permissions. Becomes a harness with Open Terminal. | `control-layer` `web-ui` `mcp-host` `sub-agents` |
| **Open Terminal** | Action layer inside Open WebUI | Fresh, isolated Docker workspace for code execution, builds, tests. | `action-layer` `sandbox` `docker` `ephemeral` |
| **Roost** | 4 MB Rust binary browser terminal | Per-project tabs; PTY sessions survive tab close; Claude Code IDE protocol support. | `terminal` `browser` `lightweight` `rust` `persistent-sessions` |
| **code-server** | Full VS Code in browser | MIT; full extension marketplace; built-in terminal. | `ide` `vs-code` `browser` `mature` |
| **wede** | Single-binary collaborative web IDE | ~19 MB Go binary; real-time multi-user editing; shared terminals; VS Code-grade git. | `ide` `single-binary` `collaborative` `go` |
| **Neko** | Self-hosted virtual browser in Docker | WebRTC streaming; multi-user; full browser (Firefox, Chrome, etc.). | `virtual-browser` `webrtc` `docker` `multi-user` |
| **agentbox** (madarco) | Isolated sandbox for coding agents | Runs agents in parallel VMs/containers; Docker, Vercel, E2B providers. | `sandbox` `isolation` `parallel-agents` `vm` |
| **agentbox** (vojtabiberle) | Container isolation for agents | Prevents `--dangerously-skip-permissions` from touching host. | `sandbox` `container` `security` |
| **agentbox** (devilcoolyue) | Self-hosted browser workspace | Docker sessions, terminal, files, Git, usage tracking for Claude Code/Codex CLI. | `workspace` `browser` `docker` `usage-tracking` |

---

### 🔄 Category: Portable Context & Handoff

Tools that externalize agent context so it travels across agents and machines.

| Tool | What It Is | Storage | Tags |
|:---|:---|:---|:---|
| **Context Teleport** | Portable context bundle for AI coding agents | Git-backed `.context-teleport/` | `portable` `git-backed` `knowledge` `decisions` `skills` `session-history` |
| **ai-memory** (akitaonrails) | Long-term memory for agent CLIs | Git-versioned Markdown wiki | `portable` `git-backed` `rust` `mcp` `hooks` `cross-agent-handoff` |
| **PACK** | Standalone MCP server backed by GitHub | Private GitHub repo | `portable` `github-backed` `markdown` `low-adoption` |
| **agent-context-cli** | Portable system context in repo | `.agent-context/` in repository | `repo-native` `portable` `git-backed` |
| **Engram** | Agent-agnostic memory binary | SQLite + FTS5 | `agent-agnostic` `go` `sqlite` `mcp` `http-api` `tui` |

---

### 📄 Category: RAG & Knowledge Platforms

Tools that turn documents into queryable knowledge bases.

| Tool | What It Is | MCP? | Tags |
|:---|:---|:---|:---|
| **AnythingLLM** | All-in-one RAG + agent workspace | ✅ Full | `rag` `document-ingestion` `agent-builder` `desktop` `mcp-host` `model-router` |
| **Dify** | AI application development platform | ✅ Imports MCP servers | `rag` `agent-workflows` `ai-native` `complement-not-replace` |
| **OpenWiki** | Proactive wiki generator (code + personal) | ✅ Connectable | `documentation` `grounded-claims` `agent-first` `codebase-wiki` |

---

### ⚙️ Category: Workflow Automation & Orchestration

Tools that route, schedule, and execute workflows.

| Tool | What It Is | Code Execution | Self-Hosted | Tags |
|:---|:---|:---|:---|:---|
| **n8n** | Visual workflow automation | Sandboxed (10-min limit) | ✅ | `visual` `400+-connectors` `mcp-server-trigger` `mcp-client` |
| **Windmill** | Code-first orchestration + storage | Full polyglot (Python, TS, Go) | ✅ | `code-first` `ducklake` `data-tables` `asset-lineage` `source-of-truth` |
| **Activepieces** | Open-source Zapier alternative | Limited | ✅ | `mit-license` `mcp-native` `400-mcp-tools` `visual` |
| **Dify** | AI-native app platform | Limited | ✅ | `ai-native` `rag` `agent-workflows` |
| **Gumloop** | Managed AI workflow platform | Limited | ❌ (Enterprise VPC) | `managed` `cloud-only` `no-local-mcp` |
| **Lindy** | Managed AI executive assistant | HTTP Request action | ❌ | `hosted-only` `no-mcp` `non-technical` |
| **Strands Agents** | Code-first agent SDK | Full (Python/TS) | ✅ (library) | `sdk` `multi-agent` `graph` `swarm` `aws-bedrock` |

---

### 🗄️ Category: Database & Storage UI

Tools for viewing, querying, and managing databases.

| Tool | What It Is | MCP? | Tags |
|:---|:---|:---|:---|
| **WhoDB** | Lightweight self-hosted DB explorer | ✅ Native | `lightweight` `go` `browser` `fast` `mcp-native` |
| **DBeaver** | Full database IDE | ❌ | `heavy` `dba-tools` `50+-db-engines` |
| **pgAdmin 4** | Official Postgres admin | ❌ | `official` `heavy` `dba` |
| **CloudBeaver** | Web version of DBeaver | ❌ | `web` `jvm-heavy` `enterprise` |
| **pgweb** | Ultra-light Postgres browser | ❌ | `ultra-light` `go` `read-only` `fast` |
| **Teable** | Airtable-like database UI | ✅ Native | `airtable-like` `community-edition` `agpl-3.0` |
| **Supabase** | Full backend platform | ✅ 31+ tools | `production-layer` `auth` `realtime` `postgrest` `per-project` |
| **NocoBase** | No-code platform | ✅ | `commercial-license` `consolidated-plugins` |

---

### 📝 Category: Knowledge Management & Note-Taking

Tools for personal knowledge management and structured notes.

| Tool | What It Is | Data Format | Open Source? | Tags |
|:---|:---|:---|:---|:---|
| **Obsidian + Bases** | PKM with native table views | Markdown + YAML | ✅ (MIT) | `markdown` `human-readable` `bases` `plugins` `fomo-risk` |
| **SiYuan** | Privacy-first PKM with Attribute Views | `.sy` JSON files | ✅ (AGPLv3) | `json` `attribute-views` `mcp-server` `agent-native` |
| **AppFlowy** | Notion-style workspace | SQLite + CollabKVDB | ⚠️ Commercial | `commercial-shift` `single-seat-free` `security-concerns` |
| **Anytype** | Local-first encrypted workspace | Encrypted protobuf | ✅ (client) | `encrypted` `local-first` `self-hostable` `7-container-server` `not-plain-text` |
| **Outline** | Team wiki | Database | ⚠️ BSL 1.1 | `team-wiki` `no-database` |
| **Docmost** | Collaborative wiki | Database | ⚠️ Commercial | `commercial-wall` `bases-paid` |
| **MarkdownDB** | Indexes Markdown into SQLite | SQLite index | ✅ | `agent-interface` `sql-queryable` `read-only-index` |

---

### 🔒 Category: Security & Sandboxing

Tools that isolate agent execution for safety.

| Tool | What It Is | Isolation Level | Tags |
|:---|:---|:---|:---|
| **agentbox** (madarco) | Run agents in parallel sandboxed VMs | VM/container | `sandbox` `vm` `parallel` `docker` `e2b` `vercel` |
| **agentbox** (vojtabiberle) | Container isolation for agents | Container | `container` `workspace-only-access` |
| **agent-box-cli** | Isolated config launcher | Kernel-level (`bwrap`) | `kernel-isolation` `bwrap` `multi-agent` |

---

### 🧩 Category: Code Intelligence

Tools that help agents understand code structure.

| Tool | What It Is | Output | MCP? | Tags |
|:---|:---|:---|:---|:---|
| **Graphify** | Multi-modal knowledge graph | `graph.json` + HTML | ✅ Native | `ast` `tree-sitter` `multi-modal` `token-efficient` `8x-savings` |
| **CodeGraph** | Semantic code graph | Persistent index | ✅ 42 tools | `symbol-retrieval` `call-chains` `impact-analysis` `92%-tool-call-reduction` |
| **OpenWiki** | Proactive wiki generator | Markdown wiki | ✅ Connectable | `grounded-claims` `self-correcting` `architecture-docs` |

---

## 🏷️ Tag Index

Use these tags to filter and cross-reference tools in your documentation.

| Tag | Tools |
|:---|:---|
| `local-llm` | llama.app, Ollama, llama.cpp, LM Studio, Jan, GPT4All, KoboldCpp, LocalAI, text-generation-webui, llamafile |
| `mcp-host` | LM Studio, Jan, KoboldCpp, LocalAI, MCPHost, Open WebUI |
| `mcp-gateway` | MetaMCP, AgentGateway |
| `mcp-native` | WhoDB, AnythingLLM, Teable, SiYuan, Graphify, CodeGraph |
| `markdown` | basic-memory, ai-memory, Context Teleport, PACK, Obsidian |
| `portable` | ai-memory, Context Teleport, PACK, KoboldCpp, llamafile |
| `git-backed` | ai-memory, Context Teleport, PACK, agent-context-cli |
| `sandbox` | agentbox, agent-box-cli, Open Terminal, Neko |
| `browser` | Open WebUI Computer, Roost, code-server, wede, Neko |
| `rag` | AnythingLLM, GPT4All LocalDocs, Dify, OpenWiki |
| `code-first` | Windmill, Strands Agents, CodeGraph |
| `visual` | n8n, Activepieces, Gumloop |
| `lightweight` | WhoDB, pgweb, Roost, wede, llama.app |
| `agent-native` | agentmemory, SiYuan, Graphify, CodeGraph, Open WebUI |
| `commercial-license` | AppFlowy, Docmost, NocoBase, Lindy, Gumloop |
| `open-source` | Jan, SiYuan, Windmill, Activepieces, basic-memory, Open WebUI |

---

## 💎 Summary

This knowledge base captures **40+ tools** across **11 categories**, each tagged for quick retrieval. The core insight from our entire conversation: **you don't need most of these.** Your minimal stack is **Codex + Windmill + Garage + WhoDB + Anytype + AgentGateway**. Everything else is either a complement you add on-demand (Graphify, ai-memory, Open WebUI Computer) or a tool you've consciously deprioritized. Use this document as a reference, not a shopping list.