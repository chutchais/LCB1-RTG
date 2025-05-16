# Use the official Mosquitto base image
FROM eclipse-mosquitto:latest

# Copy your custom config into the correct directory
COPY mosquitto.conf /mosquitto/config/mosquitto.conf

# (Optional) Copy password or other config files
COPY passwd /mosquitto/config/passwd

# Expose ports (optional but informative)
EXPOSE 1883
EXPOSE 9001
