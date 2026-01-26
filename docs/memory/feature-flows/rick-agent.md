# Feature: Rick Agent (Family Assistant)

## Overview
Family assistant chat interface using Claude Code CLI with a dedicated working directory (`~/agent-rick`) for accessing family documents and personal information. Uses SSE streaming for real-time output with session persistence and file upload support.

## User Story
As a user, I want to ask Rick about family documents, personal information, and administrative tasks so that I can quickly find expiration dates, NIF numbers, addresses, and other family-related data.

## Entry Points
- **UI**: `src/components/RickChat.vue:524` - Rick tab in desktop navigation
- **UI**: `src/App.vue:32` - Tab configuration `{ id: 'rick', name: 'Rick', icon: '...' }`
- **API**: FastAPI backend at `/api/rick/*`

## Frontend Layer

### Components
- `src/components/RickChat.vue` - Standalone component with embedded state (no external composable for desktop)
- `src/composables/useRick.js` - Shared composable for Mobile.vue integration

**Key State (RickChat.vue:4-28):**
```javascript
const messages = ref([])           // Chat messages with role, content, loading, streaming, tools
const inputMessage = ref('')       // Current input
const isLoading = ref(false)       // Request in progress
const sessionId = ref(null)        // Claude session ID for context
const rickStatus = ref(null)       // { available, version, path, working_dir }
const totalCost = ref(0)           // Cumulative session cost in USD
const savedSessions = ref([])      // Persisted sessions

// Session management
const showSessionPicker = ref(false)
const sessionName = ref('')

// Streaming state
const currentStreamController = ref(null)  // AbortController for cancellation
const streamingText = ref('')              // Accumulated streaming text
const currentTool = ref(null)              // Tool currently being used
const lastFailedSessionId = ref(null)      // Session to resume after error

// File upload state
const pendingFiles = ref([])       // Files queued for upload
const isDragging = ref(false)      // Drag & drop active
const fileInputRef = ref(null)     // Hidden file input element
const isUploading = ref(false)     // Upload in progress
```

### Composables
- `src/composables/useRick.js:1-371` - Full streaming logic for Mobile.vue
  - Same functionality as RickChat.vue but externalized for mobile

### API Calls

**Check Status (RickChat.vue:31-38):**
```javascript
const res = await fetch('/api/rick/status')
// Response: { available: true, version: "2.0.76", path: "~/.local/bin/claude", working_dir: "~/agent-rick" }
```

**Send Message - Streaming (RickChat.vue:124-341):**
```javascript
const res = await fetch('/api/rick/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: fullMessage,
    session_id: sessionId.value,
    files: uploadedPaths
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

**SSE Event Types (RickChat.vue:223-290):**
```javascript
{ type: 'init', message: 'Starting Rick...' }
{ type: 'message', text: '...', session_id: '...' }
{ type: 'tool_use', tool: 'Read', session_id: '...' }
{ type: 'system', message: '...' }
{ type: 'result', result: '...', session_id, cost_usd, duration_ms }
{ type: 'error', error: '...', session_id }
{ type: 'done', session_id, duration_ms }
{ type: 'cancelled' }
```

**Session Management (RickChat.vue:41-105):**
```javascript
// Load sessions (sorted by updated_at descending)
await fetch('/api/rick/sessions')
// Response: { sessions: [{ session_id, name, first_message, created_at, updated_at }] }

// Save session
await fetch('/api/rick/sessions', {
  method: 'POST',
  body: JSON.stringify({ session_id, name, first_message })
})

// Delete session
await fetch(`/api/rick/sessions/${session_id}`, { method: 'DELETE' })
```

**File Upload (RickChat.vue:463-499):**
```javascript
const formData = new FormData()
formData.append('file', fileObj.file)
formData.append('agent', 'rick')

const res = await fetch('/api/upload', {
  method: 'POST',
  body: formData
})
// Response: { success: true, filename: "abc123_file.png", path: "/home/eugene/agent-rick/uploads/abc123_file.png", size: 12345 }
```

## Backend Layer

### FastAPI Endpoints (`backend/main.py`)

| Endpoint | Method | Line | Purpose |
|----------|--------|------|---------|
| `/api/rick/status` | GET | 1232 | Check Claude CLI availability for Rick |
| `/api/rick/sessions` | GET | 1254 | List saved Rick sessions |
| `/api/rick/sessions` | POST | 1261 | Save/update Rick session |
| `/api/rick/sessions/{id}` | DELETE | 1290 | Delete Rick session |
| `/api/rick/chat/stream` | POST | 1307 | **Stream response via SSE** |
| `/api/rick/name-session` | POST | 1431 | Generate session name via Claude |
| `/api/upload` | POST | 795 | Upload file (shared endpoint) |

### Configuration (`backend/main.py:96-109`)
```python
# Rick agent path and sessions
RICK_SESSIONS_FILE = os.path.expanduser("~/.dgx-web-ui-rick-sessions.json")
RICK_PATH = os.path.expanduser("~/.local/bin/claude")
RICK_WORKING_DIR = os.path.expanduser("~/agent-rick")

# Upload directories for agents
UPLOAD_DIRS = {
    "rick": os.path.expanduser("~/agent-rick/uploads"),
    "sparky": os.path.expanduser("~/agent-sparky/uploads"),
}
```

### Claude CLI Execution (`backend/main.py:1307-1423`)
```python
async def rick_chat_stream(request):
    cmd = [
        RICK_PATH,                        # ~/.local/bin/claude
        "-p", request.message,            # Prompt
        "--output-format", "stream-json", # Real-time JSON events
        "--verbose",                      # Required for stream-json
        "--dangerously-skip-permissions"  # YOLO mode - no approval
    ]

    if request.session_id:
        cmd.extend(["--resume", request.session_id])

    if request.allowed_tools:
        cmd.extend(["--allowedTools", ",".join(request.allowed_tools)])

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=RICK_WORKING_DIR  # KEY DIFFERENCE: ~/agent-rick context
    )
