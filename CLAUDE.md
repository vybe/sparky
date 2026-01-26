# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**DGX Spark Web UI** — Vue 3 web interface for DGX Spark services (LLM chat, image/video generation, voice chat, container management).

**Local URLs**:
- Web UI: http://localhost:3000 (dev) / http://${DGX_HOST}:3080 (deployed)
- Backend API: http://${DGX_HOST}:3081/docs

---

## Rules of Engagement

### 1. Requirements-Driven Development
- Update `docs/memory/requirements.md` **BEFORE** implementing new features
- All features must trace back to documented requirements
- Never add features without requirements update first

### 2. Minimal Necessary Changes
- Only change what's required for the task
- No unsolicited refactoring or reorganization
- No cosmetic formatting changes to unrelated code
- No creating documentation files unless explicitly requested

### 3. Follow the Roadmap
- Check `docs/memory/roadmap.md` for current priorities
- Work topmost incomplete items in the queue
- Mark items complete with timestamp: `[x] 2025-01-08 HH:MM:SS`

### 4. Mandatory Documentation Updates
After **EVERY** change, update:
- `docs/memory/changelog.md` - Add timestamped entry with emoji prefix
- `docs/memory/architecture.md` - If changing APIs, services, or integrations
- `docs/memory/feature-flows/` - If modifying feature behavior
- `docs/memory/requirements.md` - If changing feature scope

### 5. Security First
- Never expose credentials, API keys, or tokens in code or logs
- Never commit the DGX password or internal IPs
- Use environment variables for all secrets
- Run `/security-check` before every commit
- Review diffs before committing for accidental sensitive data

---

## Memory Files

| File | Purpose |
|------|---------|
| `docs/memory/requirements.md` | **SINGLE SOURCE OF TRUTH** - All features |
| `docs/memory/architecture.md` | Current system design |
| `docs/memory/roadmap.md` | Prioritized task queue |
| `docs/memory/changelog.md` | Timestamped history |
| `docs/memory/feature-flows.md` | Index of vertical slice docs |

---

## Development Commands

```bash
# Local development (requires SSH tunnel to DGX)
npm install
npm run dev
# Open http://localhost:3000

# Build for production
npm run build

# Deploy to DGX
./deploy.sh deploy    # Full: sync + build + start
./deploy.sh sync      # Sync files only
./deploy.sh restart   # Restart containers
./deploy.sh logs      # View logs
./deploy.sh status    # Check status
```

---

## Project Structure

```
web-ui/
├── src/
│   ├── App.vue                 # Root with tab navigation
│   ├── components/             # Vue components
│   │   ├── Chat.vue            # Ollama chat
│   │   ├── ImageGenerator.vue  # ComfyUI SDXL/Flux
│   │   ├── VideoGenerator.vue  # ComfyUI LTX Video
│   │   ├── VoiceChat.vue       # Ultravox + Chatterbox
│   │   ├── AgentChat.vue       # Claude Code
│   │   ├── GooseChat.vue       # Goose research
│   │   ├── Management.vue      # Container management
│   │   └── Mobile.vue          # PWA mobile interface
│   ├── composables/            # Vue composables (state + logic)
│   └── config.js               # Runtime config loader
├── backend/
│   └── main.py                 # FastAPI backend
├── public/
│   ├── config.js               # Dev runtime config
│   ├── manifest.json           # PWA manifest
│   └── sw.js                   # Service worker
├── docs/
│   └── memory/                 # Persistent project state
├── .claude/
│   ├── commands/               # Slash commands
│   └── agents/                 # Sub-agents
├── docker-compose.yml          # Container orchestration
├── nginx.conf                  # Production proxy config
└── deploy.sh                   # Deployment script
```

---

## Key Files

| Category | File | Description |
|----------|------|-------------|
| Frontend | `src/App.vue` | Root component with tabs |
| Frontend | `src/components/*.vue` | Feature components |
| Frontend | `src/composables/*.js` | State and API logic |
| Backend | `backend/main.py` | FastAPI application |
| Config | `public/config.js` | Dev service URLs |
| Config | `config.dgx.js` | Production service URLs |
| Deploy | `docker-compose.yml` | Container setup |
| Deploy | `nginx.conf` | Proxy configuration |

---

## External Services

| Service | Port | Purpose |
|---------|------|---------|
| Ollama | 11434 | LLM chat |
| ComfyUI | 8188 | Image/video generation |
| Ultravox | 8100 | Speech LLM |
| Chatterbox | 8004 | Text-to-speech |
| Telemetry | 8006 | System stats |

---

## Important Notes for Claude Code

1. **Load context first**: Always run `/read-docs` at session start

2. **Test before committing**: Verify changes work in browser

3. **Document changes**: Use `/update-docs` after making changes

4. **Security check**: Run `/security-check` before every commit

5. **Feature flows**: Read relevant feature flow before modifying a feature

---

## See Also

- **Development Workflow**: `docs/DEVELOPMENT_WORKFLOW.md`
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **Full Requirements**: `docs/memory/requirements.md`
- **Current Roadmap**: `docs/memory/roadmap.md`
- **Recent Changes**: `docs/memory/changelog.md`
