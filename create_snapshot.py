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

def main():
    print("--- CREATING A GOLDEN SNAPSHOT ---")
    server = None
    try:
        print("\n[1/4] Creating a temporary server...")
        # добавить цикл - выбор другой локации если вдруг ошибка
        response = client.servers.create(
            name="snapshot-builder",
            server_type=ServerType(name="cx22"),
            location=Location(name="hel1"),
            image=Image(name="ubuntu-24.04"),
            ssh_keys=[client.ssh_keys.get_by_name(SSH_KEY_NAME)],
            start_after_create=True,
        )
        server = response.server
        print(f"Server '{server.name}' created. IP: {server.public_net.ipv4.ip}. Waiting for bootstrap script to complete...")
        ip = server.public_net.ipv4.ip
        print(f"Сервер '{server.name}' создан. IP: {ip}.")

        # 2. Ожидание доступности SSH
        print("\n[2/5] Ожидание доступности SSH на сервере...")
        # Собираем команду SSH с явным указанием ключа и отключением паролей
        ssh_check_command = [
            "ssh",
            "-i", SSH_PRIVATE_KEY_PATH, # <-- Указываем наш ключ
            "-o", "StrictHostKeyChecking=no",
            "-o", "PasswordAuthentication=no", # <-- Запрещаем спрашивать пароль
            "-o", "ConnectTimeout=10",
            f"root@{ip}",
            "echo 'SSH is up'"
        ]
        for _ in range(30): # Ждем максимум 5 минут
            try:
                subprocess.run(ssh_check_command, check=True, capture_output=True, text=True, timeout=15)
                print(">>> SSH доступен.")
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                print("...сервер еще не готов, ждем 10 секунд...")
                time.sleep(10)
        else:
            raise Exception("Не удалось подключиться к серверу по SSH за 5 минут.")
        
        # 3. Создание пользователя neo4j_admin
        create_user_command = f"""sudo apt-get update && sudo apt-get install -y git && git clone {GIT_REPO_URL} ~/repo_temp && bash ~/repo_temp/templates/bootstrap-template.sh"""
        create_user_run_command = [
            "ssh",
            "-i", SSH_PRIVATE_KEY_PATH,
            f"root@{ip}",
            "bash", "-s"
        ]
        subprocess.run(
            create_user_run_command, 
            input=create_user_command, 
            text=True,
            check=True
        )
        print(">>> Пользователь neo4j_admin создан.")
            
        print(">>> Скрипт подготовки выполнен.")
        
        # 4. Копирование сертификатов
        print("\n[4/5] Копирование сертификатов на сервер...")
        scp_command_base = f"scp -i {SSH_PRIVATE_KEY_PATH} -o StrictHostKeyChecking=no -o PasswordAuthentication=no"
        subprocess.run(f"{scp_command_base} certs/cert.pem neo4j_admin@{ip}:/home/neo4j_admin/neo4j_instance/ssl_certs/", shell=True, check=True)
        subprocess.run(f"{scp_command_base} certs/key.pem neo4j_admin@{ip}:/home/neo4j_admin/neo4j_instance/ssl_certs/", shell=True, check=True)

        print("\n[5/5] Docker neo4j compose...")
        change_command = f"""sudo dos2unix /home/neo4j_admin/neo4j_instance/ssl_certs/key.pem && sudo dos2unix /home/neo4j_admin/neo4j_instance/ssl_certs/cert.pem && sudo chown -R 7474:7474 /home/neo4j_admin/neo4j_instance/ssl_certs/ && sudo chmod o+x /home/neo4j_admin && docker compose -f /home/neo4j_admin/neo4j_instancedocker-compose.yml up -d""" 
        subprocess.run(
            create_user_run_command, 
            input=change_command, 
            text=True,
            check=True
        )
    
    #    time.sleep(5)
        # 5. Создание снимка
     #   print("\n[5/5] Остановка сервера и создание снимка...")
     #   server.power_off().wait_until_finished()
     #   image_action = server.create_image(description=SNAPSHOT_NAME, type="snapshot")
     #   image = client.images.get_by_id(image_action.image.id)
      #  print(f"Снимок '{image.description}' (ID: {image.id}) успешно создан!")

    finally:
        if server:
            print(f"\n[4/4] Removing a temporary server...")
        #    server.delete()
            print("Temporary server removed.")

if __name__ == "__main__":
    main()