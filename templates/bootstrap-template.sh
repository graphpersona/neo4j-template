#!/bin/bash
echo ">>> [1/4] Ufw..."
ufw allow 7473
ufw allow 7687
ufw allow ssh
ufw --force enable

echo ">>> [2/4] Installing Docker и Git..."
apt-get update
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker neo4j_admin

echo ">>> [3/4] Creating a folder structure..."
mkdir -p /home/neo4j_admin/neo4j_instance/{conf,data,logs,ssl_certs,backups,import,plugins}

echo ">>> [4/4] Cloning a repository with templates..."
cp /tmp/repo_temp/templates/docker-compose.yml /home/neo4j_admin/neo4j_instance/
cp /tmp/repo_temp/templates/neo4j.conf /home/neo4j_admin/neo4j_instance/conf/


echo ">>> Preparation complete. Cleaning..."
history -c
rm -f /root/.bash_history
rm -f /home/neo4j_admin/.bash_history
echo ">>> THE SYSTEM IS READY TO CREATE A IMAGE <<<"