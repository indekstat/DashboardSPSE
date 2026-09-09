FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port 8503 for Streamlit
EXPOSE 8503

# Command to run the application
CMD ["streamlit", "run", "dashboard.py", "--server.port", "8503", "--server.address", "0.0.0.0"]
