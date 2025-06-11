# ---- base image ----
FROM python:3.12-slim

# install gcc for some wheels that need compilation (g4f, sentence-transformers)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# ---- python deps ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge

# ---- app code ----
COPY . /app
WORKDIR /app

# ---- runtime ----
ENV PORT=8080
EXPOSE 8080
CMD ["uvicorn", "rag_demo_fastapi:app", "--host", "0.0.0.0", "--port", "8080"]
