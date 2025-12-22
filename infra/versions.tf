terraform {
  # This constraint requires Terraform 1.0 or later
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      # Version 5.0+ is required for some modern Cloud Run v2 features
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      # Beta provider is needed for Firebase resources currently
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}
