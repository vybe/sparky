# Configuration Guide - Customize for Your Instance

This guide explains how to configure the DGX Web UI for your specific hardware, network, and services.

## Required Configuration

### 1. Deployment Credentials (.env file)

Create `.env` from the example:

```bash
cp .env.example .env
```

Edit with your values:

```bash
# Required
DGX_HOST=192.168.1.100           # Your server IP or hostname
DGX_USER=youruser                # Your SSH username
DGX_PASS=yourpassword            # Your SSH password (or omit if using SSH keys)

# Optional
REMOTE_DIR=/home/$USER/dgx-web-ui   # Custom deployment directory
```

**Using SSH Keys (Recommended):**

```bash
# Generate key
ssh-keygen -t ed25519 -C "you@example.com"

# Copy to server
ssh-copy-id youruser@192.168.1.100

# In .env, omit DGX_PASS
DGX_HOST=192.168.1.100
DGX_USER=youruser
# DGX_PASS not needed
```

### 2. Network Display Configuration

The Dashboard and Mobile views show your network information. Update these files with your actual IPs.

#### File: `src/constants/mobileConstants.js`

```javascript
export const network = {
  local: {
    name: 'Local Network',
    ip: '192.168.1.100'           // ← Your local network IP
  },
  vpn: {
    name: 'Tailscale VPN',        // ← Your VPN name (Tailscale, WireGuard, etc.)
    ip: '100.64.0.100'            // ← Your VPN IP
  }
}
```

#### File: `src/components/Dashboard.vue` (lines ~8-19)

Update the same `network` object:

```javascript
const network = {
  local: {
    name: 'Local Network',
    ip: '192.168.1.100',          // ← Your local network IP
    description: 'Direct connection when on same network'
  },
  tailscale: {
    name: 'Tailscale VPN',
    ip: '100.64.0.100',           // ← Your VPN IP
    description: 'Remote access via VPN'
  }
}
```

**Finding Your IPs:**

```bash
# Local network IP
ip addr show | grep "inet 192"
# or
ifconfig | grep "inet 192"

# Tailscale IP
tailscale ip -4

# WireGuard IP
sudo wg show
```

### 3. Hardware Specifications

Update hardware info displayed in the Status/Dashboard pages.

#### File: `src/constants/mobileConstants.js`

```javascript
export const hardware = {
  gpu: {
    name: 'NVIDIA RTX 4090',      // ← Your GPU name
    arch: 'Ada Lovelace',         // ← GPU architecture
    compute: '82.6 TFLOPs FP32'   // ← Compute specs
  },
  cpu: {
    name: '16-core AMD Ryzen',    // ← Your CPU
    detail: 'Ryzen 9 7950X'       // ← CPU details
  },
  memory: {
    size: '64 GB',                // ← Your RAM size
    type: 'DDR5',                 // ← Memory type
    bandwidth: '89.6 GB/s'        // ← Memory bandwidth
  },
  storage: {
    size: '2 TB NVMe',            // ← Storage size
    free: '~1.5 TB'               // ← Free space (optional)
  }
}
```

#### File: `src/components/Dashboard.vue` (lines ~74-94)

Update the same `hardware` object with your specs.

**Finding Your Hardware Info:**

```bash
# GPU
nvidia-smi --query-gpu=name --format=csv,noheader

# CPU
lscpu | grep "Model name"

# Memory
free -h | grep Mem

# Disk
df -h /
```

### 4. Available Models

List the models you have installed.

#### File: `src/constants/mobileConstants.js`

```javascript
export const availableModels = {
  llm: [
    'llama3.2:70b',               // ← Your Ollama LLM models
    'mistral:7b',
    'qwen2.5:14b'
  ],
  video: [
    'LTX Video 2B',               // ← Your video generation models
    'CogVideoX'
  ],
  image: [
    'Stable Diffusion XL',        // ← Your image generation models
    'Flux.1 Dev',
    'Pony Diffusion'
  ],
  audio: [
    'Whisper Large v3',           // ← Your audio models
    'Chatterbox TTS'
  ]
}
```

**Check Installed Models:**

```bash
# Ollama models
ollama list

# ComfyUI models
ls ~/ComfyUI/models/checkpoints/
ls ~/ComfyUI/models/diffusion_models/
```

#### Update Model Lists in Dashboard

File: `src/components/Dashboard.vue` (lines ~97-110)

```javascript
const models = {
  llm: [
    { name: 'llama3.2:70b', size: '40GB', speed: '45 tok/s' },
    { name: 'mistral:7b', size: '4.1GB', speed: '120 tok/s' },
    // ... your models
  ],
  video: [
    { name: 'LTX Video 2B', size: '6GB', time: '~5s/frame' },
    // ... your models
  ],
  // ...
}
```

### 5. Service Links and Ports

Update service ports if they differ from defaults.

#### File: `src/constants/mobileConstants.js`

```javascript
export const serviceLinks = [
  { name: 'Open WebUI', icon: '💬', port: 8080, desc: 'Chat UI' },
  { name: 'ComfyUI', icon: '🎨', port: 8188, desc: 'Image/Video' },
  // Add your services here
]
```

#### Verify Services Are Running:

```bash
# Check if services are accessible
curl http://localhost:11434/api/version    # Ollama
curl http://localhost:8188/system_stats    # ComfyUI
curl http://localhost:8100/v1/models       # Ultravox (if installed)
curl http://localhost:8004/voices          # Chatterbox (if installed)
```

