# VPS Setup & Nginx Deployment Guide

This guide explains how to set up a brand-new Ubuntu VPS from scratch to host the project, configure Nginx as a reverse proxy with automated SSL (Let's Encrypt), and deploy using the GitHub Actions CI/CD pipeline.

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

We will place the application in `/var/www/bilim`.

### 1. Create the Project Directory
```bash
mkdir -p /var/www/bilim
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
cd /var/www/bilim
git init
git remote add origin YOUR_GITHUB_REPOSITORY_SSH_OR_HTTPS_URL
```

---

## Part 3: Setting Up Nginx Reverse Proxy

To route incoming traffic on ports 80/443 to your backend container running on port 8000, install and configure Nginx on the host VPS.

### 1. Install Nginx
```bash
sudo apt update
sudo apt install nginx -y
```

### 2. Install Certbot for Let's Encrypt SSL
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 3. Create Nginx Site Configuration
Create a configuration file for your backend API:
```bash
sudo nano /etc/nginx/sites-available/backend
```

Paste the following configuration, replacing `api.yourdomain.com` with your actual domain or IP:
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Enable Configuration and Restart Nginx
Enable the site by symlinking it to the `sites-enabled` directory:
```bash
sudo ln -s /etc/nginx/sites-available/backend /etc/nginx/sites-enabled/
```

Test Nginx configuration:
```bash
sudo nginx -t
```

If the test is successful, reload Nginx:
```bash
sudo systemctl reload nginx
```

---

## Part 4: Configure Let's Encrypt SSL

Run Certbot to automatically fetch and configure the SSL certificate for your domain:
```bash
sudo certbot --nginx -d api.yourdomain.com
```
Follow the interactive prompts to complete the setup. Certbot will automatically rewrite the Nginx configuration to route HTTPS traffic securely and redirect HTTP to HTTPS.

---

## Part 5: Bootstrapping the Backend

Before running the GitHub Actions workflow for the first time:

1. **Pull the code manually on the server**:
   ```bash
   cd /var/www/bilim
   git fetch origin master
   git reset --hard origin/master
   ```
2. **Create the production environment file**:
   Create `/var/www/bilim/.env` with your production variables:
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
   docker compose -f docker/docker-compose.prod.yml run --rm api alembic upgrade head
   ```
4. **Boot the project**:
   ```bash
   docker compose -f docker/docker-compose.prod.yml up -d --build
   ```

Subsequent push commits to the `master` branch will trigger the GitHub Actions workflow to auto-pull, rebuild, and hot-reload the containers!
