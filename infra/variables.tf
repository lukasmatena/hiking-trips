variable "project_id" {
  description = "The GCP Project ID (not the name)"
  type        = string
}

variable "region" {
  description = "The default GCP region for resources"
  type        = string
  default     = "europe-west1"
}

variable "environment" {
  description = "The environment name (e.g., stage, prod)"
  type        = string
}

variable "terraform_sa_email" {
  description = "The Service Account email used to deploy this environment"
  type        = string
}
