# Prepare Repository for GitHub - Checklist

Follow these steps to safely share the DGX Web UI repository on GitHub.

## Step 1: Backup Current Repository

```bash
# Create a backup of your current working directory
cd /Users/eugene/Dropbox/Agents/dgx
cp -r web-ui web-ui-backup-$(date +%Y%m%d)
```

## Step 2: Replace Files with Clean Versions

```bash
cd web-ui

# 1. Replace deploy script
mv deploy.sh deploy.sh.private
mv deploy.sh.example deploy.sh

# 2. Replace .gitignore
mv .gitignore .gitignore.old
mv .gitignore.clean .gitignore

# 3. Replace mobile constants
mv src/constants/mobileConstants.js src/constants/mobileConstants.js.private
mv src/constants/mobileConstants.clean.js src/constants/mobileConstants.js

# 4. Replace README
mv README.md README.md.private
mv README.clean.md README.md

# 5. Create .env from example
cp .env.example .env
# Edit .env with generic values for testing
```

## Step 3: Remove Sensitive Files

```bash
# Remove files with environment-specific data
rm -f DEPLOYMENT_TEST_REPORT.md
rm -f REFACTORING_SUMMARY.md
rm -f config.dgx.js  # Keep only as example, not in git

# Remove CLAUDE.md with specific environment details
mv CLAUDE.md CLAUDE.md.private

# Remove or sanitize any test output files
rm -rf test_outputs/
```

## Step 4: Sanitize Vue Components

### Dashboard.vue

Edit `src/components/Dashboard.vue` to use generic IPs:

```javascript
// Replace lines 8-19 with:
const network = {
  local: {
    name: 'Local Network',
    ip: import.meta.env.VITE_LOCAL_IP || '192.168.1.xxx',
    description: 'Direct connection when on same network'
  },
  tailscale: {
    name: 'VPN',
    ip: import.meta.env.VITE_VPN_IP || '100.xxx.xxx.xxx',
    description: 'Remote access via VPN'
  }
}
```

### Mobile.vue

Edit `src/components/Mobile.vue` similarly - use environment variables or generic placeholders for network IPs.

## Step 5: Initialize Git (if not already)

```bash
# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: DGX Web UI"
```

## Step 6: Review Git Status

```bash
# Check what will be committed
git status

# Make sure these are NOT showing:
# - .env
# - deploy.sh (should be deploy.sh.example in git)
# - Any files with "private" in the name
# - DEPLOYMENT_TEST_REPORT.md
# - Files in .gitignore
```

## Step 7: Verify .gitignore

```bash
# Test that sensitive files are ignored
git check-ignore -v .env
git check-ignore -v deploy.sh
git check-ignore -v "*.private"

# Should show these files are ignored
```

## Step 8: Search for Sensitive Data

```bash
# Search for hardcoded IPs
grep -r "192.168.1.127" src/
grep -r "100.122.64.45" src/

# Search for passwords
grep -r "kdr73hhe" .

# Search for usernames
grep -r "eugene@" .

# If any matches found in files that will be committed, sanitize them
```

## Step 9: Create GitHub Repository

1. Go to GitHub: https://github.com/new
2. Repository name: `dgx-web-ui`
3. Description: "Vue 3 web interface for NVIDIA DGX Spark with ComfyUI, Ollama, and system management"
4. Choose Public or Private
5. Do NOT initialize with README (we have one)
6. Click "Create repository"

## Step 10: Push to GitHub

```bash
# Add remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/dgx-web-ui.git

# Push main branch
git branch -M main
git push -u origin main
```

## Step 11: Configure GitHub Repository

1. Go to Settings → General
2. Set default branch to `main`
3. Go to Settings → Security
4. Enable "Dependabot alerts"
5. Enable "Dependabot security updates"

## Step 12: Add Repository Badges (Optional)

Add to top of README.md:

```markdown
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Vue 3](https://img.shields.io/badge/Vue-3-green.svg)
![Docker](https://img.shields.io/badge/Docker-blue.svg)
```

