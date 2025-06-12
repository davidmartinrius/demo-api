#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# 0) Sanity-check required env vars
###############################################################################

: "${PROJECT_ID:=$(gcloud config get-value project)}"
: "${REGION:=$(gcloud config get-value run/region)}"

if [[ -z "$PROJECT_ID" || -z "$REGION" ]]; then
  echo "❌ PROJECT_ID or REGION not set and could not be auto-detected from gcloud config."
  exit 1
fi

echo "🔧 Using PROJECT_ID=$PROJECT_ID and REGION=$REGION"

# Assign BILLING_ID if not already set
: "${BILLING_ID:=$(gcloud beta billing accounts list \
  --filter="OPEN=true" \
  --format="value(name)" | head -n1)}"

if [[ -z "$BILLING_ID" ]]; then
  echo "❌ No OPEN billing account found. Run 'gcloud beta billing accounts list'."
  exit 1
fi

###############################################################################
# 1) Project + billing (idempotent) ───────────────────────────────────────────
###############################################################################
if gcloud projects describe "$PROJECT_ID" &>/dev/null; then
  echo "✓ Project $PROJECT_ID already exists – skipping create"
else
  echo "➜ Creating project $PROJECT_ID …"
  gcloud projects create "$PROJECT_ID" --name="rag-demo"
fi

if gcloud beta billing projects describe "$PROJECT_ID" &>/dev/null; then
  echo "✓ Billing already linked"
else
  echo "➜ Linking billing account…"
  gcloud beta billing projects link "$PROJECT_ID" --billing-account="$BILLING_ID"
fi

###############################################################################
# 2) Budget cap (skip if present) ─────────────────────────────────────────────
###############################################################################
if gcloud beta billing budgets list --billing-account="$BILLING_ID" \
     --format="value(displayName)" | grep -q "^demo-limit$"; then
  echo "✓ Budget cap demo-limit already exists"
else
  echo "➜ Creating 5 € budget cap…"
  gcloud beta billing budgets create \
    --billing-account="$BILLING_ID" \
    --display-name="demo-limit" \
    --budget-amount=5EUR
fi

###############################################################################
# 3) Enable services (idempotent) ─────────────────────────────────────────────
###############################################################################
echo "➜ Enabling required APIs (no-op if already enabled)…"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com

###############################################################################
# 4) gcloud defaults ──────────────────────────────────────────────────────────
###############################################################################
gcloud config set project "$PROJECT_ID"
gcloud config set run/region "$REGION"

###############################################################################
# 5) Artifact Registry repo (idempotent) ──────────────────────────────────────
###############################################################################
if gcloud artifacts repositories describe rag-demo-repo \
     --location="$REGION" &>/dev/null; then
  echo "✓ Artifact repo rag-demo-repo already exists"
else
  echo "➜ Creating Artifact Registry repo rag-demo-repo…"
  gcloud artifacts repositories create rag-demo-repo \
    --repository-format=docker \
    --location="$REGION"
fi

###############################################################################
# 6) Build → push → deploy via Cloud Build ────────────────────────────────────
###############################################################################
echo "➜ Submitting Cloud Build (docker build → push → deploy)…"
gcloud builds submit \
  --config=.cloudbuild.yaml \
  --substitutions=_REGION=$REGION,_REPO=rag-demo-repo,_TAG=$(git rev-parse --short HEAD)

###############################################################################
# 7) Fetch URL & test ─────────────────────────────────────────────────────────
###############################################################################
export RAG_URL=$(gcloud run services describe rag-demo \
  --region="$REGION" \
  --format="value(status.url)")

echo "➜ Service deployed at: $RAG_URL"
echo "➜ Smoke testing…"
curl -s "$RAG_URL/ingested_docs" | head -c 120 && echo -e "…\n"
curl -s "$RAG_URL/generate?prompt=Hello%20GPT4"
echo
curl -s "$RAG_URL/rag?question=What+is+a+transformer%3F"
echo

echo "✅  All done!"
