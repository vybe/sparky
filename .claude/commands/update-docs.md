# Update Project Documentation

Update project documentation after making changes.

## Instructions

1. Get current timestamp:
   ```bash
   date '+%Y-%m-%d %H:%M:%S'
   ```

2. Update `docs/memory/changelog.md`:
   - Add entry at the TOP of "Recent Changes" section
   - Use appropriate emoji prefix:
     - 🎉 Major milestones
     - ✨ New features
     - 🔧 Bug fixes
     - 🔄 Refactoring
     - 📝 Documentation
     - 🔒 Security updates
     - 🚀 Performance improvements
     - 💾 Data/persistence changes
     - 🐳 Infrastructure/DevOps
   - Include what changed and why

3. If API/schema/integration changed:
   - Update `docs/memory/architecture.md`
   - Add new endpoints to API table
   - Update service configuration if changed
   - Update architecture diagram if needed

4. If feature behavior changed:
   - Check if feature flow exists in `docs/memory/feature-flows/`
   - Update existing flow document if it exists
   - Note if a new flow document is needed

5. If feature scope changed:
   - Update `docs/memory/requirements.md`
   - Mark requirements as completed if done
   - Add new requirements if scope expanded

6. Update `docs/memory/roadmap.md` if:
   - Task completed (mark with ✅ and timestamp)
   - New tasks discovered (add to appropriate phase)

## Format for Changelog Entry

```markdown
### YYYY-MM-DD HH:MM:SS
🔧 **Brief Title**
- What was changed
- Why it was changed
- Key files: `path/to/file.vue`, `another/file.py`
```

## Principle

Make MINIMAL necessary documentation changes only. Don't add unnecessary detail.
