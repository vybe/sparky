# Roadmap

> Prioritized task queue for DGX Spark Web UI.

---

## Current Phase: Stabilization & Documentation

Focus on documenting existing features and improving reliability.

---

## Active Tasks

| Task | Status | Notes |
|------|--------|-------|
| Document feature flows | ✅ Complete | All 8 feature flows documented |
| Set up development methodology | ✅ Complete | Commands, agents, memory files |

---

## Backlog

### High Priority

| Task | Status | Description |
|------|--------|-------------|
| Add error toasts | ⏳ Pending | Global toast notifications for errors |
| Improve loading states | ⏳ Pending | Better skeleton loaders |
| Fix mobile image download | ⏳ Pending | iOS Safari blob URL handling |

### Medium Priority

| Task | Status | Description |
|------|--------|-------------|
| WebSocket telemetry | ⏳ Pending | Replace polling with WebSocket |
| Keyboard shortcuts | ⏳ Pending | Cmd+Enter to send, Escape to cancel |
| Dark/Light theme toggle | ⏳ Pending | Currently dark-only |

### Low Priority

| Task | Status | Description |
|------|--------|-------------|
| Basic auth option | ⏳ Pending | API key header for production |
| Usage analytics | ⏳ Pending | Track generations, chat sessions |
| Export chat history | ⏳ Pending | Download as markdown/JSON |

---

## Completed

| Task | Completed | Notes |
|------|-----------|-------|
| Document feature flows | 2026-01-11 | All 8 flows in docs/memory/feature-flows/ |
| Set up development methodology | 2025-01-11 | Commands, agents, memory files |
| Initial Vue 3 setup | 2024-12-31 | Vite + Tailwind |
| Chat integration | 2025-01-01 | Ollama streaming |
| Image generation | 2025-01-01 | ComfyUI workflows |
| Video generation | 2025-01-01 | LTX Video 2B/13B |
| Voice chat | 2025-01-01 | Ultravox + Chatterbox |
| Container management | 2025-01-02 | Docker API |
| Mobile PWA | 2025-01-02 | Full feature parity |
| Agent chat | 2025-01-06 | Claude Code |
| Research agent | 2025-01-10 | Goose integration |

---

## Notes

- Feature flows should be created before adding new features
- All API changes require architecture.md update
- Test with both local dev and deployed container
