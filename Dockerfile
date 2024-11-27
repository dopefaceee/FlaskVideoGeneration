# Use the official Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy the application and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Set the command to run the application
CMD ["python", "app.py"]

# Expose the port Flask runs on
EXPOSE 8080
