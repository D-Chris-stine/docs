Lambda Function Repository
Deploy Instructions
Build using Docker
Run the build.sh file to build the Docker container image on the local machine
Run the push.sh file to
Run the
FILE STRUCTURE
functions/<function_name>/ ├── Dockerfile ├── requirements.txt ├── .dockerignore ├── src/ │ ├── lambda_function.py │ └── app/ └── (tests/ | event_samples/ | ops/)
