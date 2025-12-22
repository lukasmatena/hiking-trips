# envs/prod.tfvars

project_id  = "hiking-trips-prod"
region      = "europe-west1"
environment = "prod"
terraform_sa_email = "terraform-prod-sa@hiking-trips-prod.iam.gserviceaccount.com"

# Production might use a different region or project if you wanted strict isolation,
# but for now, we keep it simple in the same project.