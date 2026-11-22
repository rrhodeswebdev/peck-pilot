FROM node:22-bookworm
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /uvx /bin/
# OCP (OpenCascade) loads libGL even headless
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 && rm -rf /var/lib/apt/lists/*
