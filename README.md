# Neo4j Cloud Template

An automated infrastructure template for deploying Neo4j database instances on Hetzner Cloud with SSL certificates and DNS management.

## Features

- 🚀 **Automated Neo4j Deployment**: One-click deployment of Neo4j instances with SSL/TLS encryption
- 🔒 **SSL/TLS Security**: Automatic SSL certificate provisioning via Let's Encrypt and Cloudflare DNS
- 🐳 **Docker-based**: Containerized Neo4j deployment with persistent data storage
- 📸 **Golden Snapshots**: Create and manage pre-configured server snapshots for fast deployment
- 🌐 **DNS Integration**: Automatic subdomain creation and DNS record management via Cloudflare
- 🔧 **Plugin Support**: Pre-configured with APOC and Graph Data Science (GDS) plugins

## Architecture

This template provides two main workflows:

### 1. Snapshot Creation (`create_snapshot.py`)
Creates a "golden" server snapshot with pre-installed and configured Neo4j:
- Provisions a temporary Hetzner Cloud server
- Installs Docker, Neo4j, and required dependencies
- Configures SSL certificates and security settings
- Creates a reusable snapshot for fast deployment

### 2. Client Provisioning (`provision_client.py`)
Deploys new Neo4j instances from the golden snapshot:
- Creates a new server from the pre-built snapshot
- Generates unique subdomain and SSL certificates
- Configures DNS records via Cloudflare
- Starts Neo4j with SSL/TLS enabled

## Prerequisites

- **Hetzner Cloud Account** with API token
- **Cloudflare Account** with API token and zone management
- **SSH Key Pair** for server access
- **Domain** managed by Cloudflare
- **Email Address** for SSL certificate registration

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/graphpersona/neo4j-template.git
   cd neo4j-template
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Required packages:
   - `hcloud` - Hetzner Cloud API client
   - `requests` - HTTP requests
   - `python-dotenv` - Environment variable management

3. **Configure environment variables**
   ```bash
   cp env_template .env
   ```
   
   Edit `.env` with your credentials:
   ```env
   # Hetzner Cloud
   HETZNER_API_TOKEN="your_hetzner_api_token"
   SSH_KEY_NAME="your_ssh_key_name"
   
   # Cloudflare
   CLOUDFLARE_API_TOKEN="your_cloudflare_api_token"
   CLOUDFLARE_ZONE_ID="your_cloudflare_zone_id"
   YOUR_BASE_DOMAIN="db.yourdomain.com"
   
   # SSL & Contact
   SSL_EMAIL="your_email@example.com"
   SSH_PRIVATE_KEY_PATH="/path/to/your/private_key"
   
   # Snapshot Configuration
   SNAPSHOT_NAME="neo4j-docker-template-v1"
   GIT_REPO_URL="https://github.com/graphpersona/neo4j-template.git"
   ```

4. **Prepare SSL certificates** (optional)
   Place your SSL certificates in the `certs/` directory:
   - `cert.pem` - SSL certificate
   - `key.pem` - Private key

## Usage

### Creating a Golden Snapshot

Run this once to create a reusable server image:

```bash
python create_snapshot.py
```

This will:
- Create a temporary Ubuntu server
- Install Docker and Neo4j
- Configure security and SSL
- Create a snapshot for reuse
- Clean up temporary resources

### Provisioning a New Neo4j Instance

Deploy a new Neo4j instance from the snapshot:

```bash
python provision_client.py
```

This returns connection details:
```json
{
  "status": "provisioning",
  "fqdn": "inst-abc123def456.db.yourdomain.com",
  "browser_url": "https://inst-abc123def456.db.yourdomain.com",
  "connect_uri": "neo4j+s://inst-abc123def456.db.yourdomain.com:7687",
  "user": "neo4j",
  "initial_password_info": "At first login, the password is not required. The system will ask you to create a new password."
}
```

### Accessing Neo4j

1. **Web Browser**: Navigate to the `browser_url` (HTTPS on port 443)
2. **Neo4j Driver**: Connect using the `connect_uri` (Bolt+SSL on port 7687)
3. **Initial Login**: Username: `neo4j`, no password required on first login

## Configuration

### Neo4j Configuration

The deployed Neo4j instance includes:

- **Version**: Neo4j 2025.06.2
- **Plugins**: APOC, Graph Data Science (GDS)
- **Security**: SSL/TLS enabled for both HTTP and Bolt protocols
- **Authentication**: Default Neo4j authentication
- **Storage**: Persistent volumes for data, logs, and configuration

### Server Specifications

- **Europe Zone**: cx22 (2 vCPU, 4GB RAM)
- **Other Zones**: cpx11 (2 vCPU, 2GB RAM)
- **Storage**: 40GB SSD
- **Network**: Public IPv4 with firewall rules

### Firewall Configuration

Automatically configured ports:
- `443/tcp` - HTTPS (Neo4j Browser)
- `7687/tcp` - Neo4j Bolt protocol
- `22/tcp` - SSH access

## Project Structure

```
neo4j-template/
├── provision_client.py      # Main provisioning script
├── create_snapshot.py       # Snapshot creation script
├── utils.py                 # Utility functions
├── env_template            # Environment variables template
├── certs/                  # SSL certificates directory
└── templates/
    ├── bootstrap-template.sh   # Server setup script
    ├── docker-compose.yml     # Neo4j Docker configuration
    └── neo4j.conf            # Neo4j configuration file
```

## Security Features

- **SSL/TLS Encryption**: All connections encrypted with Let's Encrypt certificates
- **Firewall Protection**: Restrictive firewall rules
- **SSH Key Authentication**: Password authentication disabled
- **Secure Defaults**: Neo4j configured with security best practices
- **Automated Updates**: Ubuntu security updates enabled

## Troubleshooting

### Common Issues

1. **SSH Connection Failures**
   - Verify SSH key path and permissions
   - Check Hetzner SSH key configuration

2. **DNS Resolution Issues**
   - Verify Cloudflare API token permissions
   - Check zone ID and domain configuration

3. **SSL Certificate Errors**
   - Ensure email address is valid
   - Check Cloudflare DNS propagation

### Logs and Debugging

- Server logs available via SSH: `/home/neo4j_admin/neo4j_instance/logs/`
- Docker logs: `docker logs neo4j_user`
- Neo4j logs: Check Docker container logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue in this repository
- Check the [Neo4j Documentation](https://neo4j.com/docs/)
- Review [Hetzner Cloud API Documentation](https://docs.hetzner.cloud/)

## Acknowledgments

- [Neo4j](https://neo4j.com/) for the graph database
- [Hetzner Cloud](https://www.hetzner.com/cloud) for cloud infrastructure
- [Cloudflare](https://www.cloudflare.com/) for DNS and SSL services
- [Let's Encrypt](https://letsencrypt.org/) for free SSL certificates