```

### Session Storage (`backend/main.py:1215-1229`)
```python
RICK_SESSIONS_FILE = "~/.dgx-web-ui-rick-sessions.json"

def load_rick_sessions():
    return json.load(open(RICK_SESSIONS_FILE))

def save_rick_sessions(data):
    json.dump(data, open(RICK_SESSIONS_FILE, 'w'))
```

### Auto Session Naming (`backend/main.py:1431-1474`)
```python
@app.post("/api/rick/name-session")
async def rick_name_session(request):
    prompt = f'Name this conversation in 3-5 words: "{request.first_message[:200]}"'
    # Runs Claude to generate meaningful name
    # Falls back to truncated first message on error
```

## Data Flow

### Normal Flow (Streaming)
```
1. User clicks Rick tab in App.vue
2. RickChat.vue mounts, calls checkStatus() and loadSessions()
3. User types message in textarea
4. Optional: User attaches files (drag/drop or click)
5. User presses Enter or Send button
6. If files attached: uploadFiles() -> /api/upload -> paths returned
7. sendMessage() called with message + file paths
8. POST /api/rick/chat/stream
9. Backend spawns claude CLI in ~/agent-rick directory
10. SSE events stream back (init -> message -> tool_use -> result -> done)
11. UI updates in real-time with streaming text
12. On completion: auto-save new sessions with generated name
```

```
User Input --> /api/rick/chat/stream --> asyncio subprocess
                                            |
                               claude -p "..." --output-format stream-json
                                       cwd=~/agent-rick
                                            |
                               Real-time events (SSE)
                                            |
                    type: init -> message -> tool_use -> result -> done
                                            |
                                   Live UI updates
```

### File Upload Flow
```
1. User clicks attach button or drags files
2. Files added to pendingFiles[] with preview
3. On send: uploadFiles() calls /api/upload for each file
4. Paths returned: /home/eugene/agent-rick/uploads/abc123_file.png
5. Message appended: "[Attached files: /path/to/file.png]"
6. Claude can use Read tool to view uploaded content
```

### Error/Resume Flow
```
1. Connection drops: fetch throws error
2. Preserve state: lastFailedSessionId set to current session
3. Show banner: "Task may have completed. Resume?"
4. User clicks Resume: sends follow-up with --resume SESSION_ID
5. Claude responds: summarizes previous task results
```

## UI Features

### Example Prompts (RickChat.vue:608-617)
```javascript
<button @click="inputMessage = 'What documents are expiring soon?'">
<button @click="inputMessage = 'Show my Portuguese NIF number'">
<button @click="inputMessage = 'What is our current address?'">
```

### Session Picker (RickChat.vue:569-596)
- Dropdown showing saved sessions sorted by recency
- Each session shows name, preview, and relative time
- Click to load session context
- Delete button per session

### Real-time Streaming
- Message content updates as Claude works
- Blinking cursor indicates active streaming
- Tool usage shown inline: `[Using Read...]`

### File Upload UI (RickChat.vue:656-742)
- Attach button next to input
- Drag & drop overlay with visual feedback
- Pending files preview with thumbnails
- Supported: images (jpg, png, gif, webp) and PDFs
- Max 50MB per file

### Cost Display (RickChat.vue:539-541)
- Running total shown in header: "Session: $0.0234"
- Per-message cost shown in message footer

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| Claude offline | status.available=false | Offline badge | Install Claude |
| Connection drop | fetch throws | Error message + Resume banner | Click Resume |
| Timeout | SSE stream times out | Error message + Resume banner | Click Resume |
| Execution error | `type: 'error'` event | Red error in message | Check command |
| User cancels | AbortError | `[Cancelled by user]` | Send new message |
| Upload fails | res.ok=false | Console error | Re-attach file |

## Differences from Agent Chat (Sparky)

| Aspect | Agent Chat (Sparky) | Rick Agent |
|--------|---------------------|------------|
| Working Directory | `~/agent-sparky` | `~/agent-rick` |
| Sessions File | `~/.dgx-web-ui-sessions.json` | `~/.dgx-web-ui-rick-sessions.json` |
| API Prefix | `/api/claude/*` | `/api/rick/*` |
| Upload Directory | `~/agent-sparky/uploads/` | `~/agent-rick/uploads/` |
| Tool Presets | Yes (Full, Read Only, etc.) | No (always full access) |
| Purpose | System operations | Family documents/personal info |
| UI Color Theme | Purple/blue | Orange |

## Configuration

- **RICK_PATH**: `~/.local/bin/claude`
- **RICK_WORKING_DIR**: `~/agent-rick`
- **RICK_SESSIONS_FILE**: `~/.dgx-web-ui-rick-sessions.json`
- **UPLOAD_DIR**: `~/agent-rick/uploads/`
- **MAX_FILE_SIZE**: 50MB
- **ALLOWED_EXTENSIONS**: .jpg, .jpeg, .png, .gif, .webp, .pdf
- **SSE Headers**: `Cache-Control: no-cache`, `X-Accel-Buffering: no`

## Security Considerations

- **`--dangerously-skip-permissions`**: Allows autonomous file access
- **Working directory context**: Rick reads CLAUDE.md in `~/agent-rick` for family-specific instructions
- **File uploads**: Stored in dedicated uploads folder with unique prefixes
- **Session persistence**: Local JSON file on DGX

## Related Flows

- **Upstream**: None (standalone feature)
- **Downstream**: None (read-only family assistant)
- **Similar**: Agent Chat (`/docs/memory/feature-flows/agent-chat.md`) - same architecture, different context
