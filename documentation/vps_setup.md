# VPS Setup & Traefik Deployment Guide

This guide explains how to set up a brand-new Ubuntu VPS from scratch to host the project, integrate GitHub Actions CI/CD, and configure Traefik as a reverse proxy with automated SSL (Let's Encrypt).

---

## Part 1: Initial VPS Configuration

Connect to your VPS as `root` via SSH:
```bash
ssh root@YOUR_SERVER_IP
```

### 1. Update the System
```bash
apt update && apt upgrade -y
```

### 2. Install Docker & Docker Compose
The easiest way is using the official Docker install script:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

Verify that Docker is installed:
```bash
docker --version
docker compose version
```

### 3. Configure the Firewall
Ensure that SSH, HTTP, and HTTPS ports are open:
```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

## Part 2: Folder Structure & Git Setup

We will place the application in `/var/www/backend`.

### 1. Create the Project Directory
```bash
mkdir -p /var/www/backend
```

### 2. Set Up SSH Key for GitHub Actions
GitHub Actions needs access to run commands on your server.
1. **On your local machine or server**, generate a new SSH Key:
   ```bash
   ssh-keygen -t ed25519 -C "github-actions-deploy"
   ```
   *(Press Enter to save in the default path and leave the passphrase empty).*
2. Add the **public key** (`id_ed25519.pub`) to the server's authorized keys:
   ```bash
   cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   chmod 700 ~/.ssh
   ```
3. Copy the **private key** (`id_ed25519`). You will add this key to your GitHub repository secrets:
   * Go to **GitHub Repository** -> **Settings** -> **Secrets and variables** -> **Actions**.
   * Create a new repository secret:
     * **Name**: `SERVER_SSH_KEY`
     * **Value**: Paste the entire contents of the private key (`id_ed25519`).
   * Create another repository secret:
     * **Name**: `SERVER_HOST`
     * **Value**: Your server's public IP address.

### 3. Initialize Git Repository on the Server
```bash
cd /var/www/backend
git init
git remote add origin YOUR_GITHUB_REPOSITORY_SSH_OR_HTTPS_URL
```

---

## Part 3: Setting Up Traefik Reverse Proxy

To route multiple websites/services and get automatic SSL certificates, we will run Traefik on the VPS.

### 1. Create a Docker Network for Traefik
```bash
docker network create web
```

### 2. Create the Traefik Directory and Configs
Create a folder for Traefik configuration:
```bash
mkdir -p /opt/traefik
touch /opt/traefik/acme.json
chmod 600 /opt/traefik/acme.json
```

Create `/opt/traefik/docker-compose.yml`:
```yaml
version: "3.8"

services:
  traefik:
    image: traefik:v2.10
    container_name: traefik
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - /opt/traefik/acme.json:/acme.json
    command:
      - "--providers.docker=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      # Global redirection to HTTPS
      - "--entrypoints.web.http.redirections.entryPoint.to=websecure"
      - "--entrypoints.web.http.redirections.entryPoint.scheme=https"
      # Let's Encrypt configurations
      - "--certificatesresolvers.myresolver.acme.tlschallenge=true"
      - "--certificatesresolvers.myresolver.acme.email=YOUR_EMAIL@example.com"
      - "--certificatesresolvers.myresolver.acme.storage=/acme.json"
    networks:
      - web

networks:
  web:
    external: true
```
Replace `YOUR_EMAIL@example.com` with your actual email address (used for SSL expiry notifications).

Start Traefik:
```bash
cd /opt/traefik
docker compose up -d
```

---

## Part 4: Connect Backend to Traefik

To route traffic from Traefik to your backend `api` container, modify the backend `api` service inside `docker-compose.prod.yml` on your server to include Traefik labels and connect it to the `web` network.

### Example configuration labels to add to `api` in `docker-compose.prod.yml`:
```yaml
  api:
    # ... existing configs ...
    networks:
      - shared_network
      - web
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.bilim-api.rule=Host(`api.yourdomain.com`)" # Replace with your domain
      - "traefik.http.routers.bilim-api.entrypoints=websecure"
      - "traefik.http.routers.bilim-api.tls.certresolver=myresolver"
      - "traefik.http.services.bilim-api.loadbalancer.server.port=8000"
```
*(Also add `web` network as external at the bottom of the compose file).*

---

## Part 5: Bootstrapping the Backend

Before running the GitHub Actions workflow for the first time:

1. **Pull the code manually on the server**:
   ```bash
   cd /var/www/backend
   git fetch origin master
   git reset --hard origin/master
   ```
2. **Create the production environment file**:
   Create `/var/www/backend/.env` with your production variables:
   ```bash
   POSTGRES_DB=app
   POSTGRES_USER=app
   POSTGRES_PASSWORD=your_secure_db_password
   DATABASE_URL=postgresql+asyncpg://app:your_secure_db_password@postgres-db:5432/app
   JWT_SECRET_KEY=your_super_secret_jwt_key
   # Add any other config fields required by config.py
   ```
3. **Run your migrations**:
   ```bash
   docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
   ```
4. **Boot the project**:
   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

Subsequent push commits to the `master` branch will trigger the GitHub Actions workflow to auto-pull, rebuild, and hot-reload the containers!
