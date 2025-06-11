"""FastAPI + LangChain RAG (gpt4free, clean build)
================================================
A minimal yet functional RAG micro-service that:
* Embeds local docs with **sentence-transformers** (FAISS index on disk).
* Retrieves the top-k chunks and feeds them to **gpt4free** (GPT-4 quality) to
  craft an answer.

No API keys needed – `g4f` automatically picks a free provider.

Quick start
-----------
```bash
pip install "fastapi[all]" uvicorn sentence-transformers langchain
pip install g4f  # may need: pip install --no-binary :all: g4f --upgrade
python -m uvicorn rag_demo_fastapi:app --reload --port 8080
```

Endpoints
---------
* **GET /generate?prompt=…** – plain GPT-4 chat completion.
* **GET /rag?question=…**   – Retrieval-Augmented answer over your docs.
* **GET /ingested_docs**    – quick preview of indexed docs.
"""
from __future__ import annotations

import logging
import os
import pathlib
import random
from typing import List

import torch
from fastapi import FastAPI, Query
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS

import g4f  # GPT-4-free chat backend

# ─────────────────────────── Config & logging ────────────────────────────────
ROOT = pathlib.Path(__file__).parent
DOCS_DIR = ROOT / "documents"
VECTOR_PATH = pathlib.Path(os.getenv("VECTOR_PATH", ROOT / "faiss_index"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = 800
K = 8  # retrieved chunks
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "256"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("rag_demo_g4f_clean")

# ───────────────────────────── Doc loading ───────────────────────────────────

TEXT_SUFFIXES = {".txt", ".md", ".rst", ".log", ".csv"}

def loader_for(path: pathlib.Path):
    if path.suffix.lower() == ".pdf":
        return PyPDFLoader(str(path))
    if path.suffix.lower() in TEXT_SUFFIXES:
        return TextLoader(str(path), encoding="utf-8", errors="ignore")
    return None  # skip binaries


def load_documents(root: pathlib.Path) -> List[Document]:
    if not root.exists():
        log.warning("%s missing – using fallback docs", root)
        return [
            Document("This is a fallback document. Add PDFs or TXT files to ./docs to improve answers.", metadata={"source": "fallback"}),
        ]

    loader = DirectoryLoader(
        str(root),
        glob="**/*",
        loader_cls=lambda p: loader_for(pathlib.Path(p)) or TextLoader("", encoding="utf-8"),
        use_multithreading=True,
    )
    docs = loader.load()
    log.info("Loaded %d raw docs from %s", len(docs), root)
    return docs


raw_docs = load_documents(DOCS_DIR)

# ───────────────────────────── Embeddings / FAISS ────────────────────────────
embedder = HuggingFaceEmbeddings(model_name=EMBED_MODEL, cache_folder="/tmp/hf_cache")
splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=100)
chunks = splitter.split_documents(raw_docs)

if VECTOR_PATH.exists():
    db = FAISS.load_local(str(VECTOR_PATH), embedder, allow_dangerous_deserialization=True)
    log.info("Loaded FAISS index from %s", VECTOR_PATH)
else:
    db = FAISS.from_documents(chunks, embedder)
    db.save_local(str(VECTOR_PATH))
    log.info("Built & saved new FAISS index (%d chunks)", len(chunks))

retriever = db.as_retriever(search_kwargs={"k": K})

# ──────────────────────── g4f async wrapper ──────────────────────────────────
async def gpt4_chat(prompt: str) -> str:
    """Return GPT-4 response or fallback message."""
    try:
        response = await g4f.ChatCompletion.create_async(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=MAX_TOKENS,
        )
        return response.strip()
    except Exception as exc:
        log.error("g4f failure: %s", exc)
        return "I don't know."

# ───────────────────────────── FastAPI app ───────────────────────────────────
app = FastAPI(title="RAG Demo (gpt4free)")

def _sorry(q: str):
    return {"question": q, "answer": "I don't know.", "sources": []}

# -------- Simple completion --------------------------------------------------
@app.get("/generate")
async def generate(prompt: str = Query(..., min_length=1)):
    answer = await gpt4_chat(prompt)
    return {"prompt": prompt, "completion": answer}

# -------- RAG ----------------------------------------------------------------
@app.get("/rag")
async def rag(question: str = Query(..., min_length=1)):
    docs = retriever.get_relevant_documents(question)
    if not docs:
        return _sorry(question)

    context = "\n\n".join(d.page_content for d in docs)

    rag_prompt = (
        "You are a helpful assistant. Read the context and answer the question. "
        "List all relevant facts you find. If the answer is not contained, reply that you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}\nAnswer:"
    )

    answer = await gpt4_chat(rag_prompt)

    if answer.lower().startswith("i don't know") or not answer.strip():
        return _sorry(question)

    srcs = list({d.metadata.get("source", "unknown") for d in docs})
    return {"question": question, "answer": answer, "sources": srcs}

# -------- Inspect docs -------------------------------------------------------
@app.get("/ingested_docs")
async def ingested_docs(limit: int = Query(50, ge=1)):
    out = []
    for i, d in enumerate(raw_docs[:limit]):
        out.append({
            "id": i,
            "source": d.metadata.get("source", "unknown"),
            "chars": len(d.page_content),
            "preview": d.page_content[:160].replace("\n", " ") + ("…" if len(d.page_content) > 160 else ""),
        })
    return {"total": len(raw_docs), "shown": len(out), "docs": out}

# -------- CLI entry ----------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("rag_demo_fastapi:app", host="0.0.0.0", port=8080, reload=True)
