FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# iproute2 provides `tc` for the Phase 5 netem evaluation harness.
# The container needs CAP_NET_ADMIN at runtime for tc to apply qdisc
# changes; see edge/docker-compose.yml syncd.cap_add.
RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY src/ src/
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
