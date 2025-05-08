FROM python:3.10.0

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /downloader
COPY . /app


# Install dependencies
RUN pip install --upgrade pip
RUN pip install .
