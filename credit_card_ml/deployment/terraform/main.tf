provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "postgres" {
  name             = "credit-card-db"
  database_version = "POSTGRES_15"
  region           = var.region

  settings {
    tier = "db-f1-micro"
    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "all"
        value = "0.0.0.0/0"
      }
    }
  }
}

# Database
resource "google_sql_database" "database" {
  name     = "creditcard"
  instance = google_sql_database_instance.postgres.name
}

# User
resource "google_sql_user" "user" {
  name     = var.db_user
  instance = google_sql_database_instance.postgres.name
  password = var.db_password
}

# Cloud Storage Bucket for CSV files
resource "google_storage_bucket" "data" {
  name     = "${var.project_id}-credit-card-data"
  location = var.region
}

# Artifact Registry
resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = "credit-card-fraud"
  description   = "Docker repository for credit card fraud detection"
  format        = "DOCKER"
}

# Cloud Run Service
resource "google_cloud_run_v2_service" "app" {
  name     = "credit-card-fraud"
  location = var.region

  template {
    service_account = google_service_account.app.email

    scales {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = "gcr.io/${var.project_id}/credit-card-fraud:latest"
      ports {
        container_port = 8080
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
      env {
        name  = "DATABASE_URL"
        value = "postgresql://${var.db_user}:${var.db_password}@//cloudsql/${var.project_id}:${var.region}:creditcard?host=/cloudsql/${var.project_id}:${var.region}:creditcard"
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.serverless.id
    }
  }
}

# VPC Connector for Cloud Run to Cloud SQL
resource "google_vpc_access_connector" "serverless" {
  name          = "serverless-vpc"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = "default"
}

# Service Account
resource "google_service_account" "app" {
  account_id   = "credit-card-app"
  display_name = "Credit Card Fraud App"
}

# Permissions
resource "google_project_iam_member" "app_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app.email}"
}

resource "google_project_iam_member" "app_storage" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Allow public access
resource "google_cloud_run_v2_service_iam_member" "app_allUsers" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
