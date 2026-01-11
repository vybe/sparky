# Feature Flow Analysis

Create or update a feature flow document for end-to-end understanding.

## Arguments

- `$ARGUMENTS` - Feature name (e.g., "chat", "image-generation", "voice-chat")

## Instructions

1. If no feature name provided, ask:
   ```
   Which feature would you like to analyze?

   Available features:
   - chat (Ollama LLM streaming)
   - image-generation (ComfyUI SDXL/Flux)
   - video-generation (ComfyUI LTX Video)
   - voice-chat (Ultravox + Chatterbox)
   - telemetry (System monitoring)
   - container-management (Docker control)
   ```

2. Trace the feature execution path:

   **Frontend (Component → Composable → API)**
   - Find Vue component entry point
   - Trace to composables (state/logic)
   - Document API/WebSocket call made

   **Backend (FastAPI Endpoint → Logic → External Service)**
   - Find API endpoint handler in `backend/main.py`
   - Trace business logic
   - Document external service calls (ComfyUI, Ollama, etc.)

   **External Services (if applicable)**
   - ComfyUI API calls
   - Ollama API calls
   - Docker socket operations

3. Document side effects:
   - State changes
   - WebSocket messages
   - Polling loops

4. Document error handling:
   - What can fail?
   - Error states shown to user
   - Recovery mechanisms

5. Save flow document:
   - Path: `docs/memory/feature-flows/{feature-name}.md`
   - Use template structure below

6. Update index:
   - Add entry to `docs/memory/feature-flows.md`
   - Mark as documented with components list

## Output Format

```markdown
# Feature: {Feature Name}

## Overview
Brief description.

## User Story
As a [user], I want to [action] so that [benefit].

## Entry Points
- **UI**: `src/components/Component.vue:line` - Action trigger
- **API**: `METHOD /api/endpoint` or external service URL

## Frontend Layer
### Components
- `Component.vue:line` - handler()

### Composables
- `composables/useFeature.js` - state and methods

### API Calls
```javascript
await fetch(`${baseUrl}/endpoint`, { ... })
```

## Backend Layer
### Endpoints (if applicable)
- `backend/main.py:line` - endpoint()

### External Services
- ComfyUI: `POST /prompt`
- Ollama: `POST /api/chat`

## Data Flow
1. User action → Component
2. Component → Composable
3. Composable → API call
4. API response → State update
5. State → UI refresh

## Error Handling
| Error Case | UI State | Recovery |
|------------|----------|----------|
| Network error | Error toast | Retry button |

## Related Flows
- Upstream: flow
- Downstream: flow
```

## Principle

Information density over completeness. Think debugging notes, not comprehensive docs.
