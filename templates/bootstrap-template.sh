#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/cloud-init-output.log|logger -t user-data -s 2>/dev/console) 2>&1

echo ">>> [1/4] Create a user 'neo4j_admin'..."
adduser neo4j_admin --disabled-password --gecos ""
usermod -aG sudo neo4j_admin
ufw allow 7473
ufw allow 7687
ufw allow ssh
ufw --force enable

# --- ИЗМЕНЕНИЕ: Ждем, пока cloud-init создаст ключ для root ---
echo ">>> Ожидание SSH ключа для root..."
while [ ! -f /root/.ssh/authorized_keys ]; do
  echo "...файл /root/.ssh/authorized_keys еще не создан, ждем 2 секунды..."
  sleep 2
done
echo ">>> SSH ключ для root найден!"

mkdir -p /home/neo4j_admin/.ssh
cp /root/.ssh/authorized_keys /home/neo4j_admin/.ssh/
chown -R neo4j_admin:neo4j_admin /home/neo4j_admin/.ssh

echo ">>> [2/4] Installing Docker и Git..."
apt-get update
apt-get install -y ca-certificates curl gnupg git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker neo4j_admin

echo ">>> [3/4] Creating a folder structure..."
sudo -u neo4j_admin mkdir -p /home/neo4j_admin/neo4j_instance/{{conf,data,logs,ssl_certs,backups,import,plugins}}

echo ">>> [4/4] Cloning a repository with templates..."
sudo -u neo4j_admin git clone ${GIT_REPO_URL} /tmp/repo_temp
sudo -u neo4j_admin cp /tmp/repo_temp/templates/docker-compose.yml /home/neo4j_admin/neo4j_instance/
sudo -u neo4j_admin cp /tmp/repo_temp/templates/neo4j.conf /home/neo4j_admin/neo4j_instance/conf/
rm -rf /tmp/repo_temp

echo ">>> Preparation complete. Cleaning..."
history -c
rm -f /root/.bash_history
rm -f /home/neo4j_admin/.bash_history
echo ">>> THE SYSTEM IS READY TO CREATE A IMAGE <<<"