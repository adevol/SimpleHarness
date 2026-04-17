# SimpleHarness

A minimal coding agent in about 130 lines of Python. Built to demystify the core loop behind tools like [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), [OpenAI Codex](https://openai.com/index/codex/), [Pi Code](https://shittycodingagent.ai/), and [OpenCode](https://opencode.ai/), based on [this article](https://www.mihaileric.com/The-Emperor-Has-No-Clothes/).

Production harnesses layer on massive system prompts, permission models, MCP servers, skills, context compaction, and more. This strips all of that away to expose the fundamental pattern: **prompt -> LLM -> tool calls -> loop**.

## What it does

1. Sends your message + a system prompt + tool definitions to any LLM (via the [litellm](https://github.com/BerriAI/litellm) library)
2. If the model decides to use any tools, execute them and feed the results back
3. Repeats until the model produces a text response

Four tools: `read_file`, `list_files`, `edit_file`, `run_bash`. One slash command: `/context` (shows token usage).

## Quickstart

```bash
# requires uv (https://docs.astral.sh/uv/)
git clone https://github.com/adevol/SimpleHarness && cd SimpleHarness
cp .env.example .env  # add your API key(s) after this to the .env file
uv run main.py
```

Override the model from config or CLI:

```bash
uv run main.py --model anthropic/claude-sonnet-4-20250514
```

## Why this exists

- **Education**: understand the agentic loop that powers real coding assistants
- **Experimentation baseline**: measure context usage and performance impact of adding skills, MCP servers, or custom tools

## License

MIT
