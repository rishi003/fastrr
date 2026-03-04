# Integration tests

End-to-end tests for the Fastrr client using a real Git repo and real Ollama.

## Requirements

- **Ollama** running with the configured model (default: `qwen3.5:9b`).  
  Example: `ollama run qwen3.5:9b` once to pull and run the model.
- **Git** available on the path (tests create temporary repos).

## Run

```bash
# From repo root
uv run pytest tests_intg/ -v
```

To run only integration tests when multiple test dirs exist:

```bash
uv run pytest tests_intg/ -v -m integration
```

To exclude integration tests (e.g. in CI without Ollama):

```bash
uv run pytest tests/ -v -m "not integration"
```

## Configuration

- Model is read from `FASTRR_MODEL` (default: `qwen3.5:9b`).
- Ollama host from `OLLAMA_HOST` (default: `http://localhost:11434`).

If Ollama is unreachable or the model is not present, tests are skipped with a clear message.
