FROM python:3.11-slim

WORKDIR /app

# Copy dependency list and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the honeypot code
COPY honeypot.py .

# Expose the default DICOM port
EXPOSE 11112

# Run the honeypot
CMD ["python", "-u", "honeypot.py"]