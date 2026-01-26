# Feature: Agent Chat

## Overview
Chat interface to Claude Code CLI running on DGX for autonomous system operations. Uses SSE streaming for real-time output and supports session resume on connection failures.

## User Story
As a user, I want to send commands to Claude Code so that it can manage the DGX system autonomously, with real-time feedback and the ability to recover from timeouts.

## Entry Points
- **UI**: `src/components/AgentChat.vue` - Agent chat interface (desktop)
- **UI**: `src/components/Mobile.vue` - Mobile agent tab
- **API**: FastAPI backend at `/api/claude/*`

## Frontend Layer

### Components
- `src/components/AgentChat.vue` - Desktop agent chat
- `src/components/Mobile.vue` - Mobile PWA agent tab
- `src/composables/useAgent.js` - Shared composable for mobile

**Key State:**
```javascript
messages        // ref([]) - Chat messages with role, content, loading, streaming, tools
inputMessage    // ref('') - Current input
isLoading       // ref(false) - Request in progress
sessionId       // ref(null) - Claude session ID for context
claudeStatus    // ref(null) - { available, version, path }
totalCost       // ref(0) - Cumulative session cost in USD
savedSessions   // ref([]) - Persisted sessions
selectedPreset  // ref(toolPresets[0]) - Tool access level

// Streaming state
currentStreamController  // ref(null) - AbortController for cancellation
streamingText           // ref('') - Accumulated streaming text
currentTool             // ref(null) - Tool currently being used
lastFailedSessionId     // ref(null) - Session to resume after error

// File upload state
pendingFiles    // ref([]) - Files queued for upload
isDragging      // ref(false) - Drag & drop active
fileInputRef    // ref(null) - Hidden file input element
isUploading     // ref(false) - Upload in progress
```

### Composables
- `src/composables/useAgent.js` - Used by Mobile.vue, contains streaming logic

**Tool Presets:**
```javascript
const toolPresets = [
  { name: 'Full Access', tools: null },
  { name: 'Read Only', tools: ['Read', 'Glob', 'Grep', 'Bash(ls:*)', 'Bash(cat:*)'] },
  { name: 'Safe Bash', tools: ['Bash', 'Read', 'Write', 'Edit'] },
  { name: 'Research', tools: ['Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch'] },
]
```

### API Calls

**Check Status:**
```javascript
const res = await fetch('/api/claude/status')
// Response: { available: true, version: "2.0.76", path: "~/.local/bin/claude" }
```

**Send Message (Streaming):**
```javascript
// Uses SSE streaming for real-time output
const res = await fetch('/api/claude/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: userMessage,
    session_id: sessionId.value,
    allowed_tools: selectedPreset.value.tools
  }),
  signal: abortController.signal
})

// Read stream with ReadableStream API
const reader = res.body.getReader()
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  // Parse SSE events (data: {...}\n\n)
}
```

**SSE Event Types:**
```javascript
{ type: 'init', message: 'Starting Claude Code...' }
{ type: 'message', text: '...', session_id: '...' }
{ type: 'tool_use', tool: 'Bash', session_id: '...' }
{ type: 'system', message: '...' }
{ type: 'result', result: '...', session_id, cost_usd, duration_ms }
{ type: 'error', error: '...', session_id }
{ type: 'done', session_id, duration_ms }
{ type: 'cancelled' }
```

**Session Management:**
```javascript
// Save session
await fetch('/api/claude/sessions', {
  method: 'POST',
  body: JSON.stringify({ session_id, name, first_message })
})

// Load sessions (sorted by updated_at descending)
await fetch('/api/claude/sessions')
// Response: { sessions: [{ session_id, name, first_message, created_at, updated_at }] }

// Delete session
await fetch(`/api/claude/sessions/${session_id}`, { method: 'DELETE' })
```

**File Upload:**
```javascript
// Upload file (images, PDFs)
const formData = new FormData()
formData.append('file', file)
formData.append('agent', 'sparky')  // or 'rick'

const res = await fetch('/api/upload', {
  method: 'POST',
  body: formData
})
// Response: { success: true, filename: "abc123_file.png", path: "/home/eugene/agent-sparky/uploads/abc123_file.png", size: 12345 }

// List uploads
await fetch('/api/uploads/sparky')
// Response: { files: [{ name, path, size, modified }], agent: "sparky" }

// Delete upload
await fetch('/api/uploads/sparky/filename.png', { method: 'DELETE' })
```

## Backend Layer

### FastAPI Endpoints (`backend/main.py`)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/claude/status` | GET | Check Claude CLI availability |
| `/api/claude/chat` | POST | Send message, get response (sync, legacy) |
| `/api/claude/chat/stream` | POST | **Stream response via SSE** |
| `/api/claude/sessions` | GET | List saved sessions (sorted by updated_at) |
| `/api/claude/sessions` | POST | Save/update session |
| `/api/claude/sessions/{id}` | DELETE | Delete session |
| `/api/upload` | POST | Upload file (images, PDFs) for agent |
| `/api/uploads/{agent}` | GET | List uploaded files |
| `/api/uploads/{agent}/{filename}` | DELETE | Delete uploaded file |

