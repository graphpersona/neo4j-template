#!/bin/bash
set -e
echo ">>> [1/4] Create a user 'neo4j_admin'..."
adduser neo4j_admin --disabled-password --gecos ""
usermod -aG sudo neo4j_admin
ufw allow 7473
ufw allow 7687
ufw allow ssh
ufw --force enable

mkdir -p /home/neo4j_admin/.ssh
cp /root/.ssh/authorized_keys /home/neo4j_admin/.ssh/
chown -R neo4j_admin:neo4j_admin /home/neo4j_admin/.ssh

echo ">>> [2/4] Installing Docker и Git..."
apt-get update
apt-get install -y ca-certificates curl gnupg dos2unix
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
usermod -aG docker neo4j_admin

echo ">>> [3/4] Creating a folder structure..."
sudo -u neo4j_admin mkdir -p /home/neo4j_admin/neo4j_instance/{conf,data,logs,ssl_certs,backups,import,plugins}
ls -l /root/repo_temp/templates/docker-compose.yml
ls -l /root/repo_temp/templates/neo4j.conf
chmod a+r /root/repo_temp/templates/docker-compose.yml \
          /root/repo_temp/templates/neo4j.conf
cp -v /root/repo_temp/templates/docker-compose.yml /home/neo4j_admin/neo4j_instance/
cp -v /root/repo_temp/templates/neo4j.conf /home/neo4j_admin/neo4j_instance/conf/
echo "cp exit code = $?"
stat -c '%n %s bytes (last mod: %y)' \
     /home/neo4j_admin/neo4j_instance/docker-compose.yml \
     /home/neo4j_admin/neo4j_instance/conf/neo4j.conf
chown -v neo4j_admin:neo4j_admin \
      /home/neo4j_admin/neo4j_instance/docker-compose.yml \
      /home/neo4j_admin/neo4j_instance/conf/neo4j.conf
stat -c '%n %s bytes (last mod: %y)' \
     /home/neo4j_admin/neo4j_instance/docker-compose.yml \
     /home/neo4j_admin/neo4j_instance/conf/neo4j.conf

