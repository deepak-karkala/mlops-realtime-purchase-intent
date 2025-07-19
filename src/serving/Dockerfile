# Use an official lightweight Python image.
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables for SageMaker
ENV SAGEMAKER_PROGRAM app.py

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the feature repository and the application code
COPY ./feature_repo ./feature_repo
COPY . .

# SageMaker will mount the model artifacts to /opt/ml/model
# The CMD is not needed, as SageMaker's entrypoint will run the app

# If running locally (not on SageMaker):
# CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080", "app:app"]