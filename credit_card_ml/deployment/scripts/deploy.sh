#!/bin/bash
set -e

echo "============================================="
echo "Credit Card Fraud Detection - GCP Deployment"
echo "============================================="

# Configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
SERVICE_NAME="credit-card-fraud"
REGION="us-central1"
REPO_NAME="credit-card-fraud"
IMAGE="gcr.io/$PROJECT_ID/$REPO_NAME"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID not set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Step 1: Enable required APIs
echo ""
echo "[1/5] Enabling GCP APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    sqladmin.googleapis.com \
    artifactregistry.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --quiet

# Step 2: Create Artifact Registry repository
echo ""
echo "[2/5] Creating Artifact Registry repository..."
gcloud artifacts repositories create $REPO_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Credit Card Fraud Detection app" \
    2>/dev/null || echo "Repository already exists"

# Step 3: Build and push Docker image
echo ""
echo "[3/5] Building Docker image..."
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions=COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest") \
    --project=$PROJECT_ID

# Get the image URL
IMAGE_URL="$IMAGE:latest"

# Step 4: Deploy to Cloud Run
echo ""
echo "[4/5] Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_URL \
    --region=$REGION \
    --platform=managed \
    --memory=512Mi \
    --cpu=1 \
    --concurrency=1000 \
    --max-instances=10 \
    --allow-unauthenticated \
    --project=$PROJECT_ID

# Step 5: Get the service URL
echo ""
echo "[5/5] Deployment complete!"
echo ""
echo "============================================="
echo "Cloud Run URL:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)"
echo "============================================="
