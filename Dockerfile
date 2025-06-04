# 1. Base image with Python 3.11 (or 3.10/3.9, as you prefer)
FROM python:3.11-slim

# 2. Set working directory
WORKDIR /app

# 3. Copy requirements, install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the entire project into the container
COPY . .

# 5. Expose port 5000
EXPOSE 5000

# 6. Default command to run the Flask app
CMD ["python", "app.py"]