# Feature: Research Agent

## Overview
Web research interface using Goose agent with DuckDuckGo search and file storage capabilities.

## User Story
As a user, I want to research topics and save findings so that I can build a knowledge base from web sources.

## Entry Points
- **UI**: `src/components/GooseChat.vue:194` - Research chat interface
- **API**: FastAPI backend at `/api/goose/*`

## Frontend Layer

### Components
- `src/components/GooseChat.vue:197-222` - Header with status and mode selector
- `src/components/GooseChat.vue:231-271` - Research panel (saved files)
- `src/components/GooseChat.vue:274-332` - Messages with sources and saved indicator
- `src/components/GooseChat.vue:336-358` - Input and send button

**Key State:**
```javascript
messages         // ref([]) - Chat with sources and saved_file
inputMessage     // ref('') - Current query
isLoading        // ref(false) - Request in progress
gooseStatus      // ref(null) - { available, version, path }
savedResearch    // ref([]) - List of saved .md files
researchMode     // ref('chat') - 'chat' or 'research'
selectedResearch // ref(null) - Currently viewing file
```

**Modes:**
```javascript
// src/components/GooseChat.vue:17-20
const modes = [
  { id: 'chat', name: 'Quick Chat', desc: 'Fast Q&A with web search' },
  { id: 'research', name: 'Deep Research', desc: 'Full research with saved notes' },
]
```

### API Calls

**Check Status:**
```javascript
// src/components/GooseChat.vue:26-27
const res = await fetch('/api/goose/status')
// Response: { available: true, version: "1.19.1", path: "~/.local/bin/goose" }
```

**Send Message:**
```javascript
// src/components/GooseChat.vue:116-119
await fetch('/api/goose/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: userMessage,
    mode: researchMode.value  // 'chat' or 'research'
  })
})
// Response: { result, duration_ms, sources: [], saved_file, is_error }
```

**Research Files:**
```javascript
// List files
await fetch('/api/goose/research')
// Response: { files: [{ name, size, modified }] }

// Get content
await fetch(`/api/goose/research/${filename}`)
// Response: { content, filename }

// Delete file
await fetch(`/api/goose/research/${filename}`, { method: 'DELETE' })
```

## Backend Layer

### FastAPI Endpoints (`backend/main.py`)

| Endpoint | Method | Line | Purpose |
|----------|--------|------|---------|
| `/api/goose/status` | GET | 815 | Check Goose availability |
| `/api/goose/chat` | POST | 836 | Send query, get researched response |
| `/api/goose/research` | GET | 927 | List saved research files |
| `/api/goose/research/{name}` | GET | 953 | Get research file content |
| `/api/goose/research/{name}` | DELETE | 975 | Delete research file |

### Goose CLI Execution

**Chat Mode:**
```python
# backend/main.py:853-856
cmd = [
    GOOSE_PATH,  # ~/.local/bin/goose
    "run",
    "--text", request.message
]
```

**Research Mode:**
```python
# backend/main.py:846-850
cmd = [
    GOOSE_PATH,
    "run",
    "--recipe", os.path.join(GOOSE_RESEARCH_DIR, "research-agent.yaml"),
    "--params", f"topic={request.message}"
]
```

### Environment Setup

```python
# backend/main.py:859-864
env = {
    **os.environ,
    "OLLAMA_HOST": "http://host.docker.internal:11434",
    "PATH": f"~/.local/bin:{PATH}"
}
```

### Source Extraction

```python
# backend/main.py:893-904
# Extract URLs from output
raw_urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', output)
sources = list(set(cleaned_urls))[:10]  # Dedupe, limit to 10

# Check for saved file
saved_match = re.search(r'(?:Saved to|saved to|Saving to):\s*([^\s\n]+\.md)', output)
```

## Goose Research Agent

**Location:** `~/goose-research/` on DGX

**Recipe File:** `research-agent.yaml`
```yaml
# Uses Ollama with qwen3:30b-a3b
# Has MCP tools: web_search, fetch_webpage, save_research
```

**MCP Tools Available:**
| Tool | Purpose |
|------|---------|
| `web_search(query)` | DuckDuckGo search |
| `fetch_webpage(url)` | Extract page text |
| `news_search(query)` | Search recent news |
| `save_research(topic, content)` | Save to markdown |

**Data Directory:** `~/goose-research/data/` - Saved .md files

## Data Flow

1. **Check status**: Verify Goose CLI available
2. **Select mode**: Chat (quick) or Research (with saving)
3. **Enter query**: User types research topic
4. **Backend executes**: Goose runs with query
5. **Parse output**: Extract text, URLs, saved file path
6. **Update UI**: Show response with source links
7. **Refresh files**: If file saved, reload research list

```
Query --> /api/goose/chat --> subprocess.run(goose run --text/--recipe)
                                            |
                                      Goose + MCP tools
                                            |
                          web_search --> fetch_webpage --> save_research
                                            |
                                      { result, sources, saved_file }
```

## Response Format

```javascript
{
  result: "Research findings text...",
  duration_ms: 45000,
  sources: [
    "https://example.com/article1",
    "https://example.com/article2"
  ],
  saved_file: "AI_Agents_Research.md",  // or null
  is_error: false
}
```

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| Goose offline | status.available=false | Offline badge | Install Goose |
| Timeout | 10 min (research) / 3 min (chat) | 504 error | Simplify query |
| No results | Empty output | Shows empty result | Refine query |
| File access | Security check fails | 403 error | N/A |

## Configuration

- **GOOSE_PATH**: `backend/main.py:86` - `~/.local/bin/goose`
- **GOOSE_RESEARCH_DIR**: `backend/main.py:87` - `~/goose-research`
- **GOOSE_DATA_DIR**: `backend/main.py:88` - `~/goose-research/data`
- **Timeouts**: Research 600s, Chat 180s

## Security

```python
# backend/main.py:962-964
# Prevent path traversal
real_path = os.path.realpath(filepath)
if not real_path.startswith(os.path.realpath(GOOSE_DATA_DIR)):
    raise HTTPException(status_code=403, detail="Access denied")
```

## Related Flows

- **Upstream**: Uses Ollama for LLM inference
- **Parallel**: Agent Chat uses similar CLI execution pattern
