# Configuration

Fastrr uses LLM agents (via [Agno](https://github.com/agno-agi/agno)) for memory operations. Configuration is loaded from environment variables or a `.env` file.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FASTRR_PROVIDER` | LLM provider: `ollama` or `openrouter` | `ollama` |
| `FASTRR_MODEL` | Model ID | `llama3.2` |
| `OLLAMA_HOST` | Ollama server URL | `http://localhost:11434` |
| `OPENROUTER_API_KEY` | API key for OpenRouter (required when `provider=openrouter`) | — |

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
    worktree_root="./data/users",
    config=config,
)
```

Or pass a custom Agno `Model` directly (takes precedence over config):

```python
from agno.models.openai import OpenAI
from fastrr import Fastrr

memory = Fastrr(
    storage_path="./data/repo",
    worktree_root="./data/users",
    model=OpenAI(id="gpt-4o", api_key="sk-..."),
)
```