### Claude CLI Execution (Streaming)

```python
# backend/main.py - Streaming endpoint
async def claude_chat_stream(request):
    cmd = [
        CLAUDE_PATH,                    # ~/.local/bin/claude
        "-p", request.message,          # Prompt
        "--output-format", "stream-json", # Real-time JSON events
        "--dangerously-skip-permissions"  # YOLO mode - no approval
    ]

    if request.session_id:
        cmd.extend(["--resume", request.session_id])

    if request.allowed_tools:
        cmd.extend(["--allowedTools", ",".join(request.allowed_tools)])

    # Use asyncio.create_subprocess_exec for non-blocking I/O
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Stream events as they arrive
    while True:
        line = await process.stdout.readline()
        if not line: break
        event = json.loads(line)
        yield f"data: {json.dumps(transformed_event)}\n\n"
```

### Session Storage

```python
SESSIONS_FILE = "~/.dgx-web-ui-sessions.json"

def load_sessions():
    return json.load(open(SESSIONS_FILE))

def save_sessions(data):
    json.dump(data, open(SESSIONS_FILE, 'w'))
```

## Data Flow

### Normal Flow (Streaming)
1. **Check status**: On mount, verify Claude CLI available
2. **Load sessions**: Fetch previously saved sessions
3. **User types message**: Input stored in `inputMessage`
4. **Send message**: POST to `/api/claude/chat/stream`
5. **Backend starts**: Create async subprocess with `stream-json` output
6. **Stream events**: Events yielded as SSE `data:` lines
7. **Frontend updates**: Real-time UI updates as events arrive
8. **Completion**: `result` or `done` event signals end
9. **Auto-save**: New sessions saved automatically

```
User Input --> /api/claude/chat/stream --> asyncio subprocess
                                              |
                                    claude -p "..." --output-format stream-json
                                              |
                                    Real-time events (SSE)
                                              |
                         type: init -> message -> tool_use -> result -> done
                                              |
                                    Live UI updates
```

### Error/Resume Flow
1. **Connection drops**: Fetch throws error
2. **Preserve state**: `lastFailedSessionId` set to current session
3. **Show banner**: "Task may have completed. Resume?"
4. **User clicks Resume**: Send follow-up with `--resume SESSION_ID`
5. **Claude responds**: Summarizes what happened in previous task

## UI Features

### Real-time Streaming
- Message content updates as Claude works
- Blinking cursor (`▋`) indicates active streaming
- Tool usage shown as `[Using Bash...]`

### Cancel Button
- Red cancel button replaces send button during streaming
- Calls `abortController.abort()` to cancel fetch
- Shows `[Cancelled by user]` in message

### Resume Banner
- Appears on error/timeout if session exists
- "Task may have completed" warning
- "Resume" button to check results
- "×" button to dismiss

### Tool Indicator
- Purple badge shows tools used: `🔧 Bash, Read`
- Updates live as Claude uses tools

### File Upload
- 📎 button next to input opens file picker
- Drag & drop files onto input area
- Supported: images (jpg, png, gif, webp) and PDFs
- Max file size: 50MB
- Files uploaded to `~/agent-sparky/uploads/` (or `~/agent-rick/uploads/`)
- File paths appended to message: `[Attached files: /path/to/file.png]`
- Agent can use Read tool to view uploaded images/files

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| Claude offline | status.available=false | Offline badge | Install Claude |
| Connection drop | fetch throws | Error message + Resume banner | Click Resume |
| Timeout | SSE stream times out | Error message + Resume banner | Click Resume |
| Execution error | `type: 'error'` event | Error in message | Check command |
| User cancels | AbortError | `[Cancelled by user]` | Send new message |

## Configuration

- **CLAUDE_PATH**: `~/.local/bin/claude`
- **SPARKY_WORKING_DIR**: `~/agent-sparky`
- **SESSIONS_FILE**: `~/.dgx-web-ui-sessions.json`
- **UPLOAD_DIRS**: `~/agent-sparky/uploads/`, `~/agent-rick/uploads/`
- **MAX_FILE_SIZE**: 50MB
- **ALLOWED_EXTENSIONS**: .jpg, .jpeg, .png, .gif, .webp, .pdf
- **SSE Headers**: `Cache-Control: no-cache`, `X-Accel-Buffering: no` (nginx)

## Security Considerations

- **`--dangerously-skip-permissions`**: Allows autonomous execution
- **Tool Presets**: Optional restrictions on available tools
- **Session persistence**: Local JSON file on DGX

## Related Flows

- **Upstream**: None
- **Downstream**: Can manage containers, services via CLI
