#!/usr/bin/env bash
## Instructions  ##
#    Ensure Docker Desktop is open and you are signed in.
#    Make sure you run the build.sh & push.sh files first.
# 1. Update the FUNCTION_NAME variable to reflect the LAMBDA function you are working on
#    Update the tag after - if needed to clarify changes
#    Add or remove AWS Secrets Manager Secret Names to be set to Lambda environment variables
# 2. Ensure this file is saved in the base directory for the function. Usually the function name.
#    Ensure your working directory is also tthe base directory.
# 3. Make the file executable <chmod +x deploy.sh> (Hint: Nothing prints if this works)
# 2. Run <./deploy.sh> in CLI terminal

set -euo pipefail

FUNCTION_NAME="${FUNCTION_NAME:-tableau_export}"
ROLE_ARN="${ROLE_ARN:-arn:aws:iam::478121477551:role/LambdaFullAccess}"
AWS_REGION="${AWS_REGION:-us-east-2}"
TAG="${TAG:-latest}"

ACCOUNT_ID="${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_NAME="${IMAGE_NAME:-tableau-export}"
IMAGE_URI="${ECR_URI}/${IMAGE_NAME}:${TAG}"

# ✅ Only these env vars are set on the Lambda:
TABLEAU_SECRET_NAME="${TABLEAU_SECRET_NAME:-api/Tableau/prod}"
S3_SECRET_NAME="${S3_SECRET_NAME:-s3/config/default}"

set +e
aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1
FOUND=$?
set -e

if [ $FOUND -ne 0 ]; then
  aws lambda create-function \
    --function-name "${FUNCTION_NAME}" \
    --package-type Image \
    --code ImageUri="${IMAGE_URI}" \
    --role "${ROLE_ARN}" \
    --region "${AWS_REGION}" \
    --timeout 60 --memory-size 512 \
    --environment "Variables={TABLEAU_SECRET_NAME=${TABLEAU_SECRET_NAME},S3_SECRET_NAME=${S3_SECRET_NAME}}"
else
  aws lambda update-function-code \
    --function-name "${FUNCTION_NAME}" \
    --image-uri "${IMAGE_URI}" \
    --region "${AWS_REGION}" >/dev/null

  aws lambda update-function-configuration \
    --function-name "${FUNCTION_NAME}" \
    --timeout 60 --memory-size 512 \
    --environment "Variables={TABLEAU_SECRET_NAME=${TABLEAU_SECRET_NAME},S3_SECRET_NAME=${S3_SECRET_NAME}}" \
    --region "${AWS_REGION}" >/dev/null
fi

aws lambda publish-version --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}" >/dev/null
echo "Deployed ${FUNCTION_NAME} -> ${IMAGE_URI}"
