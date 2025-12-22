# ==============================================================================
# INFRASTRUCTURE SETUP & DEPLOYMENT GUIDE
# ==============================================================================
#
# PREREQUISITES:
# - Google Cloud Account
# - Installed: GCloud CLI, Terraform
#
# ARCHITECTURE ASSUMPTIONS:
# - PROD Project:  Empty project [Firebase enabled] (ID goes to envs/prod.tfvars)
# - STAGE Project: Empty project [Firebase enabled] (ID goes to envs/stage.tfvars)
# - STATE Project: Separate 'admin' project containing the State Bucket.
#                  (Bucket ID goes into backend.tf)
#
# STRATEGY:
# Separation relies on Terraform Workspaces (logical isolation).
# Both Stage and Prod share one state bucket (physical sharing).
#
# ==============================================================================
# PART 1: INITIAL SETUP (One-Time)
# ==============================================================================
#
# A. SERVICE ACCOUNTS
#    1. Create a Service Account (SA) in BOTH Stage and Prod projects.
#    2. Assign the following roles to each SA in their respective project:
#       - 'Editor'
#       - 'Secret Manager Secret Accessor'
#       - 'Project IAM Admin' (to manage permissions for sub-resources)
#       - 'Cloud Run Admin' (to manage public access)
#
# B. BUCKET PERMISSIONS
#    1. Go to the Admin Project -> State Bucket -> Permissions.
#    2. Grant BOTH SAs the role 'Storage Object Admin'.
#
# C. IMPERSONATION RIGHTS
#    1. Go to IAM -> Service Accounts -> Select the SA.
#    2. Grant your personal account the role 'Service Account Token Creator'.
#
# D. CODE CONFIGURATION
#    1. Update `terraform_sa_email` in envs/stage.tfvars and envs/prod.tfvars.
#
# ==============================================================================
# PART 2: DEPLOYMENT (Daily Workflow)
# ==============================================================================
#
# 1. Login to Google (Once per session)
#    gcloud auth application-default login
#
# 2. Fix Credentials Path (Windows Specific Fix)
#    # Terraform sometimes fails to locate the creds on Windows automatically.
#    # Copy the path outputted by the previous login command.
#    set GOOGLE_APPLICATION_CREDENTIALS=C:\Users\YOUR_USER\...\application_default_credentials.json
#
# 3. Select Identity (Choose Environment)
#    set GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=terraform-stage-sa@hiking-trips-stage.iam.gserviceaccount.com
#
# 4. Terraform Execution
#    terraform init                    # Only needed first time or if backend changes
#    terraform workspace new stage     # Only first time
#    terraform workspace select stage
#    terraform workspace show          # Verification
#
#    terraform plan -var-file="envs/stage.tfvars"
#    terraform apply -var-file="envs/stage.tfvars"
#
# CRITICAL SAFETY RULE: TRIPLE ALIGNMENT
# ------------------------------------------------------------------------------
# ALWAYS ensure the following three elements match the target environment:
# 1. Identity:  The exported Service Account (via Env Var)
# 2. Workspace: The Terraform Workspace (via `terraform workspace select`)
# 3. Variables: The variables file (via `-var-file`)
#
# IF MISMATCHED:
# - Wrong SA + Wrong Project = 403 Forbidden (Good, fast fail)
# - Wrong Workspace + Right Project = You corrupt the state file with wrong resources.
#
# PRO TIP: Check `terraform workspace show` before every plan/apply.
#
# ==============================================================================
# PART 3: TROUBLESHOOTING & NOTES
# ==============================================================================
#
# - APIs: Terraform may complain about disabled APIs (e.g., Cloud Run, SQL).
#   Enable them in the Google Cloud Console or allow Terraform to try enabling them.
#
# - DEBUGGING: If stuck, set logging to see detailed errors:
#   set TF_LOG=DEBUG
#
# - PASSWORDS (IMPORTANT):
#   On the first run, secrets (Admin/Reader passwords) are set to "CHANGE_ME".
#   You MUST manually:
#   1. Go to Secret Manager Console -> Add New Version -> Enter real password.
#   2. Go to SQL Console -> Users -> Update the db user password.
#   3. Redeploy Cloud Run (or run terraform apply again) to pick up the changes.
#
# - CLEANUP:
#   gcloud auth application-default revoke
#   set GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=
#   set GOOGLE_APPLICATION_CREDENTIALS=


