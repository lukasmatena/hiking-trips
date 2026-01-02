output "current_workspace" {
  value = terraform.workspace
}

output "current_project" {
  value = "${var.project_id}"
}

output "backend_url" {
  description = "URL of the Cloud Run backend"
  value       = google_cloud_run_v2_service.backend.uri
}

output "artifact_registry_repo" {
  description = "Run 'docker push' to this location"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend_repo.name}"
}

output "db_connection_name" {
  description = "Instance connection name for Cloud SQL (used in proxies)"
  value       = google_sql_database_instance.main.connection_name
}

output "firebase_app_id" {
  description = "The App ID for your frontend config"
  value       = google_firebase_web_app.frontend.app_id
}

output "workload_identity_provider" {
  description = "The WIF Provider ID. Copy this into your GitHub Actions YAML (WIF_PROVIDER)."
  value       = google_iam_workload_identity_pool_provider.github_provider.name
}

output "github_actions_email" {
  description = "The Service Account email used by GitHub. Copy this into your GitHub Actions YAML (WIF_SERVICE_ACCOUNT)."
  value       = google_service_account.github_actions.email
}