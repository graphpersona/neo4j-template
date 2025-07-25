#!/bin/bash
set -e
echo ">>> [1/3] Install certbot..."
apt-get update
apt install -y software-properties-common
add-apt-repository -y ppa:certbot/certbot
apt update
apt install -y certbot python3-certbot-dns-cloudflare
certbot --version

echo ">>> [2/3] Get SSL certificate..."
certbot certonly --webroot -w /var/www/html -d $1

echo ">>> [3/3] Copy SSL certificate..."
cp /etc/letsencrypt/live/$1/fullchain.pem /home/neo4j_admin/neo4j_instance/ssl_certs/cert.pem
cp /etc/letsencrypt/live/$1/privkey.pem /home/neo4j_admin/neo4j_instance/ssl_certs/key.pem