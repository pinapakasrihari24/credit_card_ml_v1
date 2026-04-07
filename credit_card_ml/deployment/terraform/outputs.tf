output "cloud_run_url" {
  description = "URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.app.uri
}

output "database_connection" {
  description = "Cloud SQL connection string"
  value       = google_sql_database_instance.postgres.connection_name
}

output "storage_bucket" {
  description = "Cloud Storage bucket for data files"
  value       = google_storage_bucket.data.url
}

output "artifact_registry" {
  description = "Artifact Registry URL"
  value       = google_artifact_registry_repository.docker.repository_url
}
