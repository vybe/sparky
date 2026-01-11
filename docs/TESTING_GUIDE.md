# Testing Guide

> Testing practices for DGX Spark Web UI.

---

## Philosophy

1. **Browser testing is primary** — Vue UI must be tested in browser
2. **Service health checks** — Verify external services before testing features
3. **Feature flows include testing** — Each flow doc has a Testing section
4. **Manual integration > automated unit** — For UI and external service integration

---

## Testing Tiers

### Tier 1: Service Health (Fast)

Verify all services are responding:

```bash
# Ollama
curl -s http://localhost:11434/api/version

# ComfyUI
curl -s http://localhost:8188/system_stats

# Backend API
curl -s http://localhost:3081/health
```

### Tier 2: Feature Testing (Standard)

Test each feature through the UI:
- Navigate to feature tab
- Perform typical actions
- Verify expected results
- Check console for errors

### Tier 3: Edge Case Testing (Comprehensive)

Test error conditions:
- Service unavailable
- Invalid input
- Timeout scenarios
- Network interruption

---

## Feature Testing Checklist

### Chat
- [ ] Model selection works
- [ ] Streaming responses display
- [ ] Clear conversation works
- [ ] Copy message works

### Image Generation
- [ ] Prompt submission works
- [ ] Progress indicator shows
- [ ] Image displays on complete
- [ ] Download works

### Video Generation
- [ ] Frame count selection works
- [ ] Generation completes
- [ ] Video plays in UI
- [ ] Download works

### Voice Chat
- [ ] Recording works
- [ ] Transcription appears
- [ ] TTS plays response
- [ ] Voice selection works

### Container Management
- [ ] Container list loads
- [ ] Start/Stop/Restart work
- [ ] Logs display correctly

---

## Using test-runner Agent

Request service health verification:
```
Run the test-runner agent
```

The agent will:
1. Check all service endpoints
2. Report status and response times
3. Identify any failures
4. Provide recommendations

---

## Browser Testing

### Development Mode

```bash
npm run dev
```

Open http://localhost:3000

Requires SSH tunnel to DGX services:
```bash
# From dgx directory
./tunnel.sh &
```

### Production Testing

```bash
./deploy.sh deploy
```

Access at http://192.168.1.127:3080

---

## Common Issues

### Chat Returns 403
Ollama CORS not configured:
```bash
sudo snap set ollama origins='*'
sudo snap restart ollama
```

### ComfyUI Timeout
Container may need restart:
```bash
sudo docker restart comfyui
```

### Voice Chat Not Working
Ultravox container issue:
```bash
sudo docker restart ultravox-vllm
```

---

## Quality Thresholds

| Metric | Healthy | Warning | Action |
|--------|---------|---------|--------|
| All services responding | ✅ | - | Continue |
| 1-2 services down | - | ⚠️ | Investigate |
| Core service down | - | - | 🛑 Fix first |
| Console errors | 0 | 1-2 | Fix before commit |

---

## Before Committing

1. [ ] All features tested in browser
2. [ ] No console errors
3. [ ] Service health checks pass
4. [ ] `/security-check` passes
