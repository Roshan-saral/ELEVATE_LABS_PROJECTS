# Start with a clean, slim Python image
FROM python:3.12-slim

# Set the working directory for the app
WORKDIR /app

# Copy and install dependencies first (for faster rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application files
COPY . .

# Cloud Run requires the container to listen on the PORT environment variable, which defaults to 8080.
# Streamlit needs to be explicitly told to listen on 0.0.0.0 and port 8080 (or whatever Cloud Run assigns).
EXPOSE 8080

# This is the command to run your Streamlit app
# IMPORTANT: This must match your main Streamlit file (e.g., app.py)
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]