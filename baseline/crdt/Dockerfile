FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY crdt_lww.py replica.py ./
EXPOSE 8000
CMD ["uvicorn", "replica:app", "--host", "0.0.0.0", "--port", "8000"]
