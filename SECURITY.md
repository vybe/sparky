# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please email the maintainers directly instead of opening a public issue.

**Please do NOT:**
- Open a public GitHub issue
- Post in discussions or forums
- Disclose publicly before a fix is available

**Please DO:**
- Email details to the maintainer
- Allow reasonable time for a fix
- Coordinate disclosure timing

## Security Best Practices

### For Deployment

1. **Never commit sensitive data**
   - Use `.env` files (excluded from git)
   - Use environment variables
   - Use SSH keys instead of passwords

2. **Secure your server**
   - Use firewall (UFW, iptables)
   - Restrict port access
   - Keep system updated
   - Use HTTPS in production

3. **Docker Security**
   - Run containers as non-root when possible
   - Limit Docker socket access
   - Use read-only mounts where possible
   - Keep images updated

4. **Access Control**
   - Use VPN for remote access (recommended)
   - Implement reverse proxy with authentication
   - Use strong passwords
   - Regular security audits

### Configuration Security

#### .env File

Never commit `.env` files. Use `.env.example` as a template:

```bash
# GOOD - Use .env.example with placeholder values
DGX_HOST=your-server-ip
DGX_PASS=your-password

# BAD - Don't commit real values
DGX_HOST=192.168.1.127
DGX_PASS=actualpassword123
```

#### SSH Keys (Recommended)

Instead of passwords in `.env`:

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy to server
ssh-copy-id user@server

# Use deploy.sh without DGX_PASS
DGX_HOST=server-ip
DGX_USER=username
# DGX_PASS not needed with SSH keys
```

#### API Security

The backend API has these security considerations:

1. **Docker Socket Access**
   - Required for container management
   - Limits: User must be in docker group
   - Risk: Can start/stop containers

2. **Command Execution**
   - Limited to whitelisted commands
   - Timeout enforced
   - No shell injection possible

3. **Claude Code Integration**
   - Runs with `--dangerously-skip-permissions`
   - Has access to host filesystem
   - Suitable for trusted environments only

### Network Security

1. **Firewall Rules**

```bash
# Allow only specific ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 3080/tcp  # Web UI
sudo ufw allow 3081/tcp  # API
sudo ufw enable
```

2. **Reverse Proxy (Production)**

Use nginx or Caddy with HTTPS:

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. **VPN Access**

Recommended for remote access:
- Tailscale (easy setup)
- WireGuard (performance)
- OpenVPN (traditional)

## Known Security Considerations

### Docker Socket Mounting

The backend container mounts `/var/run/docker.sock` for container management.

**Risk:** Container can control Docker daemon
**Mitigation:**
- Runs as non-root user
- Requires docker group membership
- Limited to trusted environments

### Claude Code Integration

Claude Code runs with autonomous permissions.

**Risk:** Can execute arbitrary commands
**Mitigation:**
- Runs in backend container only
- No direct web exposure
- Suitable for private/trusted deployments

### CORS Configuration

Ollama requires `origins='*'` for web access.

**Risk:** Any website can access Ollama
**Mitigation:**
- Restrict via firewall
- Use VPN for remote access
- Don't expose Ollama port publicly

## Security Checklist

Before deploying to production:

- [ ] `.env` file not in git
- [ ] Strong passwords or SSH keys
- [ ] Firewall configured
- [ ] HTTPS enabled (reverse proxy)
- [ ] VPN for remote access
- [ ] Docker images up to date
- [ ] System packages updated
- [ ] Regular backups configured
- [ ] Logs monitored
- [ ] Access limited to trusted users

## Production Deployment Example

Secure setup with Caddy + Tailscale:

```bash
# 1. Install Tailscale VPN
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# 2. Install Caddy
sudo apt install caddy

# 3. Configure Caddy
sudo nano /etc/caddy/Caddyfile
```

Caddyfile:
```
your-tailscale-name.ts.net {
    reverse_proxy localhost:3080
}
```

```bash
# 4. Start services
sudo systemctl restart caddy
./deploy.sh deploy
```

Access only via Tailscale VPN: `https://your-tailscale-name.ts.net`

## Update Policy

- Security patches: Released ASAP
- Dependencies: Updated monthly
- System: Keep OS and Docker updated

## Dependencies

Monitor for security updates:

```bash
# Check outdated npm packages
npm audit

# Update packages
npm update

# Python dependencies
pip list --outdated
```

## Incident Response

If compromised:

1. **Immediate Actions**
   - Disconnect from network
   - Stop affected containers
   - Change all passwords
   - Revoke SSH keys

2. **Investigation**
   - Check logs: `docker logs <container>`
   - Review system logs: `/var/log/`
   - Check for unauthorized changes

3. **Recovery**
   - Restore from backup
   - Update all credentials
   - Apply security patches
   - Review access controls

4. **Prevention**
   - Document what happened
   - Update security measures
   - Improve monitoring

## Additional Resources

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Mozilla Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)

## Contact

For security issues, contact the repository maintainer directly.
