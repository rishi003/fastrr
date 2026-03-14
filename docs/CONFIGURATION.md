# Configuration

Fastrr uses LLM agents (via [Agno](https://github.com/agno-agi/agno)) for memory operations. Configuration is loaded from environment variables or a `.env` file.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FASTRR_PROVIDER` | LLM provider: `ollama` or `openrouter` | `ollama` |
| `FASTRR_MODEL` | Model ID | `llama3.2` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OPENROUTER_API_KEY` | API key for OpenRouter (required when `provider=openrouter`) | — |
| `FASTRR_MEMORY_TEMPLATE_PATH` | Path to a custom memory template JSON file. When unset, the built-in default template (`preferences.md`, `history.jsonl`, `facts.md`) is used. | — |

## Providers

### Ollama (default)

Runs models locally. Ensure [Ollama](https://ollama.ai) is installed and running.

```bash
# .env or export
FASTRR_PROVIDER=ollama
FASTRR_MODEL=llama3.2
OLLAMA_HOST=http://localhost:11434
```

### OpenRouter

Uses [OpenRouter](https://openrouter.ai) to access various models (OpenAI, Anthropic, etc.).

```bash
# .env or export
FASTRR_PROVIDER=openrouter
FASTRR_MODEL=openai/gpt-4o
OPENROUTER_API_KEY=sk-or-v1-...
```

## Memory Template

The memory workspace is initialised from a template on first use. The template declares which files exist and their purpose, so agents know exactly where to read and write without needing to call `list_files` at runtime.

The built-in default template contains three files:

| File | Purpose |
|------|---------|
| `preferences.md` | User preferences and settings |
| `history.jsonl` | Chronological entries (each line: `{"timestamp": ..., "type": ..., "content": ...}`) |
| `facts.md` | Standalone facts about the user |

To use a custom template, create a JSON file with the following structure and set `FASTRR_MEMORY_TEMPLATE_PATH`:

```json
{
  "files": [
    {"name": "preferences.md", "description": "User preferences and settings"},
    {"name": "notes.md", "description": "Freeform notes"}
  ]
}
```

```bash
FASTRR_MEMORY_TEMPLATE_PATH=/path/to/my_template.json
```

Or pass it directly at runtime:

```python
from fastrr.core.config import FastrrConfig
config = FastrrConfig(memory_template_path="/path/to/my_template.json")
memory = Fastrr(storage_path="./data/repo", config=config)
```

## Loading Order

1. Environment variables (highest precedence)
2. `.env` file in the current working directory
3. Defaults in `FastrrConfig`

## Overriding at Runtime

You can override configuration when constructing `Fastrr`:

```python
from fastrr import Fastrr
from fastrr.core.config import FastrrConfig

# Custom config
config = FastrrConfig(provider="openrouter", model="anthropic/claude-3-haiku")
memory = Fastrr(
    storage_path="./data/repo",
    config=config,
)
```

Or pass a custom Agno `Model` directly (takes precedence over config):

```python
from agno.models.openai import OpenAI
from fastrr import Fastrr

memory = Fastrr(
    storage_path="./data/repo",
    model=OpenAI(id="gpt-4o", api_key="sk-..."),
)
```
