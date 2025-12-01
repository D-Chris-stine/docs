#!/usr/bin/env bash

## Instructions  ##
#    Ensure Docker Desktop is open and you are signed in.
#    Make sure you run the build.sh file first.
# 1. Update the IMAGE_NAME variable to reflect the LAMBDA function you are working on
# 2. Ensure this file is saved in the base directory for the function. Usually the function name.
#    Ensure your working directory is also tthe base directory.
# 3. Make the file executable <chmod +x push.sh> (Hint: Nothing prints if this works)
# 2. Run <./push.sh> in CLI terminal

set -euo pipefail

IMAGE_NAME="tableau-export"
AWS_REGION="${AWS_REGION:-us-east-2}"
TAG="${TAG:-latest}"

ACCOUNT_ID="${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
REPO_URI="${ECR_URI}/${IMAGE_NAME}"

aws ecr describe-repositories --repository-names "${IMAGE_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1 || \
  aws ecr create-repository --repository-name "${IMAGE_NAME}" --region "${AWS_REGION}" >/dev/null

aws ecr get-login-password --region "${AWS_REGION}" \
| docker login --username AWS --password-stdin "${ECR_URI}"

docker push "${REPO_URI}:${TAG}"
echo "Pushed ${REPO_URI}:${TAG}"
