## Lambda Function Repository

### Deploy Instructions
1. Build using Docker
2. Run the build.sh file to build the Docker container image on the local machine
3. Run the push.sh file to 
4. Run the 

### FILE STRUCTURE
functions/<function_name>/
├── Dockerfile
├── requirements.txt
├── .dockerignore
├── src/
│   ├── lambda_function.py
│   └── app/
└── (tests/ | event_samples/ | ops/)
