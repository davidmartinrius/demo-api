# 📚 FastAPI + LangChain RAG Demo (gpt4free edition)

A lightweight **retrieval‑augmented generation (RAG)** micro‑service you can run on any laptop (CPU‑only) or deploy cheaply to **Google Cloud Run**—with **no LLM API key** required.  
It embeds your local documents with **sentence‑transformers**, stores them in **FAISS**, retrieves the most relevant chunks, and asks **gpt4free** (GPT‑4‑class) to craft an answer.

---

[![Demo video](https://img.youtube.com/vi/qDrYGK2p-Co/hqdefault.jpg)](https://youtu.be/qDrYGK2p-Co)

> **Watch:** *27-minute walkthrough — goals, live Cloud Run demo, code tour, CI/CD, and improvement ideas.*

---

## ✨ Stack at a glance

| Layer | Component |
|-------|-----------|
| **LLM**        | *gpt4free* (auto‑selects a live GPT‑4 endpoint) |
| **Embeddings** | `sentence‑transformers/all‑MiniLM‑L6‑v2` |
| **Vector DB**  | FAISS (persisted on disk) |
| **Frameworks** | FastAPI · LangChain |
| **Docs folder**| `./documents/` (next to `rag_demo_fastapi.py`) |

Default knobs: **chunk = 800 chars**, **top‑k = 8**, **max_tokens = 256** – all configurable at the top of the script.

---

## 🚀 Quick start (local)

```bash
# 1 – (optional) create a virtual‑env
python -m venv .venv && source .venv/bin/activate

# 2 – install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3 – run the API (pick one)

# 3 a) via Uvicorn CLI — easiest to tweak flags
uvicorn rag_demo_fastapi:app --reload --port 8080

# 3 b) or simply run the file (hard-coded host/port)
python rag_demo_fastapi.py
```

Add new **`.pdf`, `.txt`, `.md` …** into **`./documents/`**, then restart the server or container to rebuild the FAISS index and include the new content.

---

## 🐳 Run with Docker (local)

Prefer containers?  Build the image once and run it locally—no Python or
virtual‑env required.

```bash
# build (uses the Dockerfile in the repo root)
docker build -t rag-demo:local .

# run the container exposing port 8080
#   - mount ./documents into /app/documents so you can edit docs without rebuilds
#   - faiss_index will be written inside the container

docker run --rm -p 8080:8080 \
  -v $(pwd)/documents:/app/documents \
  rag-demo:local
```

---

## 🔗 Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/generate?prompt=…`  | Raw chat completion via *gpt4free* |
| `GET`  | `/rag?question=…`    | Retrieval‑augmented answer sourced from your docs |
| `GET`  | `/ingested_docs`     | JSON preview of the indexed documents |

Examples:

```bash
curl "http://localhost:8080/generate?prompt=Hello%2C+who+are+you%3F"

curl "http://localhost:8080/rag?question=Which+programming+languages+are+mentioned%3F"
```

---

## ☁️ Deploy to Google Cloud Run (step‑by‑step)

> These commands create a brand‑new project, link billing, set a spending cap, build the image with Cloud Build, push to Artifact Registry, and deploy to Cloud Run.

```bash
# 0 – Define project and region
export PROJECT_ID="rag-demo-$(date +%s)"
export REGION="europe-west1"

# 1 – Pick a billing account
gcloud beta billing accounts list
export BILLING_ID="XXX-YYY-ZZZ"  # replace with your actual billing ID

# 2 – Create project and link billing
gcloud projects create $PROJECT_ID --name="rag-demo"
gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ID

# 3 – (Optional) Set a budget limit
gcloud beta billing budgets create \
  --billing-account=$BILLING_ID \
  --display-name="demo-limit" \
  --budget-amount=5EUR

# 4 – Enable required APIs
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

# 5 – Configure gcloud defaults
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# 6 – Create Artifact Registry (if not exists)
gcloud artifacts repositories create rag-demo-repo \
  --repository-format=docker \
  --location=$REGION

# 7 – Build & push using Cloud Build
gcloud builds submit \
  --config=.cloudbuild.yaml \
  --substitutions=_REGION=$REGION,_REPO=rag-demo-repo,_TAG=latest

# 8 – Get the public service URL
gcloud run services describe rag-demo \
  --region=$REGION \
  --format="value(status.url)"
```

**What each step does**

| Step | Purpose |
|------|---------|
| 0‑1 | Pick names & billing account. |
| 2   | Creates a new GCP project and links billing. |
| 3   | Sets a hard budget cap (optional but recommended). |
| 4   | Enables Cloud Run, Cloud Build, Artifact Registry, Logging, Monitoring. |
| 5   | Sets gcloud defaults so you don’t repeat flags. |
| 6   | Creates a private Docker repo in Artifact Registry. |
| 7   | Cloud Build builds the Dockerfile and pushes the image. |
| 8   | Deploys the container to Cloud Run with 0 → 3 autoscaling instances. |
| 9   | Prints the public HTTPS endpoint. |

After deployment, test:
```bash
curl "$RAG_URL/rag?question=What+is+this+service%3F"
```

---

## ⚙️ Tunable settings

| Constant      | Default | Why it matters |
|---------------|---------|----------------|
| `CHUNK_SIZE`  | 800 chars | Size of each document split |
| `K`           | 8 chunks | Number of chunks retrieved for context |
| `MAX_TOKENS`  | 256 | LLM response limit |
| `EMBED_MODEL` | MiniLM-L6-v2 | Embedding model from sentence-transformers |
| `VECTOR_PATH` | `./faiss_index` | Path where FAISS index is saved |

---

## 🗂️ Project structure
```
.
├── rag_demo_fastapi.py   # FastAPI + LangChain application
├── Dockerfile            # container definition (see docs)
├── cloudbuild.yaml       # optional CI/CD pipeline
├── documents/            # ← put your knowledge base here
├── faiss_index/          # auto‑generated FAISS files
└── README.md             # you are here
```

---

## 📜 License & credits

* Code: MIT
* gpt4free: © xtekky (GPL‑3) — use responsibly
* Sentence‑transformers & FAISS: Apache‑2.0

> Developed using FastAPI and LangChain, with open-source tools that enable GPT‑4-level performance without proprietary APIs.

