# 📚 FastAPI + LangChain RAG Demo

A minimal **retrieval‑augmented generation (RAG)** service that runs entirely on **CPU**—perfect for local testing and effortless deployment to **Google Cloud Run**.

- **LLM**: `google/flan‑t5‑small` (≈80 MB)
- **Vector store**: FAISS (in‑memory, persisted to `/tmp`)
- **Embeddings**: `sentence‑transformers/all‑MiniLM‑L6‑v2`
- **Frameworks**: FastAPI · LangChain · Hugging Face Transformers

The service exposes three HTTP endpoints:

| Method | Path        | Description                               |
|--------|-------------|-------------------------------------------|
| POST   | `/predict`  | Dummy numeric prediction (example)        |
| GET    | `/generate` | Direct text generation with the LLM       |
| GET    | `/rag`      | Retrieval‑augmented QA (with fallback)    |

If no document is relevant, `/rag` returns a polite **“Sorry, I don't have enough information to answer that.”** message.

---

## 🚀 Quick Start (local, no Docker)

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Optional – point to your own knowledge base
export DOCS_DIR=/absolute/path/to/docs  # default is ./docs

python -m uvicorn main:app --reload --port 8080
```

```bash
# Smoke tests
curl -X POST http://localhost:8080/predict
curl "http://localhost:8080/generate?prompt=What%20is%20Cloud%20Run?"
curl "http://localhost:8080/rag?question=What%20does%20Flan‑T5%20stand%20for?"
```

---

## 🐳 Run inside Docker

```bash
# Build once
docker build -t demo-api:local .

# Run, exposing port 8080
# Mount your docs folder and pass DOCS_DIR env var (optional)
docker run --rm -p 8080:8080   -v $(pwd)/docs:/app/docs   -e DOCS_DIR=/app/docs   demo-api:local
```

*Hint:* mount `~/.cache/huggingface` if you want to reuse model weights across runs.

---

## ☁️ Deploy on Google Cloud Run (via Cloud Build trigger)

1. **Artifact Registry** repo already set up (`demo-repo`).
2. Push to `main` → Cloud Build:
   * builds the container
   * pushes it to Artifact Registry
   * deploys it to Cloud Run (`europe‑west1`)
3. Fetch the live URL:
   ```bash
   gcloud run services describe demo-api      --region europe-west1      --format="value(status.url)"
   ```

> Adjust region or memory in `cloudbuild.yaml` as needed.

---

## 🗂️ Knowledge‑base files

Place **`.txt`, `.md`, or `.pdf`** files inside the folder pointed to by `DOCS_DIR` (default `./docs/`).

Example download script:
```bash
bash scripts/bootstrap_docs.sh   # populates docs/ with three sample files
```

The app indexes (or reloads) documents at startup; no restart is needed for *uvicorn --reload*.

---

## 🔌 Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DOCS_DIR` | `docs` | Path (inside container or host) to the folder with knowledge documents |
| `PORT`     | `8080` | Cloud Run listens on this port |

---

## 📖 API Reference

### `/generate`
```
GET /generate?prompt=Translate"Hello"toSpanish
```
Response
```json
{
  "prompt": "Translate "Hello" to Spanish",
  "completion": "Hola"
}
```

### `/rag`
```
GET /rag?question=What+is+Cloud+Run?
```
Response
```json
{
  "question": "What is Cloud Run?",
  "answer": "Cloud Run is a fully‑managed Knative‑based platform that runs stateless containers and scales to zero, charging only while requests are processed.",
  "sources": ["cloud_run.md"]
}
```

---

## 🛠️ Project Structure
```
.
├── main.py               # FastAPI + LangChain app
├── Dockerfile            # Container definition
├── cloudbuild.yaml       # Build + push + deploy pipeline
├── requirements.txt      # Python deps
├── docs/                 # (your knowledge base files)
└── README.md             # ← you are here
```

---

## 📝 License & Credits

* Code: MIT
* Models & embeddings: Apache‑2.0 / respective upstream licences (see their model cards)
* Sample docs: MIT, Apache‑2.0, CC‑BY‑SA 3.0

> Built with ❤️ using FastAPI, Hugging Face, LangChain and Google Cloud.