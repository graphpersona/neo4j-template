import os
import time
import subprocess
import requests
from dotenv import load_dotenv
from hcloud import Client
from hcloud.images import Image
from hcloud.ssh_keys import SSHKey
from hcloud.server_types import ServerType
from hcloud.locations import Location
import secrets
import string
from utils import get_location, wait_ssh, get_ssl_certificate

load_dotenv()

# --- Константы из .env ---
HETZNER_API_TOKEN = os.getenv("HETZNER_API_TOKEN")
SSH_KEY_NAME = os.getenv("SSH_KEY_NAME")
YOUR_BASE_DOMAIN = os.getenv("YOUR_BASE_DOMAIN")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")
SSH_PRIVATE_KEY_PATH = os.getenv("SSH_PRIVATE_KEY_PATH")

client = Client(token=HETZNER_API_TOKEN)

def create_server(server_name, server_type, location, snapshot, ssh_keys_name):
    print(f"\n[1/5] Создание сервера '{server_name}' из снимка...")
    try:
        response = client.servers.create(
                name=server_name,
                server_type=ServerType(name=server_type),
                location=Location(name=location),
                image=snapshot,
                ssh_keys=[client.ssh_keys.get_by_name(ssh_keys_name)],
                start_after_create=True,
            )
        server = response.server
        return server, True
    except Exception as e:
        print(f"Error creating server: {e}")
        return False, False

def create_cloudflare_dns_record(fqdn, ip_address):
    print(f"\n[2/5] Создание DNS-записи...")
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}", "Content-Type": "application/json"}
    url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
    data = {"type": "A", "name": fqdn, "content": ip_address, "ttl": 1, "proxied": False}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"DNS A-запись для '{fqdn}' -> {ip_address} создана.")
        return True
    except Exception as e:
        print(f"Error creating DNS record: {e}")
        return False


    
def run_neo4jdocker(ip):
    print(f"\n[3/4] Запуск neo4j docker compose...")
    try:
        run_command = ["ssh", "-i", SSH_PRIVATE_KEY_PATH, f"neo4j_admin@{ip}", "bash", "-s"]
        start_command = f"""docker start neo4j_user""" 
        subprocess.run(run_command, input=start_command, text=True, check=True)
        return True
    except Exception as e:
        print(f"Error running or stopping neo4j docker compose: {e}")
        return False
    
def provision_neo4j_for_client(SNAPSHOT_ID=304291995, zone=None, location=None):
    # Ищем наш снимок по имени
    snapshot = client.images.get_by_id(SNAPSHOT_ID)
    if not snapshot:
        raise Exception(f"Снимок '{os.getenv('SNAPSHOT_NAME')}' не найден!")

    # 1. Создание VM из снимка
    zone, list_locations = get_location(zone, location)
    server_type="cx22" if zone == "europe" else "cpx11"
    subdomain = f"inst-{''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(12))}"
    server_name = f"{subdomain}.{YOUR_BASE_DOMAIN}"

    for location in list_locations:
        server, status = create_server(server_name, server_type, location, snapshot, SSH_KEY_NAME)
        if status == True:
            break

    if status == False:
        print("Failed to create server. Try again with another location.")
        return "NO_SERVER"

    print(f"Server '{server.name}' created. IP: {server.public_net.ipv4.ip}.")
    ip = server.public_net.ipv4.ip
    print(f"Server '{server.name}' created. IP: {ip}.")

    # 2. Создание A-записи в DNS
    status = create_cloudflare_dns_record(server_name, ip)
    if status == False:
        print("Failed to create DNS record.")
        return "NO_SERVER"
    print(">>> DNS record created.")

    # 3. Wait SSH
    status = wait_ssh(ip)
    if status == False:
        print("Failed to connect to server by SSH in 5 minutes.")
        return "NO_SERVER"
    print(">>> SSH is up.")

    # 4. Get SSL certificate
    status = get_ssl_certificate(server_name, ip)
    if status == False:
        print("Failed to get SSL certificate.")
        return "NO_SERVER"
    print(">>> SSL certificate created.")

    # 5. Запуск neo4j docker compose
    run_neo4jdocker(ip)

    # 6. Возвращаем результат немедленно. Проверку готовности можно сделать отдельным API-вызовом.
    print(f"\n[4/4] Развертывание запущено. Возвращаем данные пользователю.")
    return {
        "status": "provisioning",
        "fqdn": server_name,
        "browser_url": f"https://{server_name}",
        "connect_uri": f"neo4j+s://{server_name}:7687",
        "user": "neo4j",
        "initial_password_info": "При первом входе пароль не требуется. Система попросит вас создать свой новый пароль."
    }

if __name__ == '__main__':
    # Пример вызова функции
    # Это будет вызываться из твоего FastAPI/Flask эндпоинта
    result = provision_neo4j_for_client(SNAPSHOT_ID=304291995)
    print("\n--- РЕЗУЛЬТАТ ---")
    print(result)