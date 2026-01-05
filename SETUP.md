# DGX Web UI - Setup Guide

This guide walks through setting up and customizing the DGX Web UI for your environment.

## Initial Setup

### 1. Configure Deployment Credentials

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` with your server details:

```bash
DGX_HOST=your-server-ip-or-hostname
DGX_USER=your-username
DGX_PASS=your-password  # Optional if using SSH keys
REMOTE_DIR=/path/to/deployment  # Optional, defaults to /home/$USER/dgx-web-ui
```

**Security Note:** The `.env` file is excluded from git. Never commit credentials to the repository.

### 2. Configure Ollama CORS

Ollama must allow cross-origin requests from the web UI:

```bash
# If using snap:
sudo snap set ollama origins='*'
sudo snap restart ollama

# If using systemd:
sudo nano /etc/systemd/system/ollama.service
# Add: Environment="OLLAMA_ORIGINS=*"
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### 3. Copy and Configure deploy.sh

```bash
cp deploy.sh.example deploy.sh
chmod +x deploy.sh
```

The script will automatically load configuration from `.env`.

### 4. Deploy

```bash
./deploy.sh deploy
```

## Customizing for Your Environment

### Network Configuration

The Dashboard and Mobile views display network information. To customize:

**Option 1: Environment Variables (recommended)**

Add to your `.env`:
```bash
LOCAL_NETWORK_IP=192.168.1.xxx
VPN_NETWORK_IP=100.xxx.xxx.xxx
```

**Option 2: Direct Edit**

Edit these files:
- `src/constants/mobileConstants.js` - Mobile constants
- `src/components/Dashboard.vue` - Desktop dashboard

Change the `network` object:
```javascript
export const network = {
  local: { name: 'Local Network', ip: '192.168.1.xxx' },
  vpn: { name: 'VPN', ip: '100.xxx.xxx.xxx' }
}
```

### Hardware Specifications

Update hardware specs in:
- `src/constants/mobileConstants.js`
- `src/components/Dashboard.vue`

```javascript
export const hardware = {
  gpu: { name: 'Your GPU', arch: 'Architecture', compute: 'Compute specs' },
  cpu: { name: 'Your CPU', detail: 'CPU details' },
  memory: { size: 'XX GB', type: 'Memory type', bandwidth: 'XXX GB/s' },
  storage: { size: 'X TB', free: '~X.X TB' }
}
```

### Available Models

Customize the model lists based on what you have installed:

In `src/constants/mobileConstants.js` and `src/components/Dashboard.vue`:

```javascript
export const availableModels = {
  llm: ['model1', 'model2', ...],
  video: ['video-model1', ...],
  image: ['image-model1', ...],
  audio: ['audio-model1', ...]
}
```

### Service Links

Update service ports and links in:
- `src/constants/mobileConstants.js` (mobile)
- `src/components/Dashboard.vue` (desktop)

```javascript
export const serviceLinks = [
  { name: 'Service Name', icon: '🔧', port: 8080, desc: 'Description' },
  // ...
]
```

### API Endpoints

**Local Development:**
Edit `public/config.js` to point to your tunneled/local services:

```javascript
window.DGX_CONFIG = {
  COMFYUI_URL: 'http://localhost:11005',
  OLLAMA_URL: 'http://localhost:11434',
  ULTRAVOX_URL: 'http://localhost:11100',
  CHATTERBOX_URL: 'http://localhost:11004',
  TELEMETRY_URL: 'http://localhost:11006',
  APP_NAME: 'Your UI Name',
  VERSION: '1.0.0'
};
```

**Production (on server):**
Edit `config.dgx.js` to use nginx proxies or direct ports:

```javascript
window.DGX_CONFIG = {
  COMFYUI_URL: '/comfyui',  // Via nginx proxy
  OLLAMA_URL: '/ollama',
  // ...
};
```

## Backend API Configuration

The backend API (`backend/main.py`) may need customization for your environment:

### 1. Service Container Names

Edit `MANAGED_SERVICES` dict with your container names:

```python
MANAGED_SERVICES = {
    "comfyui": {"container": "your-comfyui-container", "description": "Description"},
    # ...
}
```

### 2. System Paths

Update paths if your system differs:

```python
CLAUDE_PATH = os.path.expanduser("~/.local/bin/claude")
SESSIONS_FILE = os.path.expanduser("~/.dgx-web-ui-sessions.json")
```

### 3. Trinity Integration (Optional)

If using Trinity, update paths in:
```python
@app.get("/api/trinity/status")
async def get_trinity_status():
    # ...
    result = subprocess.run(
        ["git", "-C", os.path.expanduser("~/your-trinity-path"), ...
```

## Docker Compose Customization

Edit `docker-compose.yml` to match your environment:

### Ports

```yaml
services:
  dgx-web-ui:
    ports:
      - "3080:80"  # Change 3080 to your preferred port
  dgx-api:
    ports:
      - "3081:8080"  # Change 3081 to your preferred port
```

### User/Group IDs

```yaml
  dgx-api:
    user: "1000:1000"  # Your user:group IDs
    group_add:
      - "988"  # Docker group ID (check with: getent group docker)
```

### Volume Mounts

```yaml
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /home/eugene:/home/eugene  # Change to your home directory
```

## PWA Customization

### App Name and Icon

Edit `public/manifest.json`:

```json
{
  "name": "Your App Name",
  "short_name": "Short Name",
  "description": "Your description",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ],
  "start_url": "/?mobile=1",
  "display": "standalone"
}
```

Replace icon files in `public/icons/`:
- `icon-192.png` - 192x192 PNG
- `icon-512.png` - 512x512 PNG
- `apple-touch-icon.png` - 180x180 PNG for iOS

## Testing

### Local Development

```bash
npm install
npm run dev
# Open http://localhost:3000
```

### Production Build

```bash
npm run build
# Output in dist/
```

### Deployment Test

```bash
./deploy.sh sync    # Test file sync
./deploy.sh build   # Test Docker build
./deploy.sh start   # Start containers
./deploy.sh status  # Check status
```

## Troubleshooting

### Deployment Issues

**SSH Connection Failed:**
- Check `DGX_HOST` is reachable: `ping $DGX_HOST`
- Test SSH manually: `ssh $DGX_USER@$DGX_HOST`
- Verify credentials in `.env`

**Permission Denied:**
- Ensure user has sudo access or Docker group membership
- Check Docker socket permissions: `ls -l /var/run/docker.sock`

### Runtime Issues

**CORS Errors:**
- Verify Ollama CORS is configured (see step 2 above)
- Check nginx proxy configuration in `nginx.conf`

**Container Not Starting:**
- Check logs: `./deploy.sh logs`
- Verify port conflicts: `sudo netstat -tlnp | grep 3080`
- Check Docker: `sudo docker ps -a`

**API Endpoints Not Working:**
- Verify services are running on expected ports
- Check firewall rules
- Test endpoints directly: `curl http://localhost:8188/system_stats`

## Security Checklist

- [ ] `.env` file is not committed to git
- [ ] SSH keys used instead of password (recommended)
- [ ] Firewall configured to restrict access
- [ ] HTTPS configured for production (reverse proxy)
- [ ] Docker socket access limited to trusted users
- [ ] Regular security updates applied

## Next Steps

1. Customize network/hardware info for your system
2. Update model lists based on what you have installed
3. Configure SSL/HTTPS via reverse proxy (nginx/Caddy)
4. Set up monitoring/alerting
5. Configure backups for user data

For more help, see:
- [README.md](README.md) - Main documentation
- [Docker Compose docs](https://docs.docker.com/compose/)
- [Vue 3 docs](https://vuejs.org/)
