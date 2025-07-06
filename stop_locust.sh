#!/bin/bash

# Stop any existing Locust processes to free up ports
echo "Stopping any existing Locust processes..."
sudo pkill -f locust