## Step 13: Create Release (Optional)

```bash
# Tag version
git tag -a v1.0.0 -m "Initial release"
git push origin v1.0.0
```

Then create release on GitHub:
1. Go to Releases → Create a new release
2. Choose tag v1.0.0
3. Release title: "v1.0.0 - Initial Release"
4. Description: Features, requirements, setup instructions

## Step 14: Final Validation

Before making public, verify:

- [ ] No credentials in any file
- [ ] No hardcoded IPs specific to your network
- [ ] .env.example exists with placeholders
- [ ] README.md has generic setup instructions
- [ ] SETUP.md explains customization
- [ ] SECURITY.md explains security considerations
- [ ] CONTRIBUTING.md has contribution guidelines
- [ ] .gitignore excludes sensitive files
- [ ] deploy.sh requires .env configuration
- [ ] All documentation uses example values

## Testing the Clean Repository

```bash
# Clone your GitHub repo in a new directory
cd /tmp
git clone https://github.com/YOUR_USERNAME/dgx-web-ui
cd dgx-web-ui

# Verify files
ls -la

# Check for sensitive data
grep -r "192.168.1.127" .
grep -r "kdr73hhe" .

# Should find nothing except in README examples
```

## Maintenance After Publishing

### Keep Private Configuration Separate

Your private configuration stays in the backup:
```bash
/Users/eugene/Dropbox/Agents/dgx/web-ui-backup-YYYYMMDD/
├── .env                              # Your real credentials
├── deploy.sh.private                 # Script with your IPs
├── CLAUDE.md.private                 # Your environment docs
├── src/constants/mobileConstants.js.private  # Your real IPs
└── README.md.private                 # Your private notes
```

### Syncing Updates

When you make improvements to share:

```bash
# Work in your main directory (with private config)
cd /Users/eugene/Dropbox/Agents/dgx/web-ui

# Make changes, test them
# ...

# When ready to share:
# 1. Copy non-sensitive files to a clean branch
git checkout -b share-updates

# 2. Sanitize and commit
git add src/components/NewFeature.vue
git commit -m "Add: New feature"

# 3. Push to GitHub
git push origin share-updates

# 4. Create PR on GitHub
```

## What to Share vs Keep Private

### SHARE (on GitHub):
- Source code (sanitized)
- Docker configuration
- Documentation (generic)
- Examples and templates
- Setup guides
- Security policies

### KEEP PRIVATE:
- .env file
- deploy.sh with real credentials
- CLAUDE.md with your environment
- Any files with "private" in name
- Deployment reports
- Test outputs with real data
- Network topology
- Server access details

## Repository Description

Use this for GitHub repository description:

```
Vue 3 web interface for NVIDIA DGX Spark featuring:
• Image generation (SDXL, Flux, Pony) via ComfyUI
• Video generation (LTX Video) via ComfyUI
• LLM chat with Ollama streaming
• Voice chat (Ultravox + Chatterbox TTS)
• Real-time telemetry and GPU monitoring
• Docker container management
• Progressive Web App (PWA) support

Includes FastAPI backend for system management and Claude Code integration.
```

## Topics/Tags for GitHub

Add these topics to your repository:

```
vue3, vite, tailwindcss, docker, nvidia-dgx, comfyui, ollama,
fastapi, pwa, ai, llm, image-generation, video-generation,
gpu-monitoring, container-management
```

## License

The clean version includes MIT License. If you want a different license, add a LICENSE file before committing.

## Questions Before Publishing?

Review:
1. Is all sensitive data removed?
2. Are setup instructions clear for others?
3. Does it work with example configuration?
4. Are security warnings prominent?
5. Is CONTRIBUTING.md welcoming?

If yes to all, you're ready to publish!

## After Publishing

1. Share on social media/forums (optional)
2. Monitor issues and PRs
3. Keep dependencies updated
4. Respond to security reports promptly
5. Maintain CHANGELOG for updates

Good luck! 🚀
