FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Copy dependency specifications
COPY pyproject.toml uv.lock* ./

# Install dependencies into virtualenv
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source
COPY . .

# Final stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Copy virtualenv and application
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Non-root user for security
RUN chmod +x /app/scripts/start.sh && useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request, os; urllib.request.urlopen('http://localhost:' + os.environ.get('PORT', '8000') + '/health')" || exit 1

CMD ["/app/scripts/start.sh"]

