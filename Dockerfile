# Use an official Python runtime as a parent image
FROM python:3.12.0-slim-bullseye

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the Python script into the container
COPY LAST.py .

# Install any needed packages specified in requirements.txt
RUN pip install requirements.txt

# Define environment variable
ENV OPENAI_API_KEY=YOUR_OPENAI_API_KEY
ENV GITHUB_TOKEN=GITHUB_TOKEN

# Run security_scanner.py when the container launches
CMD ["python", "./LAST.py"]
