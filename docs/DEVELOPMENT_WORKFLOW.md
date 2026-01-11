# Development Workflow

> For developers and AI assistants working on DGX Spark Web UI.

---

## The Development Cycle

```
1. CONTEXT LOADING    →  /read-docs
       ↓
2. DEVELOPMENT        →  Implement changes
       ↓
3. TESTING            →  Browser verification + test-runner agent
       ↓
4. DOCUMENTATION      →  /update-docs
```

---

## Phase 1: Context Loading

**Always start by loading context.**

### Full Context Load
```
/read-docs
```

Loads: requirements, architecture, roadmap, changelog, feature-flows index.

### Targeted Context
If working on a specific feature:
```
Read docs/memory/feature-flows/chat.md
```

---

## Phase 2: Development

### Before Writing Code

1. **Check requirements**: Is this in `requirements.md`?
2. **Check roadmap**: Is this a current priority?
3. **Read feature flow**: Understand existing data flow

### During Development

Follow patterns in existing code:
- Components: Vue 3 Composition API with `<script setup>`
- State: Composables in `src/composables/`
- Styling: Tailwind utility classes
- API calls: fetch with async/await

---

## Phase 3: Testing

### Browser Testing

```bash
# Start dev server
npm run dev
# Open http://localhost:3000
```

Verify:
- [ ] Feature works as expected
- [ ] No console errors
- [ ] Network calls succeed
- [ ] UI responsive

### Test Runner Agent

```
Run the test-runner agent to verify services
```

---

## Phase 4: Documentation

### Always Update

```
/update-docs
```

This prompts updates to:
- `changelog.md` - Always
- `architecture.md` - If APIs changed
- `requirements.md` - If scope changed
- `feature-flows/*.md` - If behavior changed

### Feature Flow Updates

If you modified a feature significantly:
```
/feature-flow-analysis chat
```

---

## Commands Reference

| Command | Purpose | When |
|---------|---------|------|
| `/read-docs` | Load project context | Session start |
| `/update-docs` | Update documentation | After changes |
| `/feature-flow-analysis <name>` | Document feature | After modifying |
| `/security-check` | Check for secrets | Before commit |
| `/add-testing <name>` | Add test section | Improving coverage |

---

## Agents Reference

| Agent | Purpose | When |
|-------|---------|------|
| `feature-flow-analyzer` | Trace and document features | Understanding/documenting |
| `test-runner` | Verify service health | After changes |
| `security-analyzer` | OWASP security review | Before deploy |

---

## Best Practices

### DO

- ✅ Load context before starting
- ✅ Read feature flows before modifying
- ✅ Test in browser after changes
- ✅ Update feature flows when behavior changes
- ✅ Run `/security-check` before commits

### DON'T

- ❌ Skip context loading
- ❌ Modify features without reading their flow
- ❌ Commit without browser testing
- ❌ Leave feature flows outdated
- ❌ Commit hardcoded credentials or IPs
