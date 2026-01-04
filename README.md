# TL;DR

**A simple website to store reports and photos from hiking trips. This is a personal learning project.**



## Overview of the stack and used technologies

Despite the simplicity of the app, the stack is meant to be robust and well made. None of this is vibe-coded in order to actually practice modern web development principles and technologies, though I admit that AI has helped create initial scaffolding for Github Actions workflow and Terraform.


#### Backend
- Python (FastAPI)
- JWT-based auth (two fixed roles with two fixed passwords, bcrypt hashes in env vars)

#### Data
- PostgreSQL (asyncpg)
- raw SQL queries (no ORM)
- migrations handled by alembic
- GCP Storage bucket for photos (private, backend requests presigned URLs)

#### Frontend
- very basic vanilla TypeScript for now
- bunded by Vite

#### Infrastructure
- defined in Terraform for GCP
- hosting uses Firebase
- completely separate stage and prod envs
- docker-compose for local development, including faked GCP bucket

#### CI/CD
- Github Actions workflow deploys on pushes to `stage` and `prod` branches
- Github -> GCP auth relies on WIF (Workload Identity Federation)

More detailed documentation can be found in the respective folders (and of course in the code itself).

## Local testing

1. `cp .env.example .env`
2. Edit `.env` and fill in your values
3. `docker compose up -d`
4. `cd frontend && npm run dev`
5. The website is now available at `localhost:5173` (or another port that Vite chooses)

## Deployment

See `infra/README.md` for instructions on how to setup GCP projects.

For manual deployment, read comments in `backend/deploy.sh` (backend) and `frontend/README.md` (frontend).

Github Actions workflow in `.github/workflows/deploy.yml` documents the same process (except manual auth).
