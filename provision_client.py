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

load_dotenv()

# --- Константы из .env ---
HETZNER_API_TOKEN = os.getenv("HETZNER_API_TOKEN")
SSH_KEY_NAME = os.getenv("SSH_KEY_NAME")
YOUR_BASE_DOMAIN = os.getenv("YOUR_BASE_DOMAIN")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")

# --- СКРИПТ ДЛЯ ЗАПУСКА НА КЛИЕНТСКОЙ VM ---
BOOTSTRAP_INSTANCE_SCRIPT = """
#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/cloud-init-output.log|logger -t user-data -s 2>/dev/console) 2>&1

echo ">>> [1/2] Запуск сервера Neo4j..."
cd /home/neo4j_admin/neo4j_instance
sudo chown -R 7474:7474 ./ssl_certs
docker compose -f docker-compose.yml up -d

echo ">>> [2/2] Настройка файрвола..."
ufw allow 7473
ufw allow 7687
ufw allow ssh
ufw --force enable

echo "SUCCESS" > /home/neo4j_admin/provision_done
"""

def create_cloudflare_dns_record(fqdn, ip_address):
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}", "Content-Type": "application/json"}
    url = f"https://api.cloudflare.com/client/v4/zones/{CLOUDFLARE_ZONE_ID}/dns_records"
    data = {"type": "A", "name": fqdn, "content": ip_address, "ttl": 1, "proxied": True}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    print(f"DNS A-запись для '{fqdn}' -> {ip_address} создана.")

def provision_neo4j_for_client(location: str):
    client = Client(token=HETZNER_API_TOKEN)
    # Ищем наш снимок по имени
    snapshot = client.images.get_by_name(os.getenv("SNAPSHOT_NAME"))
    if not snapshot:
        raise Exception(f"Снимок '{os.getenv('SNAPSHOT_NAME')}' не найден!")

    subdomain = f"inst-{''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))}"
    fqdn = f"{subdomain}.{YOUR_BASE_DOMAIN}"

    # 1. Создание VM из снимка
    print(f"\n[1/3] Создание сервера '{fqdn}' из снимка...")
    response = client.servers.create(
        name=fqdn,
        server_type=ServerType(name="cx22"),
        image=snapshot,
        location=Location(name=location),
        ssh_keys=[client.ssh_keys.get_by_name(SSH_KEY_NAME)],
        user_data=BOOTSTRAP_INSTANCE_SCRIPT # <-- ЗАПУСКАЕМ НАСТРОЙКУ
    )
    server = response.server
    ip = server.public_net.ipv4.ip
    print(f"Сервер создан. IP: {ip}.")

    # 2. Создание A-записи в DNS
    print(f"\n[2/3] Создание DNS-записи...")
    create_cloudflare_dns_record(fqdn, ip)

    # 3. Возвращаем результат немедленно. Проверку готовности можно сделать отдельным API-вызовом.
    print(f"\n[3/3] Развертывание запущено. Возвращаем данные пользователю.")
    return {
        "status": "provisioning",
        "fqdn": fqdn,
        "browser_url": f"https://{fqdn}:7473",
        "connect_uri": f"neo4j+s://{fqdn}:7687",
        "user": "neo4j",
        "initial_password_info": "При первом входе пароль не требуется. Система попросит вас создать свой новый пароль."
    }

if __name__ == '__main__':
    # Пример вызова функции
    # Это будет вызываться из твоего FastAPI/Flask эндпоинта
    result = provision_neo4j_for_client(location="nbg1")
    print("\n--- РЕЗУЛЬТАТ ---")
    print(result)