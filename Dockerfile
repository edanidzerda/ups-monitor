FROM python:3.7-slim-buster


# Set the working directory in the container
WORKDIR /app
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-setuptools \
    python3-venv \
    nut-client \
    && apt-get clean

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the content of the local src directory to the working directory 
COPY . .

# Run ups-monitor2.py when the container launches
CMD ["python", "ups-monitor2.py"]