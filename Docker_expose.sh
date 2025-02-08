#!/bin/bash


# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root"
  exit 1
fi

# Get the IP address of the tailscale0 interface
TAILSCALE_IP=$(ip -4 addr show tailscale0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
if [ -z "$TAILSCALE_IP" ]; then
  echo "Error: Could not find the IP address of the tailscale0 interface."
  exit 1
fi

# Warn about overwriting existing configurations
echo "Warning: This script will overwrite the following files if they exist:"
echo "- /etc/docker/daemon.json"
echo "- /etc/systemd/system/docker.service.d/override.conf"
echo "Proceeding in 5 seconds... (Press Ctrl+C to cancel)"
sleep 5

# Create the /etc/docker directory if it doesn't exist
mkdir -p /etc/docker

# Create or overwrite the daemon.json file
cat <<EOF > /etc/docker/daemon.json
{
  "hosts": ["tcp://$TAILSCALE_IP:2375", "unix:///var/run/docker.sock"]
}
EOF
echo "Created/overwritten /etc/docker/daemon.json"

# Create the systemd override directory if it doesn't exist
mkdir -p /etc/systemd/system/docker.service.d

# Create or overwrite the override.conf file
cat <<EOF > /etc/systemd/system/docker.service.d/override.conf
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd
EOF
echo "Created/overwritten /etc/systemd/system/docker.service.d/override.conf"

# Reload the systemd daemon
systemctl daemon-reload
echo "Reloaded systemd daemon"

# Restart the Docker service
systemctl restart docker.service
echo "Restarted Docker service"

# Check the status of the Docker service
echo "Checking Docker service status..."
systemctl status docker.service --no-pager

echo "Docker has been configured successfully."
echo "Docker is now listening on:"
echo "- TCP: $TAILSCALE_IP:2375"
echo "- Unix socket: /var/run/docker.sock"
