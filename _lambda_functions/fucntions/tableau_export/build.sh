#!/usr/bin/env bash
## Instructions  ##
#    Ensure Docker Desktop is open and you are signed in.
# 1. Update the IMAGE_NAME variable to reflect the LAMBDA function you are working on
#    Update the Tag Name if needed to clarify changes made.
# 2. Ensure this file is saved in the base directory for the function. Usually the function name.
#    Ensure your working directory is also the base directory.
# 3. Make the file executable by running <chmod +x build.sh> in the terminal (Hint: Nothing prints if this works)
# 2. Run <./build.sh> in CLI terminal

#!/usr/bin/env bash
set -euo pipefail

# ========= CONFIGURE ME (edit as needed) =========
IMAGE_NAME="${IMAGE_NAME:-tableau-export}"      # ECR repo & local image name
AWS_REGION="${AWS_REGION:-us-east-2}"
TAG="${TAG:-latest}"                            # or set TAG externally
PLATFORM="${PLATFORM:-linux/amd64}"             # Lambda x86_64. Use linux/arm64 if your fn is arm.
NO_CACHE="${NO_CACHE:-true}"                    # set to "false" to allow cache
# ================================================

ACCOUNT_ID="${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
REPO_URI="${ECR_URI}/${IMAGE_NAME}"

# Require Dockerfile in the current folder (lambda_repo/functions/<fn>/files)
[[ -f Dockerfile ]] || { echo "Dockerfile not found in $(pwd)"; exit 1; }

# Ensure buildx is ready
docker buildx version >/dev/null 2>&1 || { echo "docker buildx not available"; exit 1; }
docker buildx inspect >/dev/null 2>&1 || docker buildx create --use --name lambda-builder

echo "Building ${IMAGE_NAME}:${TAG} for ${PLATFORM}"
docker buildx build \
  --platform "${PLATFORM}" \
  $([ "${NO_CACHE}" = "true" ] && echo "--no-cache") \
  -t "${IMAGE_NAME}:${TAG}" \
  --output=type=docker \
  .

# Tag for ECR
docker tag "${IMAGE_NAME}:${TAG}" "${REPO_URI}:${TAG}"

# Persist tag for push/deploy convenience
echo "${TAG}" > .last_tag

echo "Built ${REPO_URI}:${TAG}"
echo "export TAG=${TAG}"
