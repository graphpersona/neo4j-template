import os
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()
SSH_PRIVATE_KEY_PATH = os.getenv("SSH_PRIVATE_KEY_PATH") 
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
SSL_EMAIL = os.getenv("SSL_EMAIL")

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
    
def dns_cloudflare_api(ip):
    try:
        print("\n Run dns_cloudflare_api...")
        dns_cloudflare_command = f"echo 'dns_cloudflare_api_token = {CLOUDFLARE_API_TOKEN}' | sudo tee /root/cf.ini >/dev/null && sudo chmod 600 /root/cf.ini"
        create_user_run_command = ["ssh", "-i", SSH_PRIVATE_KEY_PATH, f"root@{ip}", "bash", "-s"]
        subprocess.run(create_user_run_command, input=dns_cloudflare_command, text=True, check=True)
        print(">>> dns_cloudflare_api completed.")
        return True
    except Exception as e:
        print(f"Error running bootstrap script: {e}")
        return False
    
def get_ssl_certificate(fqdn, ip):
    try:
        print("\n Get SSL certificate...")
        create_user_run_command = ["ssh", "-i", SSH_PRIVATE_KEY_PATH, f"root@{ip}", "bash", "-s"]
        ssh_command = f"""export SUBDOMAIN="{fqdn}" && export EMAIL="{SSL_EMAIL}" """
        subprocess.run(create_user_run_command, input=ssh_command, text=True, check=True)
        ssh_command = """certbot certonly --non-interactive \
            --dns-cloudflare --dns-cloudflare-credentials /root/cf.ini \
                --dns-cloudflare-propagation-seconds 30 \
            --agree-tos -m "$EMAIL" \
            --key-type ecdsa \
            --cert-name neo4j \
            -d "$SUBDOMAIN" """
        subprocess.run(create_user_run_command, input=ssh_command, text=True, check=True)
        ssh_command = """cp -f /etc/letsencrypt/live/neo4j/fullchain.pem \
                /home/neo4j_admin/neo4j_instance/ssl_certs/cert.pem
            cp -f /etc/letsencrypt/live/neo4j/privkey.pem \
                /home/neo4j_admin/neo4j_instance/ssl_certs/key.pem
            chmod 600 /home/neo4j_admin/neo4j_instance/ssl_certs/key.pem """
        subprocess.run(create_user_run_command, input=ssh_command, text=True, check=True)
        print(">>> SSL certificate completed.")
        return True
    except Exception as e:
        print(f"Error running bootstrap script: {e}")