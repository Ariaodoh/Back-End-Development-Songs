# Use a small base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy your Flask app and other files
COPY . .

# Expose port for Flask app
EXPOSE 5000

# Set the main container command
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
