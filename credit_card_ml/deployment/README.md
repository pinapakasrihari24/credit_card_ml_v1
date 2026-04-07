# Credit Card ML - GCP Deployment

## Architecture
- **Cloud Run**: Flask web application (serverless, auto-scaling)
- **Cloud SQL**: PostgreSQL database (managed, high availability)
- **Cloud Storage**: CSV data files storage
- **Artifact Registry**: Docker container registry

## Files
```
deployment/
├── Dockerfile              # Container image
├── cloudbuild.yaml        # CI/CD pipeline
├── terraform/
│   ├── main.tf            # Infrastructure
│   ├── variables.tf       # Variables
│   └── outputs.tf         # Outputs
├── scripts/
│   ├── deploy.sh          # Deployment script
│   └── init_db.py         # Database initialization
└── .env.example           # Environment template
```

## Quick Deploy
```bash
cd deployment
./scripts/deploy.sh
```

## Manual Deploy
```bash
# Build and push
gcloud builds submit --config=cloudbuild.yaml

# Deploy to Cloud Run
gcloud run deploy credit-card-fraud \
  --image=gcr.io/$PROJECT_ID/credit-card-fraud:latest \
  --platform=managed \
  --region=us-central1 \
  --add-cloudsql-instances=$INSTANCE_CONNECTION_NAME \
  --set-env-vars="DATABASE_URL=postgresql://$USER:$PASS@/$DB?host=/cloudsql/$CONNECTION""
```