## Optional Configuration

### Image Generation Models

Update available image models for the Image Generator.

File: `src/constants/mobileConstants.js`

```javascript
export const imageModels = [
  { id: 'sd_xl_base_1.0.safetensors', name: 'SDXL Base', type: 'sdxl' },
  { id: 'your-model.safetensors', name: 'Your Model', type: 'sdxl' },
  // Add your installed models
]
```

### Video Generation Models

File: `src/constants/mobileConstants.js`

```javascript
export const videoModels = [
  { id: 'ltxv-2b.safetensors', name: 'LTX 2B', steps: 20 },
  { id: 'your-video-model.safetensors', name: 'Your Model', steps: 30 },
  // Add your installed models
]
```

### Runtime API Configuration

For development, edit `public/config.js`:

```javascript
window.DGX_CONFIG = {
  COMFYUI_URL: 'http://localhost:11005',     // Local with SSH tunnel
  OLLAMA_URL: 'http://localhost:11434',
  // ...
};
```

For production on server, edit `config.dgx.js`:

```javascript
window.DGX_CONFIG = {
  COMFYUI_URL: '/comfyui',                   // Via nginx proxy
  OLLAMA_URL: '/ollama',
  // ...
};
```

### Backend API Configuration

If you need to customize backend behavior, edit `backend/main.py`:

```python
# Managed services (lines ~37-45)
MANAGED_SERVICES = {
    "comfyui": {"container": "your-comfyui-container", "description": "Description"},
    "your-service": {"container": "your-container", "description": "Your service"},
}

# Claude Code path (line ~78)
CLAUDE_PATH = os.path.expanduser("~/.local/bin/claude")  # Your path

# Trinity directory (line ~488, if using Trinity)
trinity_dir = os.path.expanduser("~/your-trinity-path")
```

### Docker Compose Ports

Change exposed ports in `docker-compose.yml`:

```yaml
services:
  dgx-web-ui:
    ports:
      - "8080:80"        # Change 3080 to your preferred port

  dgx-api:
    ports:
      - "8081:8080"      # Change 3081 to your preferred port
```

## Configuration Checklist

Use this checklist before deploying:

### Required
- [ ] `.env` created with your server credentials
- [ ] `deploy.sh` copied from example and made executable
- [ ] Network IPs updated in `mobileConstants.js`
- [ ] Network IPs updated in `Dashboard.vue`
- [ ] Hardware specs updated in both files
- [ ] Model lists updated based on your installations

### Verify Services
- [ ] Ollama running and CORS configured
- [ ] ComfyUI running and accessible
- [ ] Other services (Ultravox, Chatterbox) running if used
- [ ] Firewall allows connections on ports 3080, 3081

### Optional
- [ ] Image model list customized
- [ ] Video model list customized
- [ ] Service links updated
- [ ] Backend service list updated
- [ ] Docker Compose ports changed (if needed)

## Quick Configuration Commands

Search and replace all instances (use with caution):

```bash
# Find all hardcoded IPs to update
grep -r "192.168.1" src/
grep -r "100.122" src/

# Find model references
grep -r "gpt-oss" src/
grep -r "ltxv-" src/
```

## Testing Configuration

After configuring:

1. **Test locally (development)**
   ```bash
   npm install
   npm run dev
   # Open http://localhost:3000
   ```

2. **Test deployment**
   ```bash
   ./deploy.sh sync      # Test file sync
   ./deploy.sh build     # Test Docker build
   ./deploy.sh deploy    # Full deployment
   ```

3. **Verify web UI**
   - Navigate to `http://your-server-ip:3080`
   - Check Dashboard shows your hardware specs
   - Check Status shows your network IPs
   - Try generating an image/video
   - Try chat with Ollama

## Troubleshooting

### Wrong IP Addresses Displayed

Files to check:
1. `src/constants/mobileConstants.js` - lines 12-15
2. `src/components/Dashboard.vue` - lines 8-19

### Wrong Hardware Specs

Files to check:
1. `src/constants/mobileConstants.js` - lines 17-22
2. `src/components/Dashboard.vue` - lines 74-94

### Models Not Showing

1. Update `availableModels` in `mobileConstants.js`
2. Update `models` in `Dashboard.vue`
3. Ensure model files exist in ComfyUI directories

### Services Not Working

1. Verify service is running: `docker ps` or `systemctl status service`
2. Check ports are correct in `config.js` or `config.dgx.js`
3. Verify nginx proxy in `nginx.conf` (production)
4. Check firewall rules: `sudo ufw status`

## Environment-Specific Configs

### Home Lab Setup
- Use local network IPs (192.168.x.x)
- No VPN needed
- Direct port access

### Remote Server with VPN
- Configure both local and VPN IPs
- Use VPN for remote access
- Consider firewall rules

### Cloud Instance
- Public IP for local access
- Security group/firewall configuration critical
- Consider HTTPS reverse proxy

## Next Steps

After configuration:
1. Review [SECURITY.md](SECURITY.md) for security best practices
2. See [SETUP.md](SETUP.md) for advanced customization
3. Deploy with `./deploy.sh deploy`
4. Test all features

## Getting Help

If you need help with configuration:
1. Check [SETUP.md](SETUP.md) for detailed guides
2. Review [Troubleshooting](#troubleshooting) section
3. Open an issue on GitHub with:
   - Your configuration (redact credentials)
   - Error messages
   - Service status output
