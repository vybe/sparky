# Pre-Commit Security Check

Validate that staged changes don't contain sensitive information before committing.

## Instructions

Run these checks on staged files (or all modified files if nothing staged):

### 1. Get files to check

```bash
# Check if there are staged files
STAGED=$(git diff --cached --name-only 2>/dev/null)

if [ -n "$STAGED" ]; then
  echo "Checking staged files..."
  FILES="$STAGED"
else
  # Fall back to all modified files
  echo "No staged files. Checking all modified files..."
  FILES=$(git diff --name-only HEAD 2>/dev/null)
fi

echo "$FILES"
```

### 2. Check for API keys and tokens

Search for common API key patterns in the changed files:

```bash
# Common API key patterns
git diff --cached -U0 | grep -iE '(sk-[a-zA-Z0-9]{20,}|pk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22,}|xox[baprs]-[a-zA-Z0-9-]{10,}|ya29\.[a-zA-Z0-9_-]{50,}|AIza[a-zA-Z0-9_-]{35}|AKIA[A-Z0-9]{16})'
```

**Patterns checked:**
- `sk-...` — Anthropic/OpenAI secret keys
- `ghp_...`, `gho_...`, `github_pat_...` — GitHub tokens
- `xox...` — Slack tokens
- `AIza...` — Google API keys
- `AKIA...` — AWS access keys

### 3. Check for hardcoded IPs and passwords

```bash
# Check for DGX password (known issue in this repo)
git diff --cached -U0 | grep -iE 'kdr73hhe|password.*=.*["\x27][^"\x27]{6,}'

# Check for internal IPs (non-localhost)
git diff --cached -U0 | grep -oE '\b(192\.168\.[0-9]+\.[0-9]+|100\.[0-9]+\.[0-9]+\.[0-9]+)\b'
```

### 4. Check for .env files with values

```bash
# Check if any .env files are staged (not .env.example)
git diff --cached --name-only | grep -E '^\.env$|/\.env$' | grep -v '\.example'
```

**Rule:** Never commit `.env` files. Only `.env.example` with placeholder values.

### 5. Check for credential files

```bash
# Check for credential/key files being committed
git diff --cached --name-only | grep -iE '(credentials\.json|service.?account.*\.json|\.pem$|\.key$|id_rsa|id_ed25519)'
```

## Report Format

After running all checks, report:

```markdown
## Security Check Results

### Summary
| Check | Status | Findings |
|-------|--------|----------|
| API Keys | ✅/❌ | count |
| Passwords/IPs | ✅/❌ | count |
| .env Files | ✅/❌ | count |
| Credential Files | ✅/❌ | count |

### Issues Found (if any)

#### [Category]
- File: `path/to/file`
- Line: `suspicious content here...`
- Risk: [Why this is a problem]
- Fix: [How to remediate]

### Recommendations

1. [Action items if issues found]
2. [Or "Safe to commit" if clean]
```

## Severity Levels

| Level | Action | Examples |
|-------|--------|----------|
| **CRITICAL** | Do NOT commit | API keys, tokens, passwords |
| **HIGH** | Remove before commit | Real IPs, internal hostnames |
| **MEDIUM** | Review carefully | .env files, credential paths |
| **LOW** | Verify intentional | Example placeholder values |

## When to Use

- **Before every commit** — Run `/security-check` as habit
- **Before PRs** — Mandatory check before opening PR
- **Code review** — Reviewer should run on PR branch
