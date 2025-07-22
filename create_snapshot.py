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

# --- SCRIPT THAT WILL BE EXECUTED ON TEMPORARY VM ---

def main():
    print("--- CREATING A GOLDEN SNAPSHOT ---")
    server = None
    try:
        print("\n[1/4] Creating a temporary server...")
        response = client.servers.create(
            name="snapshot-builder",
            server_type=ServerType(name="cx22"),
            location=Location(name="nbg1"),
            image=Image(name="ubuntu-24.04"),
            ssh_keys=[client.ssh_keys.get_by_name(SSH_KEY_NAME)],
            start_after_create=True
        )
        server = response.server
        print(f"Server '{server.name}' created. IP: {server.public_net.ipv4.ip}. Waiting for bootstrap script to complete...")
        ip = server.public_net.ipv4.ip
        print(f"Сервер '{server.name}' создан. IP: {ip}.")

        # 2. Ожидание доступности SSH
        print("\n[2/5] Ожидание доступности SSH на сервере...")
        for _ in range(30): # Ждем максимум 5 минут
            try:
                subprocess.run(
                    ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10", f"root@{ip}", "echo 'SSH is up'"],
                    check=True, capture_output=True, text=True, timeout=10
                )
                print(">>> SSH доступен.")
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                print("...сервер еще не готов, ждем 10 секунд...")
                time.sleep(10)
        else:
            raise Exception("Не удалось подключиться к серверу по SSH за 5 минут.")
            
        # 3. Запуск bootstrap-скрипта через SSH
        print(f"\n[3/5] Запуск скрипта подготовки на сервере...")
        # Мы передаем весь скрипт в одну SSH-команду
        subprocess.run(
            f"ssh -o StrictHostKeyChecking=no root@{ip} 'bash -s' < templates/bootstrap-template.sh",
            shell=True,
            check=True
        )
        print(">>> Скрипт подготовки выполнен.")
        
        # 4. Копирование сертификатов
        print("\n[4/5] Копирование сертификатов на сервер...")
        subprocess.run(f"scp -o StrictHostKeyChecking=no certs/cert.pem neo4j_admin@{ip}:/home/neo4j_admin/neo4j_instance/ssl_certs/", shell=True, check=True)
        subprocess.run(f"scp -o StrictHostKeyChecking=no certs/key.pem neo4j_admin@{ip}:/home/neo4j_admin/neo4j_instance/ssl_certs/", shell=True, check=True)
        
        # 5. Создание снимка
        print("\n[5/5] Остановка сервера и создание снимка...")
        server.power_off().wait_until_finished()
        image_action = server.create_image(description="Golden Image for Neo4j", type="snapshot", name=SNAPSHOT_NAME)
        image_action.wait_until_finished()
        image = client.images.get_by_id(image_action.image.id)
        print(f"Снимок '{image.name}' (ID: {image.id}) успешно создан!")

    finally:
        if server:
            print(f"\n[4/4] Removing a temporary server...")
        #    server.delete()
            print("Temporary server removed.")

if __name__ == "__main__":
    main()