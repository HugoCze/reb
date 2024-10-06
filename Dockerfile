# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV BOT_TOKEN=6366039222:AAEmToq1dtMWit8eYvyo2eC1YB_c9U9bFj8

# Run bot.py when the container launches
CMD ["python", "testGambieBot_2.py"]