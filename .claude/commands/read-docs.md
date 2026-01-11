# Read Project Documentation

Load all project documentation into context for this session.

## Instructions

1. Read these files in full (no summaries until all are loaded):
   - `docs/memory/requirements.md` - Feature requirements (SINGLE SOURCE OF TRUTH)
   - `docs/memory/architecture.md` - Current system design
   - `docs/memory/roadmap.md` - Prioritized task queue
   - `docs/memory/feature-flows.md` - Feature flow index

2. Read changelog using Bash (file may be large, only need recent entries):
   - Run: `head -150 docs/memory/changelog.md`
   - Do NOT use the Read tool for changelog - use Bash with head command

   Note: `CLAUDE.md` is loaded automatically at session start - no need to read it again.

3. Understand the current project state:
   - What features are implemented?
   - What's currently in progress?
   - What are the current priorities in the roadmap?

4. Report completion:
   ```
   Documentation loaded. Ready to work on DGX Spark Web UI.

   Current Phase: [phase name from roadmap]
   Top Priority: [first incomplete item from roadmap]
   Recent Change: [most recent changelog entry]
   ```

## When to Use

- At the start of a new session
- When you need to understand the current project state
- Before starting work on a new task
- When switching between different areas of the codebase

## Principle

Load context first, then act. Never modify code without understanding the current state.
