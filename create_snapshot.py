import os
import time
import subprocess
from dotenv import load_dotenv
from hcloud import Client
from hcloud.images import Image
from hcloud.locations import Location
from hcloud.ssh_keys import SSHKey
from hcloud.server_types import ServerType

load_dotenv()
HETZNER_API_TOKEN = os.getenv("HETZNER_API_TOKEN")
SSH_KEY_NAME = os.getenv("SSH_KEY_NAME")
SNAPSHOT_NAME = os.getenv("SNAPSHOT_NAME")
GIT_REPO_URL = os.getenv("GIT_REPO_URL")
SSH_PRIVATE_KEY_PATH = os.getenv("SSH_PRIVATE_KEY_PATH") 
client = Client(token=HETZNER_API_TOKEN)

# --- SCRIPT THAT WILL BE EXECUTED ON TEMPORARY VM ---
def create_server(server_name, server_type, location, image, ssh_keys_name):
    print("\n[1/6] Creating a temporary server Hetzner...")
    try:
        response = client.servers.create(
                name=server_name,
                server_type=ServerType(name=server_type),
                location=Location(name=location),
                image=Image(name=image),
                ssh_keys=[client.ssh_keys.get_by_name(ssh_keys_name)],
                start_after_create=True,
            )
        server = response.server
        return server, True
    except Exception as e:
        print(f"Error creating server: {e}")
        return False, False

def wait_ssh(ip):
    print("\n[2/6] Wait SSH on server...")
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

def run_bootstrap_script(ip):
    try:
        print("\n[3/6] Create user neo4j_admin, install and run bootstrap script, copy ssl certs...")
        create_user_command = f"""sudo apt-get update && sudo apt-get install -y git && git clone {GIT_REPO_URL} ~/repo_temp && bash ~/repo_temp/templates/bootstrap-template.sh"""
        create_user_run_command = ["ssh", "-i", SSH_PRIVATE_KEY_PATH, f"root@{ip}", "bash", "-s"]
        subprocess.run(create_user_run_command, input=create_user_command, text=True, check=True)
        print(">>> Bootstrap script completed.")
        scp_command_base = f"scp -i {SSH_PRIVATE_KEY_PATH} -o StrictHostKeyChecking=no -o PasswordAuthentication=no"
        subprocess.run(f"{scp_command_base} certs/cert.pem neo4j_admin@{ip}:/home/neo4j_admin/neo4j_instance/ssl_certs/", shell=True, check=True)
        subprocess.run(f"{scp_command_base} certs/key.pem neo4j_admin@{ip}:/home/neo4j_admin/neo4j_instance/ssl_certs/", shell=True, check=True)
        print(">>> SSL certs copied.")
        return True
    except Exception as e:
        print(f"Error running bootstrap script: {e}")
        return False

def neo4jdocker(ip):
    try:
        create_user_run_command = ["ssh", "-i", SSH_PRIVATE_KEY_PATH, f"root@{ip}", "bash", "-s"]
        print("\n[4/6] Docker neo4j compose...")
        change_command = f"""sudo dos2unix /home/neo4j_admin/neo4j_instance/ssl_certs/key.pem && sudo dos2unix /home/neo4j_admin/neo4j_instance/ssl_certs/cert.pem && sudo chown -R 7474:7474 /home/neo4j_admin/neo4j_instance/ssl_certs/ && sudo chmod o+x /home/neo4j_admin && docker compose -f /home/neo4j_admin/neo4j_instance/docker-compose.yml up -d""" 
        subprocess.run(create_user_run_command, input=change_command, text=True, check=True)

        print("\nDocker neo4j wait 120s and stop...")
        time.sleep(120)
        stop_command = f"""docker stop neo4j_user""" 
        subprocess.run(create_user_run_command, input=stop_command, text=True, check=True)
        time.sleep(30)
        return True
    except Exception as e:
        print(f"Error running or stopping neo4j docker compose: {e}")
        return False

def create_snapshot(server):
    try:
        print("\n[5/6] Stop server and create snapshot...")
        action = server.power_off()
        action.wait_until_finished()
        image_action = server.create_image(description=SNAPSHOT_NAME, type="snapshot")
        image_action.wait_until_finished()
        image = client.images.get_by_id(image_action.image.id)
        time.sleep(120)
        print(f"Snapshot '{image.description}' (ID: {image.id}) created!")
        return True, image
    except Exception as e:
        print(f"Error creating snapshot: {e}")
        return False, None

def delete_server(server):
    try:
        print(f"\n[6/6] Removing a temporary server...")
        server.delete()
        print("Temporary server removed.")
        return True
    except Exception as e:
        print(f"Error deleting server: {e}")
        return False

def main(zone=None, location=None):
    print("--- CREATING A GOLDEN SNAPSHOT ---")
    server = None
    try:
        # 1. Create server
        default_location = "fsn1"
        default_zone = "europe"
        locations = {
            "europe": ["fsn1", "nbg1","hel1"],
            "asia": ["sin1"],
            "us": ["ash", "hil"],
        }
        server_name="snapshot-builder"
        image="ubuntu-24.04"
        ssh_keys_name=[SSH_KEY_NAME]
        if location is None:
            if zone is None or zone not in locations:
                zone = default_zone
                location = default_location
            else:
                location = locations[zone][0]
        list_locations = [location] + [loc for loc in locations[zone] if loc != location]
        server_type="cx22" if zone == "europe" else "cpx11"
        for location in list_locations:
            server, status = create_server(server_name, server_type, location, image, ssh_keys_name)
            if status == True:
                break

        if status == False:
            print("Failed to create server. Try again with another location.")
            return "NO_SERVER"

        print(f"Server '{server.name}' created. IP: {server.public_net.ipv4.ip}. Waiting for bootstrap script to complete...")
        ip = server.public_net.ipv4.ip
        print(f"Server '{server.name}' created. IP: {ip}.")

        # 2. Wait SSH
        status = wait_ssh(ip)
        if status == False:
            print("Failed to connect to server by SSH in 5 minutes.")
            return "NO_SERVER"
        print(">>> SSH is up.")

        
        # 3. Create user neo4j_admin, install and run bootstrap script - All bash operations
        status = run_bootstrap_script(ip)
        if status == False:
            print("Failed to run bootstrap script.")
            return "NO_SERVER"
        print(">>> Bootstrap script completed.")

        # 4. Docker neo4j compose and first start
        status = neo4jdocker(ip)
        if status == False:
            print("Failed to run or stop neo4j docker compose.")
            return "NO_SERVER"
        print(">>> Neo4j docker compose completed and stopped.")

        # 5. Stop server and create snapshot
        status, image = create_snapshot(server)
        if status == False:
            print("Failed to create snapshot.")
            return "NO_SERVER"
        print(f"Snapshot '{image.description}' (ID: {image.id}) created!")
        return image.id

    finally:
        if server and status == True:
            status = delete_server(server)
            if status == False:
                print("Failed to delete server.")
                return "NO_SERVER"
            print("Temporary server removed.")

if __name__ == "__main__":
    main()