provider "google" {
  project = var.project_id
  region  = var.region
  # Terraform will use your local creds ONLY to fetch this token.
  # All actual resource creation happens as this SA.
  impersonate_service_account = var.terraform_sa_email
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  impersonate_service_account = var.terraform_sa_email
}


# ==============================================================================
# 0. API ENABLEMENT (applied on provider project)
# ==============================================================================
locals {
  services = toset([
    "run.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "compute.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudbuild.googleapis.com",
    "serviceusage.googleapis.com",     # Required for Terraform to check APIs
  ])
}

resource "google_project_service" "enabled_services" {
  for_each = local.services
  
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}



# ==============================================================================
# 1. ARTIFACT REGISTRY (Where Docker images live)
# ==============================================================================
resource "google_artifact_registry_repository" "backend_repo" {
  location      = var.region
  repository_id = "backend-repo"
  description   = "Docker repository for Backend (${var.environment})"
  format        = "DOCKER"
  
  # Clean up old images to save money (keep last 5 versions)
  cleanup_policies {
    id     = "keep-last-5"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }
}

# ==============================================================================
# 2. SECRETS & PASSWORDS
# ==============================================================================

# --- A. Database Password (Generated by Terraform) ---
resource "random_password" "db_password" {
  length  = 16
  special = false # Avoid special chars that might break connection strings
}

# Create the Secret "Box" in Google Secret Manager
resource "google_secret_manager_secret" "db_pass_secret" {
  secret_id = "db-password"
  replication {
    auto {}
  }
}

# Put the generated password into the box
resource "google_secret_manager_secret_version" "db_pass_val" {
  secret      = google_secret_manager_secret.db_pass_secret.id
  secret_data = random_password.db_password.result
}

# --- B. JWT Secret (Generated by Terraform) ---
resource "random_password" "jwt_secret" {
  length  = 32
  special = true
}

resource "google_secret_manager_secret" "jwt_secret_box" {
  secret_id = "jwt-secret"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "jwt_secret_val" {
  secret      = google_secret_manager_secret.jwt_secret_box.id
  secret_data = random_password.jwt_secret.result
}

# --- C. Application Passwords (Provided by You via TF_VAR_) ---
resource "google_secret_manager_secret" "admin_pass_box" {
  secret_id = "admin-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "admin_pass_val" {
  secret      = google_secret_manager_secret.admin_pass_box.id
  secret_data = "DEFAULT_ADMIN_PASSWORD_CHANGE_IN_CONSOLE"
  lifecycle {
    # Ensure that terraform does not reset to the default.
     ignore_changes = [ secret_data ]
  }
}

resource "google_secret_manager_secret" "reader_pass_box" {
  secret_id = "reader-password"
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "reader_pass_val" {
  secret      = google_secret_manager_secret.reader_pass_box.id
  secret_data = "DEFAULT_READER_PASSWORD_CHANGE_IN_CONSOLE"
  lifecycle {
     ignore_changes = [ secret_data ]
  }
}

# ==============================================================================
# 3. DATABASE (Cloud SQL)
# ==============================================================================
resource "google_sql_database_instance" "main" {
  name             = "trips-db"
  database_version = "POSTGRES_15"
  region           = var.region

  # Prevent accidental deletion in Prod!
  deletion_protection = var.environment == "prod" ? true : false

  depends_on = [
    google_project_service.enabled_services
  ]

  settings {
    # "db-f1-micro" is cheapest.
    tier = var.environment == "prod" ? "db-f1-micro" : "db-f1-micro"

    # Enable Public IP (easiest for Cloud Run setup without VPC connectors)
    # Security is handled by the Cloud SQL Auth Proxy (built into Cloud Run)
    ip_configuration {
      ipv4_enabled = true 
    }
  }
}

resource "google_sql_database" "app_db" {
  name     = "trips_db"
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app_user" {
  name     = "app_user"
  instance = google_sql_database_instance.main.name
  password = random_password.db_password.result # Use the generated password

  lifecycle {
    ignore_changes = [password]
  }
}

# ==============================================================================
# 4. CLOUD RUN (Backend)
# ==============================================================================

# A dedicated Service Account for the backend identity
resource "google_service_account" "backend_sa" {
  account_id   = "backend-sa"
  display_name = "Cloud Run Backend Identity (${var.environment})"
  depends_on = [ google_project_service.enabled_services ]
}

# Grant SA permission to read Secrets
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
  depends_on = [ google_project_service.enabled_services ]
}

# Grant SA permission to connect to Cloud SQL
resource "google_project_iam_member" "sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
  depends_on = [ google_project_service.enabled_services ]
}

