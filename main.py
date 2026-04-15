"""
SimpleHarness — a minimal coding agent CLI.
Based on https://www.mihaileric.com/The-Emperor-Has-No-Clothes/

Usage:
    uv run main.py [--model MODEL] [--config CONFIG]

Any litellm model string works (provided the required API keys are set), e.g.:
    --model ollama/mistral
    --model gemini/gemini-1.5-flash
    --model anthropic/claude-3-5-haiku-20241022
"""

import argparse, json, subprocess, litellm, yaml
from pathlib import Path

COLORS = {"you": 94, "assistant": 93, "tool": 32, "dim": 2, "error": 31}
def c(role, text): return f"\033[{COLORS[role]}m{text}\033[0m"

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

def list_files(directory: str = ".") -> str:
    entries = sorted(Path(directory).iterdir(), key=lambda p: (p.is_file(), p.name))
    return "\n".join(("  " if e.is_file() else "[D] ") + e.name for e in entries) or "(empty)"

def edit_file(path: str, content: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Successfully wrote {path}"

def run_bash(command: str) -> str:
    r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
    return (r.stdout + r.stderr).strip() or "(no output)"

def tool(func, desc, *params):
    schema = {"type": "function", "function": {
        "name": func.__name__, "description": desc,
        "parameters": {"type": "object",
                       "properties": {p: {"type": "string"} for p in params},
                       "required": list(params)}}}
    return func.__name__, (func, schema)

TOOLS = dict([
    #tool(read_file,  "Read a file.",             "path"),
    #tool(list_files, "List a directory.",        "directory"),
    #tool(edit_file,  "Write content to a file.", "path", "content"),
    tool(run_bash,   "Run a shell command.",     "command"),
])

def runtool(name: str, args: dict) -> str:
    if name not in TOOLS:
        return f"Error: unknown tool: {name}"
    try:
        return TOOLS[name][0](**args)
    except Exception as e:
        return f"Error: {e}"

# ---------------------------------------------------------------------------
# Slash commands
# ---------------------------------------------------------------------------

def count(model, messages):
    return litellm.token_counter(model=model, messages=messages)

def cmd_context(messages, model):
    window = (litellm.get_model_info(model) or {}).get("max_input_tokens") or 0
    used = count(model, messages)
    pct = f" ({used / window * 100:.1f}%)" if window else ""
    print(c("dim", f"  window: {window or '?'}  |  used: {used:,}{pct}"))
    for role in ("system", "user", "assistant", "tool"):
        msgs = [m for m in messages if m.get("role") == role]
        if msgs:
            print(c("dim", f"    {role:<10} {count(model, msgs):>7,}  ({len(msgs)} msg)"))
    print()

COMMANDS = {"/context": cmd_context}

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def call_model(model: str, messages: list[dict]) -> dict:
    resp = litellm.completion(model=model, messages=messages, tools=[t[1] for t in TOOLS.values()])
    return resp.choices[0].message.model_dump()

def main() -> None:
    parser = argparse.ArgumentParser(description="SimpleHarness: a tiny coding agent CLI")
    parser.add_argument("--model", default=None, help="litellm model string (overrides config)")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config file")
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    COLORS.update(cfg.get("colors", {}))
    model = args.model or cfg["model"]
    litellm.suppress_debug_info = True

    print(c("dim", f"SimpleHarness  |  model: {model}  (ctrl-c to quit)") + "\n")
    messages = [{"role": "system", "content": cfg["system_prompt"].strip()}]

    while True:
        try:
            prompt = input(c("you", "You: ")).strip()
        except (KeyboardInterrupt, EOFError):
            print(); break
        if not prompt:
            continue
        if prompt in ("exit", "quit", "q"):
            break
        if prompt in COMMANDS:
            COMMANDS[prompt](messages, model)
            continue
        messages.append({"role": "user", "content": prompt})
        # agent loop: keep going until the model stops calling tools
        try:
            while True:
                reply = call_model(model, messages)
                messages.append(reply)
                if not reply.get("tool_calls"):
                    print(f"\n{c('assistant', 'Agent:')} {reply.get('content', '')}\n"); break
                for tc in reply["tool_calls"]:
                    name = tc["function"]["name"]
                    tool_args = json.loads(tc["function"]["arguments"])
                    short = ", ".join(f"{k}={repr(v)[:50]}" for k, v in tool_args.items())
                    print(c("tool", f"  [{name}]") + c("dim", f"({short})"))
                    result = runtool(name, tool_args)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
        except Exception as e:
            print(c("error", f"  [error] {type(e).__name__}: {e}\n"))

if __name__ == "__main__":
    main()
