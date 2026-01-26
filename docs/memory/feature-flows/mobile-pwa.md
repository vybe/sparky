# Feature: Mobile PWA

## Overview
Mobile-optimized Progressive Web App interface providing touch-friendly access to all DGX Spark features with offline caching and home screen installation support.

## User Story
As a mobile user, I want to control DGX Spark from my phone so that I can generate content and manage services without needing a desktop browser.

## Entry Points
- **UI**: `src/components/Mobile.vue:1` - Full mobile interface with 8 tabs
- **PWA**: `public/manifest.json` - Web app manifest for installation
- **URL**: `/?mobile=1` or `/?rick=1` for Rick-only mode
- **Shortcuts**: `/?mobile=1&tab=chat` or `/?mobile=1&tab=image` via PWA shortcuts

## Frontend Layer

### Components

**Mobile.vue** (`src/components/Mobile.vue`)
- Lines 362-420: Lifecycle hooks - mounts composables, checks URL params, sets up keyboard handling
- Lines 422-1264: Template - 8 tab panels (Status, Agent, Rick, Goose, Chat, Image, Video, Manage)
- Lines 1266+: Scoped styles - mobile-first responsive layout

**App.vue** (`src/App.vue:14-25`)
- Detects mobile mode via `?mobile=1` URL param or standalone PWA display mode
- Conditionally renders `Mobile.vue` instead of desktop components

### Tab Navigation

```javascript
// src/constants/mobileConstants.js:5-14
export const tabs = [
  { id: 'status', icon: '...', name: 'Status' },
  { id: 'agent', icon: '...', name: 'Agent' },
  { id: 'rick', icon: '...', name: 'Rick' },
  { id: 'goose', icon: '...', name: 'Goose' },
  { id: 'chat', icon: '...', name: 'Chat' },
  { id: 'image', icon: '...', name: 'Image' },
  { id: 'video', icon: '...', name: 'Video' },
  { id: 'manage', icon: '...', name: 'Manage' },
]
```

### Composables Used

Mobile.vue reuses all existing composables for feature logic:

| Composable | Import Line | Purpose |
|------------|-------------|---------|
| `useTelemetry` | Line 12 | System stats, charts, loaded models |
| `useChat` | Line 13 | Ollama chat with model selection |
| `useAgent` | Line 14 | Claude Code agent integration |
| `useRick` | Line 15 | Rick family assistant agent |
| `useImageGeneration` | Line 16 | ComfyUI image generation |
| `useVideoGeneration` | Line 17 | ComfyUI LTX video generation |
| `useManagement` | Line 18 | Container/service management |

**Goose Agent** (Lines 227-359) - Implemented inline rather than in separate composable:
- `gooseMessages`, `gooseInput`, `gooseLoading`, `gooseStatus` refs
- `sendGooseMessage()` - POST to `/api/goose/chat`
- `loadResearchFiles()` - GET `/api/goose/research`
- `viewResearchFile()`, `deleteResearchFile()` - Research management

### PWA Configuration

**Manifest** (`public/manifest.json`)
```json
{
  "name": "Sparky - NVidia DGX Spark instance",
  "short_name": "Sparky",
  "start_url": "/?mobile=1",
  "display": "standalone",
  "background_color": "#111827",
  "theme_color": "#111827",
  "orientation": "portrait",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192" },
    { "src": "/icons/icon-512.png", "sizes": "512x512" }
  ],
  "shortcuts": [
    { "name": "Chat", "url": "/?mobile=1&tab=chat" },
    { "name": "Generate Image", "url": "/?mobile=1&tab=image" }
  ]
}
```

**Service Worker** (`public/sw.js`)
```javascript
// Cache strategy: Network-first with cache fallback
const CACHE_NAME = 'dgx-spark-v3'
const STATIC_ASSETS = ['/', '/index.html', '/config.js', '/manifest.json', '/icons/*']

// Install: Cache static assets, skip waiting
// Activate: Clear old caches, claim clients immediately
// Fetch: Network first, cache fallback for GET requests
//        API calls (/api/*) are never cached
```

**Service Worker Registration** (`index.html:31-57`)
- Unregisters old service workers on load
- Clears all caches before fresh registration
- Registers with `?v=3` cache buster

### iOS Keyboard Handling

**Visual Viewport API** (Lines 56-81)
```javascript
// Handle iOS keyboard resizing
function handleViewportResize() {
  if (window.visualViewport && isInputFocused.value) {
    const viewport = window.visualViewport
    // Position input at bottom of visible viewport using TOP positioning
    inputContainerTop.value = viewport.offsetTop + viewport.height
  }
}

// Setup listeners on mount
window.visualViewport.addEventListener('resize', handleViewportResize)
window.visualViewport.addEventListener('scroll', handleViewportResize)
```