# Grant SA permission to sign URLs for Cloud Storage (if you use signed URLs)
resource "google_project_iam_member" "storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.backend_sa.email}"
  depends_on = [ google_project_service.enabled_services ]
}

resource "google_cloud_run_v2_service" "backend" {
  name     = "trips-backend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL" # Allow public internet access
  depends_on = [
    google_project_service.enabled_services,
    google_project_iam_member.secret_accessor,
    google_project_iam_member.sql_client
  ]

  template {
    service_account = google_service_account.backend_sa.email

    scaling {
      min_instance_count = var.environment == "prod" ? 0 : 0
      max_instance_count = 1
    }

    containers {
      # Initially, use a dummy placeholder image so TF can create the service.
      # Your CI/CD will overwrite this with the real image later.
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      
      # Define Environment Variables
      env {
        name  = "POSTGRES_DB"
        value = google_sql_database.app_db.name
      }
      env {
        name  = "POSTGRES_USER"
        value = google_sql_user.app_user.name
      }
      # The DB Host for Cloud Run is a Unix Socket provided by the proxy
      env {
        name  = "POSTGRES_HOST"
        value = "/cloudsql/${google_sql_database_instance.main.connection_name}"
      }
      env {
        name  = "GCP_STORAGE_BUCKET_NAME"
        value = google_storage_bucket.media.name
      }

      # --- INJECT SECRETS ---
      env {
        name = "POSTGRES_PASSWORD"
        value_source {
          secret_key_ref {
            secret = google_secret_manager_secret.db_pass_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "AUTH_SECRET_KEY"
        value_source {
          secret_key_ref {
            secret = google_secret_manager_secret.jwt_secret_box.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "AUTH_PASSWORD_ADMIN"
        value_source {
          secret_key_ref {
            secret = google_secret_manager_secret.admin_pass_box.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "AUTH_PASSWORD_READER"
        value_source {
          secret_key_ref {
            secret = google_secret_manager_secret.reader_pass_box.secret_id
            version = "latest"
          }
        }
      }

      # Connect to Cloud SQL via the Auth Proxy
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [google_sql_database_instance.main.connection_name]
      }
    }
  }
  lifecycle {
    ignore_changes = [
      # 1. Ignore the image (handled by gcloud/CI)
      template[0].containers[0].image,
      
      # 2. Ignore these labels (gcloud adds them automatically on deploy)
      client,
      client_version,
      
      # 3. (Optional) If you notice Terraform fighting over annotations
      # template[0].annotations["run.googleapis.com/client-name"],
      # template[0].annotations["run.googleapis.com/client-version"]
    ]
  }
}

# Allow unauthenticated users to hit the API (The app handles Auth itself)
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_v2_service.backend.name
  location = google_cloud_run_v2_service.backend.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ==============================================================================
# 5. CLOUD STORAGE (For your images)
# ==============================================================================
resource "google_storage_bucket" "media" {
  name          = "trips-app-media-${var.project_id}"
  location      = var.region
  force_destroy = false # Prevent deleting non-empty bucket
  
  uniform_bucket_level_access = true

  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    response_header = ["*"]
    max_age_seconds = 3600
  }
}

# ==============================================================================
# 6. FIREBASE (Frontend)
# ==============================================================================

# Enable Firebase services on the project
resource "google_project_service" "firebase" {
  provider           = google-beta
  project            = var.project_id
  service            = "firebase.googleapis.com"
  disable_on_destroy = false
}

resource "google_firebase_project" "default" {
  provider = google-beta
  project  = var.project_id
  
  depends_on = [google_project_service.firebase]
}

resource "google_firebase_web_app" "frontend" {
  provider     = google-beta
  project      = var.project_id
  display_name = "Frontend (${var.environment})"

  depends_on = [google_firebase_project.default]
}
