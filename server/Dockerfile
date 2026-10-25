# UpdateApply API — production image (Python 3.14 + uv).
# Build from this directory: `docker build -t updateapply-api .`
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Dependency layer (cached until lock/pyproject change).
# README.md is referenced by pyproject.toml (readme = "README.md").
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Application source (see .dockerignore).
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen \
    && mkdir -p data/uploads data/locks data/logs

EXPOSE 8000

# Migrations run once per deploy via fly.toml [deploy].release_command
# (avoids multi-machine races). Do not use `uv run app` here — that entrypoint
# enables uvicorn --reload for local dev.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
