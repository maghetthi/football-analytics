# Build from the repository root:  docker build -f services/dashboard/Dockerfile -t football-dashboard .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY pyproject.toml ./
COPY services ./services
RUN pip install ".[dashboard]"

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8501
CMD ["sh", "-c", "streamlit run services/dashboard/app.py --server.port ${PORT:-8501} --server.address 0.0.0.0 --server.headless true"]
