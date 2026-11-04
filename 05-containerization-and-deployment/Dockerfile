# Start from an image that already contains Python 3.12 (minimal Linux)
FROM python:3.12-slim

# Working folder inside the image
WORKDIR /app

# Copy the library list first, then install the libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your code (app.py) into the image
COPY . .

# Command run when the container starts: launch uvicorn on port 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]