# 📚 FastAPI + LangChain RAG Demo (gpt4free edition)

A lightweight **retrieval‑augmented generation (RAG)** micro‑service you can run on any laptop (CPU‑only) or deploy cheaply to **Google Cloud Run**—with **no LLM API key** required.  
It embeds your local documents with **sentence‑transformers**, stores them in **FAISS**, retrieves the most relevant chunks, and asks **gpt4free** (GPT‑4‑class) to craft an answer.

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
yes | pip install --upgrade pip
pip install "fastapi[all]" uvicorn sentence-transformers langchain langchain-community
pip install --no-binary :all: g4f --upgrade   # g4f sometimes needs --no-binary

# 3 – run the API with auto‑reload
python -m uvicorn rag_demo_fastapi:app --reload --port 8080
```

Drop **`.pdf`, `.txt`, `.md` …** into **`./documents/`** and the server will auto‑reload and re‑index them.

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
# 0 – choose IDs up front ------------------------------------------------------
export PROJECT_ID="your-project-$(date +%s)"   # e.g. drius-ai-run-1718123456
export REGION="europe-west1"                   # pick any Cloud Run region

# 1 – list billing accounts and pick one --------------------------------------
gcloud beta billing accounts list
export BILLING_ID="0123A4-B5C6D7-89EF01"       # replace with your account ID

# 2 – create & link the project ----------------------------------------------
gcloud projects create $PROJECT_ID --name="rag-demo"
gcloud beta billing projects link $PROJECT_ID \
  --billing-account=$BILLING_ID

# 3 – (optional) set a budget so you never overspend --------------------------
gcloud beta billing budgets create \
  --billing-account=$BILLING_ID \
  --display-name="demo-limit" \
  --budget-amount=5EUR

# 4 – enable required services ------------------------------------------------
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

# 5 – configure gcloud defaults ----------------------------------------------
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION

# 6 – create an Artifact Registry repo (once) ---------------------------------
gcloud artifacts repositories create rag-demo-repo \
  --repository-format=docker \
  --location=$REGION

# 7 – build & push the container ---------------------------------------------
gcloud builds submit \
  --tag $REGION-docker.pkg.dev/$PROJECT_ID/rag-demo-repo/rag-demo:latest

# 8 – deploy to Cloud Run ------------------------------------------------------
gcloud run deploy rag-demo \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/rag-demo-repo/rag-demo:latest \
  --region=$REGION \
  --platform=managed \
  --memory=1Gi \
  --min-instances=0 \
  --max-instances=3 \
  --allow-unauthenticated

# 9 – grab the HTTPS URL -------------------------------------------------------
gcloud run services describe rag-demo --region=$REGION --format="value(status.url)"
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
| `CHUNK_SIZE`  | 800 chars | Coherence vs. recall |
| `K`           | 8 chunks | Context depth vs. prompt size |
| `MAX_TOKENS`  | 256 | Response length (provider limits vary) |
| `EMBED_MODEL` | MiniLM-L6-v2 | Swap for higher accuracy / slower speed |
| `VECTOR_PATH` | `./faiss_index` | Where FAISS index is persisted |

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

> Built with ❤️ using FastAPI, LangChain, and a pinch of guerrilla GPT‑4 power.
