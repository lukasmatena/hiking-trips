# envs/stage.tfvars

project_id  = "hiking-trips-stage"
region      = "europe-west1"
environment = "stage"
terraform_sa_email = "terraform-stage-sa@hiking-trips-stage.iam.gserviceaccount.com"

# Note: We do NOT put passwords here. 
# Passwords come from env vars (TF_VAR_...) or your terminal.