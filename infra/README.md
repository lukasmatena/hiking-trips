# INFRASTRUCTURE SETUP & DEPLOYMENT GUIDE

## PREREQUISITES

- Google Cloud Account
- Installed: GCloud CLI, Terraform

- PROD Project:  Empty project [Firebase enabled] (ID goes to envs/prod.tfvars)
- STAGE Project: Empty project [Firebase enabled] (ID goes to envs/stage.tfvars)
- STATE Project: Separate 'admin' project containing the State Bucket (Bucket ID goes into backend.tf)

- Separation relies on Terraform Workspaces (logical isolation).
- Both Stage and Prod share one state bucket (physical sharing).

## PART 1: INITIAL SETUP (One-Time)

### A. SERVICE ACCOUNTS

1. Create a Service Account (SA) in BOTH Stage and Prod projects.
2. Assign the following roles to each SA in their respective project:
- 'Editor'
- 'Secret Manager Secret Accessor'
- 'Project IAM Admin' (to manage permissions for sub-resources)
- 'Cloud Run Admin' (to manage public access)
- 'Service Account Admin'
- 'Workload Identity Pool Admin'

### B. BUCKET PERMISSIONS

1. Go to the Admin Project -> State Bucket -> Permissions.
2. Grant BOTH SAs the role 'Storage Object Admin'.

### C. IMPERSONATION RIGHTS

1. Go to IAM -> Service Accounts -> Select the SA.
2. Grant your personal account the role 'Service Account Token Creator'.

### D. CODE CONFIGURATION
1. Update `terraform_sa_email` in envs/stage.tfvars and envs/prod.tfvars.

## PART 2: DEPLOYMENT (Daily Workflow)

```
gcloud auth application-default login
export GOOGLE_APPLICATION_CREDENTIALS=path/application_default_credentials.json  # Path reported by previous cmd.
terraform init
terraform workspace new stage
terraform workspace select stage
terraform plan -var-file="envs/stage.tfvars"
terraform apply -var-file="envs/stage.tfvars"
```

## PART 3: TROUBLESHOOTING & NOTES

#### DEBUGGING

If stuck, set logging to see detailed errors: `export TF_LOG=DEBUG`

#### PASSWORDS (IMPORTANT)

On the first run, secrets (Admin/Reader passwords) are set to a variation of "CHANGE_ME". You MUST manually:

1. Go to Secret Manager Console -> Add New Version -> Enter real password.
2. Redeploy Cloud Run to pick up the changes.

#### CLEANUP

```
gcloud auth application-default revoke
set GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=
set GOOGLE_APPLICATION_CREDENTIALS=
```
