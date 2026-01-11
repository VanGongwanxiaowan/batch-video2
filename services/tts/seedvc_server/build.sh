#!/bin/bash

# Define the image name and tag
IMAGE_NAME="registry.cn-hangzhou.aliyuncs.com/gjxserver/ubuntubase"
IMAGE_TAG="tts_seed_vc0.2"
FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

echo "Building Docker image: ${FULL_IMAGE_NAME}"

# Build the Docker image
docker build -t "${FULL_IMAGE_NAME}" .

# Check if the build was successful
if [ $? -eq 0 ]; then
    echo "Docker image built successfully."
    echo "Pushing Docker image: ${FULL_IMAGE_NAME}"
    # Push the Docker image to the registry
    docker push "${FULL_IMAGE_NAME}"
    if [ $? -eq 0 ]; then
        echo "Docker image pushed successfully."
    else
        echo "Error: Docker image push failed."
        exit 1
    fi
else
    echo "Error: Docker image build failed."
    exit 1
fi