# Build from the shared base image (adjust path in CI build)
FROM public.ecr.aws/lambda/python:3.12

# Install function-specific deps
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY src/ ${LAMBDA_TASK_ROOT}/src/
# Lambda handler path: src/lambda_function.lambda_handler
CMD ["src/lambda_function.lambda_handler"]
