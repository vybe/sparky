# Feature: Agent Chat

## Overview
Chat interface to Claude Code CLI running on DGX for autonomous system operations.

## User Story
As a user, I want to send commands to Claude Code so that it can manage the DGX system autonomously.

## Entry Points
- **UI**: `src/components/AgentChat.vue:215` - Agent chat interface
- **API**: FastAPI backend at `/api/claude/*`

## Frontend Layer

### Components
- `src/components/AgentChat.vue:221-246` - Header with status, cost, sessions, preset
- `src/components/AgentChat.vue:264-290` - Session picker panel
- `src/components/AgentChat.vue:292-331` - Messages container
- `src/components/AgentChat.vue:334-356` - Input textarea and send button

**Key State:**
```javascript
messages        // ref([]) - Chat messages with role, content, loading
inputMessage    // ref('') - Current input
isLoading       // ref(false) - Request in progress
sessionId       // ref(null) - Claude session ID for context
claudeStatus    // ref(null) - { available, version, path }
totalCost       // ref(0) - Cumulative session cost in USD
savedSessions   // ref([]) - Persisted sessions
selectedPreset  // ref(toolPresets[0]) - Tool access level
```

### Composables
- `src/composables/useAgent.js:3-178` - Used by Mobile.vue

**Tool Presets:**
```javascript
// src/components/AgentChat.vue:19-24
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
// src/components/AgentChat.vue:30-31
const res = await fetch('/api/claude/status')
// Response: { available: true, version: "2.0.76", path: "~/.local/bin/claude" }
```

**Send Message:**
```javascript
// src/components/AgentChat.vue:140-144
await fetch('/api/claude/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: userMessage,
    session_id: sessionId.value,
    allowed_tools: selectedPreset.value.tools
  })
})
// Response: { result, session_id, duration_ms, cost_usd, is_error }
```

**Session Management:**
```javascript
// Save session
await fetch('/api/claude/sessions', {
  method: 'POST',
  body: JSON.stringify({ session_id, name, first_message })
})

// Load sessions
await fetch('/api/claude/sessions')
// Response: { sessions: [{ session_id, name, first_message, created_at }] }

// Delete session
await fetch(`/api/claude/sessions/${session_id}`, { method: 'DELETE' })
```

## Backend Layer

### FastAPI Endpoints (`backend/main.py`)

| Endpoint | Method | Line | Purpose |
|----------|--------|------|---------|
| `/api/claude/status` | GET | 627 | Check Claude CLI availability |
| `/api/claude/chat` | POST | 648 | Send message, get response |
| `/api/claude/sessions` | GET | 716 | List saved sessions |
| `/api/claude/sessions` | POST | 723 | Save/update session |
| `/api/claude/sessions/{id}` | DELETE | 755 | Delete session |
| `/api/claude/chat/stream` | POST | 772 | Stream response (future) |

### Claude CLI Execution

```python
# backend/main.py:653-675
cmd = [
    CLAUDE_PATH,                    # ~/.local/bin/claude
    "-p", request.message,          # Prompt
    "--output-format", "json",      # JSON response
    "--dangerously-skip-permissions"  # YOLO mode - no approval
]

if request.session_id:
    cmd.extend(["--resume", request.session_id])

if request.allowed_tools:
    cmd.extend(["--allowedTools", ",".join(request.allowed_tools)])

result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=300,  # 5 minute timeout
    env={**os.environ, "PATH": f"~/.local/bin:{PATH}"}
)
```

### Session Storage

```python
# backend/main.py:91-108
SESSIONS_FILE = "~/.dgx-web-ui-sessions.json"

def load_sessions():
    return json.load(open(SESSIONS_FILE))

def save_sessions(data):
    json.dump(data, open(SESSIONS_FILE, 'w'))
```

## Data Flow

1. **Check status**: On mount, verify Claude CLI available
2. **Load sessions**: Fetch previously saved sessions
3. **User types message**: Input stored in `inputMessage`
4. **Send message**: POST to `/api/claude/chat`
5. **Backend executes**: Claude CLI runs with message
6. **Parse response**: JSON output parsed for result, session_id, cost
7. **Update UI**: Message appended, session tracked
8. **Auto-save**: New sessions saved automatically

```
User Input --> /api/claude/chat --> subprocess.run(claude -p "..." --output-format json)
                                                      |
                                               Claude CLI
                                                      |
                                               { result, session_id, cost_usd }
                                                      |
                                         Update messages + session
```

## Claude CLI Integration

**Executable Path:**
```python
CLAUDE_PATH = os.path.expanduser("~/.local/bin/claude")
```

**Output Format:**
```json
{
  "result": "Command output or response text",
  "session_id": "uuid-for-continuation",
  "duration_ms": 1234,
  "total_cost_usd": 0.0042,
  "is_error": false
}
```

**Session Continuation:**
```bash
claude -p "follow up" --resume SESSION_ID
```

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| Claude offline | status.available=false | Offline badge | Install Claude |
| Timeout (5 min) | subprocess.TimeoutExpired | 504 error | Simplify request |
| Execution error | Non-zero return | Error in result | Check command |
| JSON parse fail | JSONDecodeError | Raw output shown | N/A |

## Configuration

- **CLAUDE_PATH**: `backend/main.py:83` - `~/.local/bin/claude`
- **SESSIONS_FILE**: `backend/main.py:91` - `~/.dgx-web-ui-sessions.json`
- **Timeout**: 300 seconds (5 minutes)

## Security Considerations

- **`--dangerously-skip-permissions`**: Allows autonomous execution
- **Tool Presets**: Optional restrictions on available tools
- **Session persistence**: Local JSON file on DGX

## Related Flows

- **Upstream**: None
- **Downstream**: Can manage containers, services via CLI
