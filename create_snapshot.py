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
client = Client(token=HETZNER_API_TOKEN)

# --- СКРИПТ, КОТОРЫЙ БУДЕТ ВЫПОЛНЕН НА ВРЕМЕННОЙ VM ---
BOOTSTRAP_SCRIPT = f"""
#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/cloud-init-output.log|logger -t user-data -s 2>/dev/console) 2>&1

echo ">>> [1/4] Создание пользователя 'neo4j_admin'..."
adduser neo4j_admin --disabled-password --gecos ""
usermod -aG sudo neo4j_admin
ufw allow 7473
ufw allow 7687
ufw allow ssh
ufw --force enable

mkdir -p /home/neo4j_admin/.ssh
cp /root/.ssh/authorized_keys /home/neo4j_admin/.ssh/
chown -R neo4j_admin:neo4j_admin /home/neo4j_admin/.ssh

echo ">>> [2/4] Установка Docker и Git..."
sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg && sudo install -m 0755 -d /etc/apt/keyrings && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg && sudo chmod a+r /etc/apt/keyrings/docker.gpg && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null && sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker neo4j_admin

echo ">>> [4/4] Создание структуры папок..."
sudo -u neo4j_admin mkdir -p /home/neo4j_admin/neo4j_instance/{{conf,data,logs,ssl_certs,backups,import,plugins}}

echo ">>> [3/4] Клонирование репозитория с шаблонами..."
sudo -u neo4j_admin git clone ${GIT_REPO_URL} /tmp/repo_temp
sudo -u neo4j_admin cp /tmp/repo_temp/templates/docker-compose.yml /home/neo4j_admin/neo4j_instance/
sudo -u neo4j_admin cp /tmp/repo_temp/templates/neo4j.conf /home/neo4j_admin/neo4j_instance/conf/
rm -rf /tmp/repo_temp

echo ">>> Подготовка завершена. Очистка..."
history -c
rm -f /root/.bash_history
rm -f /home/neo4j_admin/.bash_history
echo ">>> СИСТЕМА ГОТОВА К СОЗДАНИЮ СНИМКА <<<"
"""

def main():
    print("--- СОЗДАНИЕ ЗОЛОТОГО СНИМКА ---")
    server = None
    try:
        print("\n[1/4] Создание временного сервера...")
        response = client.servers.create(
            name="snapshot-builder",
            server_type=ServerType(name="cx22"),
            location=Location(name="nbg1"),
            image=Image(name="ubuntu-24.04"),
            ssh_keys=[client.ssh_keys.get_by_name(SSH_KEY_NAME)],
            start_after_create=True,
            user_data=BOOTSTRAP_SCRIPT # <-- СКРИПТ ПЕРЕДАЕТСЯ ЗДЕСЬ
        )
        server = response.server
        print(f"Сервер '{server.name}' создан. IP: {server.public_net.ipv4.ip}. Ожидание завершения bootstrap-скрипта...")
                
        # Простой способ дождаться завершения скрипта - подождать некоторое время
        time.sleep(180) # 3 минуты на установку Docker и т.д.

        print("\n[2/4] Копирование сертификатов на сервер...")
        ip = server.public_net.ipv4.ip
        # Копируем локальные сертификаты в папку ssl_certs, которую создал bootstrap-скрипт
        subprocess.run(f"scp -o StrictHostKeyChecking=no certs/cert.pem neo4j_admin@{ip}:/home/neo4j_admin/neo4j_instance/ssl_certs/", shell=True, check=True)
        subprocess.run(f"scp -o StrictHostKeyChecking=no certs/key.pem neo4j_admin@{ip}:/home/neo4j_admin/neo4j_instance/ssl_certs/", shell=True, check=True)
        
        print("\n[3/4] Остановка сервера и создание снимка...")
        server.power_off().wait_until_finished()
        image_action = server.create_image(description="Golden Image for Neo4j", type="snapshot", name=SNAPSHOT_NAME)
        image_action.wait_until_finished()
        image = client.images.get_by_id(image_action.image.id)
        print(f"Снимок '{image.name}' (ID: {image.id}) успешно создан!")

    finally:
        if server:
            print(f"\n[4/4] Удаление временного сервера...")
            server.delete()
            print("Временный сервер удален.")

if __name__ == "__main__":
    main()