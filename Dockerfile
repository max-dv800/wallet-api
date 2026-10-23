FROM python:3.14-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /wallet-api

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . .

RUN  --mount=type=cache,target=/root/.cache/uv \
     uv sync --locked --no-dev

FROM python:3.14-slim-bookworm

WORKDIR /wallet-api

COPY --from=builder /wallet-api/.venv /wallet-api/.venv
COPY --from=builder /wallet-api/src /wallet-api/src
COPY --from=builder /wallet-api/migrations /wallet-api/migrations
COPY --from=builder /wallet-api/alembic.ini /wallet-api/alembic.ini

ENV PATH="/wallet-api/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "wallet_api.main:app", "--host", "0.0.0.0", "--port", "8000"]