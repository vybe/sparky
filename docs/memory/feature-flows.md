# Feature Flows Index

> Directory of all documented feature flows.

---

## How to Use

1. Before modifying a feature, read its flow document
2. After modifying a feature, update or create its flow document
3. Use `/feature-flow-analysis <name>` to create new flows

---

## Documented Flows

| Feature | Status | File | Components |
|---------|--------|------|------------|
| Chat | Documented | [`chat.md`](feature-flows/chat.md) | Chat.vue, useChat.js |
| Image Generation | Documented | [`image-generation.md`](feature-flows/image-generation.md) | ImageGenerator.vue, useImageGeneration.js |
| Video Generation | Documented | [`video-generation.md`](feature-flows/video-generation.md) | VideoGenerator.vue, useVideoGeneration.js |
| Voice Chat | Documented | [`voice-chat.md`](feature-flows/voice-chat.md) | VoiceChat.vue |
| Agent Chat | Documented | [`agent-chat.md`](feature-flows/agent-chat.md) | AgentChat.vue, useAgent.js |
| Rick Agent | Documented | [`rick-agent.md`](feature-flows/rick-agent.md) | RickChat.vue, useRick.js |
| Research Agent | Documented | [`research-agent.md`](feature-flows/research-agent.md) | GooseChat.vue, backend/main.py |
| Container Management | Documented | [`container-management.md`](feature-flows/container-management.md) | Management.vue, useManagement.js, backend/main.py |
| Telemetry | Documented | [`telemetry.md`](feature-flows/telemetry.md) | ActivityMonitor.vue, Telemetry.vue, useTelemetry.js |
| Mobile PWA | Documented | [`mobile-pwa.md`](feature-flows/mobile-pwa.md) | Mobile.vue, mobileConstants.js, manifest.json, sw.js |

---

## Flow Document Template

When creating a new flow, use this structure:

```markdown
# Feature: {Name}

## Overview
One-line description.

## Entry Points
- **UI**: Component and action
- **API**: Endpoint or service

## Frontend Layer
- Components
- Composables
- API calls

## Backend Layer (if applicable)
- Endpoints
- External services

## Data Flow
Step-by-step data transformation

## Error Handling
Error cases and UI feedback

## Related Flows
Upstream and downstream connections
```

---

## Documentation Complete

All 10 features documented (updated 2026-01-26).

### Quick Reference

| Feature | External Service | Port |
|---------|-----------------|------|
| Chat | Ollama | 11434 |
| Image Generation | ComfyUI | 11005 |
| Video Generation | ComfyUI | 11005 |
| Voice Chat | Ultravox + Chatterbox | 11100, 11004 |
| Agent Chat | Claude Code CLI | N/A |
| Rick Agent | Claude Code CLI | N/A |
| Research Agent | Goose CLI | N/A |
| Container Management | FastAPI + Docker | /api |
| Telemetry | Telemetry API + Ollama | 11006, 11434 |
| Mobile PWA | All services (aggregates) | Multiple |