**Safe Area Insets** (`index.html:60-67`)
```css
:root {
  --sat: env(safe-area-inset-top);
  --sar: env(safe-area-inset-right);
  --sab: env(safe-area-inset-bottom);
  --sal: env(safe-area-inset-left);
}
```

### API Calls

All API calls route through existing composables. Mobile-specific calls:

**Goose Status Check:**
```javascript
// src/components/Mobile.vue:243-250
const res = await fetch(`${apiBaseUrl.value}/goose/status`)
gooseStatus.value = await res.json()
```

**Goose Chat:**
```javascript
// src/components/Mobile.vue:298-310
const res = await fetch(`${apiBaseUrl.value}/goose/chat`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ message: userMessage, mode: gooseMode.value })
})
```

**Research Files:**
```javascript
// src/components/Mobile.vue:252-260
const res = await fetch(`${apiBaseUrl.value}/goose/research`)
const data = await res.json()
savedResearch.value = data.files || []
```

## Backend Layer

Mobile PWA uses the same backend endpoints as desktop. No mobile-specific backend code.

**Backend Endpoints Used:**
| Endpoint | Purpose |
|----------|---------|
| `/api/processes` | Top processes for Status tab |
| `/api/goose/*` | Goose research agent |
| `/api/agent/*` | Claude Code agent |
| `/api/rick/*` | Rick family assistant |
| `/api/containers/*` | Container management |
| `/api/services/*` | Service management |
| `/api/trinity/*` | Trinity agent platform |

## Configuration

**Constants** (`src/constants/mobileConstants.js`)
- `tabs` - Navigation tab definitions
- `network` - Local/Tailscale IP addresses
- `hardware` - DGX Spark hardware specs for display
- `serviceLinks` - Quick links to external services
- `availableModels` - Model lists by category
- `imageModels`, `videoModels` - ComfyUI model definitions
- `videoPresets` - Resolution/frame presets

**Environment Variables:**
```javascript
VITE_LOCAL_IP    // Override local network IP (default: 192.168.1.100)
VITE_VPN_IP      // Override Tailscale VPN IP (default: 100.100.100.100)
```

## Data Flow

### PWA Installation Flow
```
1. User visits /?mobile=1 in browser
2. index.html loads manifest.json, registers service worker
3. Browser prompts "Add to Home Screen" (iOS/Android)
4. User installs -> App opens in standalone mode
5. App.vue detects (display-mode: standalone) -> renders Mobile.vue
```

### Tab Navigation Flow
```
1. User taps tab in bottom nav (Lines 1246-1251)
2. activeTab ref updates
3. watch(activeTab) triggers (Lines 403-420)
4. Tab-specific initialization runs:
   - status: initTelemetryCharts()
   - agent: checkAgentStatus()
   - rick: checkRickStatus(), loadRickSessions()
   - goose: checkGooseStatus(), loadResearchFiles()
   - chat: loadChatModels()
   - manage: loadManagement()
```

### Rick-Only Mode Flow
```
1. User visits /?rick=1
2. onMounted checks URL params (Lines 364-375)
3. rickOnly.value = true, activeTab = 'rick'
4. Header shows "Rick" instead of "Sparky"
5. Bottom nav hidden (!rickOnly in v-if)
6. Only Rick tab content rendered
```

## Error Handling

| Error Case | Detection | UI Feedback | Recovery |
|------------|-----------|-------------|----------|
| Service offline | Status dot red | Red status indicator | Refresh button in header |
| Agent unavailable | agentStatus.available = false | "Offline" version text | Auto-retry on tab switch |
| Network error | Catch in async functions | Error in message bubble | User can retry |
| Model load fail | chatModelsError set | Error banner + Retry button | Reload via button |
| Container action fail | managementError set | Error banner with dismiss | Refresh list |

## PWA Files

| File | Purpose |
|------|---------|
| `public/manifest.json` | PWA manifest with icons, shortcuts, theme |
| `public/sw.js` | Service worker for caching |
| `public/icons/icon.svg` | Vector icon source |
| `public/icons/icon-192.png` | Standard PWA icon |
| `public/icons/icon-512.png` | Large PWA icon |
| `public/icons/apple-touch-icon.png` | iOS home screen icon |
| `index.html` | PWA meta tags, SW registration, safe area CSS |

## Related Flows

- **Upstream**: All feature flows (Chat, Image, Video, Agent, etc.) - Mobile reuses their composables
- **Downstream**: None - Mobile is a presentation layer
- **Parallel**: Desktop components in `App.vue` provide same features for larger screens
