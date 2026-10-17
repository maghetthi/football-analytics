# Build from the repository root:  docker build -f services/api/Dockerfile -t football-api .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# Install only what serving needs (no mlflow, dbt or prefect).
COPY pyproject.toml ./
COPY services ./services
RUN pip install ".[api,ml-serve]"

COPY models ./models
ENV ARTIFACTS_DIR=/app/models

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/health', timeout=2)"
CMD ["sh", "-c", "uvicorn football_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
