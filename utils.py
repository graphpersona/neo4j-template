import os
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()
SSH_PRIVATE_KEY_PATH = os.getenv("SSH_PRIVATE_KEY_PATH") 

def get_location(zone=None, location=None):
    default_location = "fsn1"
    default_zone = "europe"
    locations = {
        "europe": ["fsn1", "nbg1","hel1"],
        "asia": ["sin1"],
        "us": ["ash", "hil"],
    }
    if location is None:
        if zone is None or zone not in locations:
            zone = default_zone
            location = default_location
        else:
            location = locations[zone][0]
    list_locations = [location] + [loc for loc in locations[zone] if loc != location]
    return zone, list_locations

def wait_ssh(ip):
    print("\nWait SSH on server...")
    # Collect SSH command with explicit key and disable password authentication
    ssh_check_command = [
        "ssh",
        "-i", SSH_PRIVATE_KEY_PATH, # <-- Our key
        "-o", "StrictHostKeyChecking=no",
        "-o", "PasswordAuthentication=no", # <-- Disable password authentication
        "-o", "ConnectTimeout=10",
        f"root@{ip}",
        "echo 'SSH is up'"
    ]
    for _ in range(30): # Wait max 5 minutes
        try:
            subprocess.run(ssh_check_command, check=True, capture_output=True, text=True, timeout=15)
            print(">>> SSH is up.")
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("...server is not ready, wait 10 seconds...")
            time.sleep(10)
    else:
        print("Failed to connect to server by SSH in 5 minutes.")
        return False