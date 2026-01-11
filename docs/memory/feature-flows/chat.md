# Feature: Chat

## Overview
LLM chat interface using Ollama models running on DGX Spark.

## User Story
As a user, I want to chat with local LLM models so that I can get AI responses without external API dependencies.

## Entry Points
- **UI**: `src/components/Chat.vue:47` - Main chat tab with model selector, message list, and input
- **API**: Ollama API at `http://localhost:11434/api/chat`

## Frontend Layer

### Components
- `src/components/Chat.vue:42-44` - `handleSend()` triggers message sending
- `src/components/Chat.vue:53-68` - Model selector dropdown with load status
- `src/components/Chat.vue:142-183` - Message list rendering with loading states
- `src/components/Chat.vue:186-208` - Textarea input with Enter-to-send

### Composables
- `src/composables/useChat.js:6-213` - Complete chat state management

**Key State:**
```javascript
chatModels       // ref([]) - Available models from Ollama
selectedChatModel // ref('') - Currently selected model name
chatMessages     // ref([]) - Array of {role, content, loading}
loadedModels     // ref([]) - Models currently in GPU memory
```

**Key Methods:**
- `loadChatModels()` - Fetches model list from `/api/tags`
- `checkLoadedModels()` - Polls `/api/ps` for GPU-loaded models
- `loadSelectedModel()` - Warms up model with minimal prompt
- `sendChat()` - Sends message, streams response

### API Calls

**List Models:**
```javascript
// src/composables/useChat.js:23-30
const res = await fetch(`${OLLAMA_URL}/api/tags`, {
  signal: AbortSignal.timeout(5000)
})
// Response: { models: [{ name, details: { parameter_size } }] }
```

**Check Loaded Models:**
```javascript
// src/composables/useChat.js:48-50
const res = await fetch(`${OLLAMA_URL}/api/ps`)
// Response: { models: [{ name }] }
```

**Load Model (warm-up):**
```javascript
// src/composables/useChat.js:67-75
await fetch(`${OLLAMA_URL}/api/generate`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: selectedChatModel.value,
    prompt: 'hi',
    stream: true
  })
})
```

**Send Chat Message:**
```javascript
// src/composables/useChat.js:126-137
await fetch(`${OLLAMA_URL}/api/chat`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: selectedChatModel.value,
    messages: chatMessages.value.filter(m => !m.loading).map(m => ({
      role: m.role,
      content: m.content
    })),
    stream: true
  })
})
```

## External Services

### Ollama API (port 11434)

**Endpoints Used:**
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tags` | GET | List available models |
| `/api/ps` | GET | List GPU-loaded models |
| `/api/generate` | POST | Warm up model with prompt |
| `/api/chat` | POST | Send chat message, stream response |

**Response Streaming:**
```javascript
// NDJSON stream format
{"message":{"role":"assistant","content":"Hello"},"done":false}
{"message":{"role":"assistant","content":" there"},"done":false}
{"done":true}
```

## Data Flow

1. **On Mount**: `loadChatModels()` fetches model list from Ollama
2. **Every 10s**: `checkLoadedModels()` polls for GPU-loaded models
3. **User selects model**: If not loaded, shows "Load Model" button
4. **User clicks Load**: `loadSelectedModel()` warms up model (30-90s)
5. **User types message**: Input stored in `chatInput` ref
6. **User presses Enter**: `handleSend()` called
7. **Message added**: User message + loading placeholder appended
8. **Streaming**: Response chunks parsed and appended to placeholder
9. **Complete**: Loading state removed, message content finalized

```
User Input --> sendChat() --> POST /api/chat --> Stream Response --> Update Message
                                                       |
                                                  Parse NDJSON
                                                       |
                                                  Append Content
```

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| Ollama offline | Fetch timeout/error | `chatModelsError` message | Retry via Refresh button |
| Model not loaded | `!isModelLoaded()` | Yellow warning banner | Load Model button |
| Network error | Catch in sendChat | Error in message content | User can retry |
| No models found | Empty response | "No models available" | Check Ollama via Manage tab |

## Configuration

- **OLLAMA_URL**: `src/config.js:7` defaults to `http://localhost:11434`
- **Runtime override**: `public/config.js` sets `window.DGX_CONFIG.OLLAMA_URL`

## Related Flows

- **Upstream**: Telemetry flow monitors Ollama loaded models
- **Downstream**: Management flow can restart Ollama service
