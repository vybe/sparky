# Add Testing Section to Feature Flow

Add a Testing section to a feature flow document using the standard template.

## Usage

```
/add-testing {feature-flow-name}
```

Example:
```
/add-testing chat
/add-testing image-generation
```

## What It Does

1. Reads the feature flow document (`docs/memory/feature-flows/{name}.md`)
2. Adds a Testing section before "Related Flows" using the template:
   - Prerequisites checklist
   - Step-by-step test instructions
   - Expected results
   - Verification checklist
   - Edge cases
   - Status tracking
3. Updates the document

## Template

```markdown
## Testing

**Prerequisites**:
- [ ] Web UI running (`./deploy.sh status`)
- [ ] Required service running (Ollama/ComfyUI/etc.)
- [ ] SSH tunnel active (for local development)

**Test Steps**:

### 1. [Action Name]
**Action**:
- Navigate to [tab/section]
- Perform [action]

**Expected**: What should happen

**Verify**:
- [ ] UI state check
- [ ] Console check (no errors)
- [ ] Network tab check (correct API call)

### 2. [Next Action]
...

**Edge Cases**:
- [ ] Empty input handling
- [ ] Very long input
- [ ] Service unavailable
- [ ] Network timeout

**Cleanup**:
- [ ] Clear any generated files
- [ ] Reset UI state

**Last Tested**: YYYY-MM-DD
**Tested By**: Not yet tested
**Status**: 🚧 Not Tested
**Issues**: None
```

## Notes

- Customize the template based on the specific feature
- Include service status checks where applicable
- Document both happy path and edge cases
- Keep instructions clear and actionable
