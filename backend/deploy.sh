# Running migrations
#
# Migrations are run from local environment using SQL proxying. In one terminal, run
#
# $ cloud-sql-proxy.exe --port 5433 --quota-project hiking-trips-stage hiking-trips-stage:europe-west1:trips-db
#
# In a different terminal, cd to backend folder, set up Python venv, install alembic and then
#
# $ export POSTGRES_DB=trips_db
# $ export POSTGRES_HOST=127.0.0.1
# $ export POSTGRES_PORT=5433
# $ export POSTGRES_USER=(see console)
# $ export POSTGRES_PASSWORD=(see secrets)
# $ venv/Scripts/alembic upgrade head


# The actual deploy script follows:


if [ "$1" != "stage" ] && [ "$1" != "prod" ]; then
  echo "Usage: ./deploy.sh [stage|prod]"
  exit 1
fi

# These must match Terraform config:
REGION="europe-west1"
PROJECT_ID="hiking-trips-$1"
REPO="backend-repo"

# Other vars
IMAGE="trips-backend"
TAG=$(git rev-parse --short HEAD)

IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$IMAGE:$TAG"

echo "Deploying $TAG to $1..."

set -e # so the script stops if the build fails

# Sends code to Google so it can build the image and save it.
gcloud builds submit . --project "$PROJECT_ID" --tag "$IMAGE_URL" --gcs-log-dir="gs://${PROJECT_ID}_cloudbuild/logs"

gcloud run deploy trips-backend \
  --image="$IMAGE_URL" \
  --region=$REGION \
  --project=$PROJECT_ID
