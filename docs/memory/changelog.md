# Changelog

> Timestamped history of changes to DGX Spark Web UI.

---

## Recent Changes

### 2026-01-11 14:45:00
📚 **Created all feature flow documentation**
- Documented 8 feature flows (chat, image-gen, video-gen, voice-chat, agent-chat, research-agent, container-management, telemetry)
- Each flow includes: entry points, frontend/backend layers, data flow, error handling
- Updated feature-flows.md index with quick reference table
- Key files: `docs/memory/feature-flows/*.md`

### 2025-01-11 10:30:00
📝 **Set up development methodology**
- Added `.claude/commands/` with 5 slash commands
- Added `.claude/agents/` with 3 sub-agents
- Created `docs/memory/` structure for persistent state
- Key files: `.claude/`, `docs/memory/`, `CLAUDE.md`

### 2025-01-10 16:28:00
✨ **Added Goose Research Agent integration**
- New GooseChat.vue component
- Backend endpoints for Goose CLI
- Chat mode and research mode support
- Research file viewing
- Key files: `src/components/GooseChat.vue`, `backend/main.py`

### 2025-01-10 15:54:00
🔄 **Updated App.vue tabs**
- Added Goose tab (Research icon 🪿)
- Renamed tabs for clarity
- Key files: `src/App.vue`

### 2025-01-06 16:48:00
✨ **Added Agent Chat with Claude Code**
- Full Claude Code integration
- Session persistence and resume
- Tool restriction options
- Streaming response display
- Key files: `src/components/AgentChat.vue`, `backend/main.py`

### 2025-01-06 15:26:00
🔄 **Improved Chat component**
- Better message formatting
- Fixed streaming display issues
- Key files: `src/components/Chat.vue`, `src/style.css`

### 2025-01-05 12:11:00
📝 **Comprehensive documentation**
- Added README.md with setup guide
- Created CONFIGURATION.md
- Created SETUP.md for advanced config
- Created SECURITY.md
- Created CONTRIBUTING.md

### 2025-01-03 14:32:00
🔄 **Refactored composables**
- Improved error handling
- Better state management
- Key files: `src/composables/*.js`

### 2025-01-02 22:36:00
✅ **Deployment testing complete**
- Verified container build and run
- Tested all features on DGX
- Created DEPLOYMENT_TEST_REPORT.md

### 2025-01-02 08:19:00
✨ **Added Activity Monitor**
- Real-time header bar with GPU/memory/disk
- Compact design for always-visible status
- Key files: `src/components/ActivityMonitor.vue`

### 2025-01-02 08:16:00
🐳 **Docker deployment setup**
- Multi-stage Dockerfile
- Docker Compose configuration
- nginx config with proxies
- deploy.sh script
- Key files: `Dockerfile`, `docker-compose.yml`, `nginx.conf`, `deploy.sh`

### 2025-01-01 20:19:00
✨ **Mobile PWA implementation**
- Full mobile interface
- PWA manifest and icons
- Service worker for offline
- iOS home screen support
- Key files: `src/components/Mobile.vue`, `public/manifest.json`, `public/sw.js`

### 2025-01-01 15:32:00
🔧 **Configuration system**
- Runtime config via window.DGX_CONFIG
- Development vs production config
- Key files: `public/config.js`, `config.dgx.js`

### 2025-01-01 12:46:00
✨ **Core features complete**
- Image generation (SDXL/Flux)
- Video generation (LTX Video)
- Voice chat (Ultravox + Chatterbox)
- Telemetry display
- Key files: `src/components/*.vue`

### 2024-12-31 22:23:00
🎉 **Initial project setup**
- Vue 3 + Vite scaffold
- Tailwind CSS configuration
- Basic component structure
- Key files: `package.json`, `vite.config.js`, `tailwind.config.js`

---

## Archive

Older entries moved to `docs/memory/changelog-archive.md` when this file exceeds 500 lines.
