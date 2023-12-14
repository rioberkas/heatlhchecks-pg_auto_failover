#!/bin/bash

# Define variables
INSTALL_DIR="/etc/hc-pg_auto_failover"
SERVICE_NAME="cek-hc"

# Function to install Python dependencies
install_dependencies() {
    pip install Flask Flask-SSLify psycopg2-binary python-dotenv pyinstaller
}

# Function to create directory and copy files
setup_application() {
    sudo mkdir -p $INSTALL_DIR
    sudo cp -r cek-hc.py env templates $INSTALL_DIR
}

# Function to create systemd service file
create_systemd_service() {
    cat <<EOL | sudo tee /usr/lib/systemd/system/$SERVICE_NAME.service
[Unit]
Description=Flask Application for Health Check
After=network.target

[Service]
ExecStart=/usr/bin/python3 $INSTALL_DIR/cek-hc.py
User=${USER}
Group=${USER}
WorkingDirectory=$INSTALL_DIR
Restart=always

[Install]
WantedBy=multi-user.target
EOL
}

# Function to start and enable the systemd service
start_systemd_service() {
    sudo systemctl daemon-reload
    sudo systemctl start $SERVICE_NAME
    sudo systemctl enable $SERVICE_NAME
    sudo systemctl status $SERVICE_NAME
}

# Main installation process
echo "Installing dependencies..."
install_dependencies

echo "Setting up application..."
setup_application

echo "Creating systemd service..."
create_systemd_service

echo "Starting and enabling the service..."
start_systemd_service

echo "Installation complete."
