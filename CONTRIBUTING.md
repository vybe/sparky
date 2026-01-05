# Contributing to DGX Web UI

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help maintain a welcoming environment

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/dgx-web-ui`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test thoroughly
6. Submit a pull request

## Development Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Coding Standards

### Vue Components

- Use Composition API with `<script setup>`
- Keep components focused and single-purpose
- Use composables for shared logic
- Follow existing naming conventions

Example:
```vue
<script setup>
import { ref, onMounted } from 'vue'

const data = ref(null)

onMounted(async () => {
  // Load data
})
</script>

<template>
  <div class="container">
    <!-- Component markup -->
  </div>
</template>
```

### JavaScript/TypeScript

- Use modern ES6+ features
- Prefer `const` over `let`, avoid `var`
- Use async/await over callbacks
- Handle errors properly

### CSS/Styling

- Use Tailwind CSS utility classes
- Follow mobile-first responsive design
- Avoid inline styles unless dynamic
- Keep custom CSS minimal

### Python (Backend)

- Follow PEP 8 style guide
- Use type hints
- Write docstrings for functions
- Handle exceptions appropriately

## Testing

Before submitting:

1. Test locally with `npm run dev`
2. Test production build with `npm run build`
3. Verify all features work
4. Check console for errors
5. Test mobile view (`?mobile=1`)

## Security Guidelines

### Never Commit

- Passwords or API keys
- Hardcoded IP addresses specific to your environment
- `.env` files
- Session files
- Personal data

### Always

- Use environment variables for configuration
- Provide `.example` files for sensitive configs
- Sanitize user input
- Use HTTPS in production
- Keep dependencies updated

### Security Checklist

- [ ] No hardcoded credentials
- [ ] No sensitive paths or IPs
- [ ] `.env` in `.gitignore`
- [ ] Input validation added
- [ ] Error messages don't leak info

## Pull Request Guidelines

### Before Submitting

1. Update documentation if needed
2. Add/update tests if applicable
3. Ensure no console errors
4. Check for security issues
5. Update CHANGELOG.md if applicable

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How has this been tested?

## Checklist
- [ ] Code follows project style
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Tested locally
- [ ] No console errors
```

## Feature Requests

Feature requests are welcome! Please:

1. Check existing issues first
2. Describe the use case clearly
3. Explain why it's useful
4. Provide examples if possible

## Bug Reports

When reporting bugs, include:

1. **Environment**: Browser, OS, versions
2. **Steps to reproduce**: Exact steps to trigger the bug
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Screenshots**: If applicable
6. **Console logs**: Any error messages

Example:
```markdown
**Environment:** Chrome 120, macOS 14
**Steps:**
1. Open image generator
2. Select "Flux Abliterated"
3. Click Generate

**Expected:** Image generates successfully
**Actual:** Error "Model not found"
**Console:** `TypeError: Cannot read property 'name' of undefined`
```

## Code Review Process

1. Maintainer reviews your PR
2. Feedback provided via comments
3. Make requested changes
4. Maintainer approves and merges

## File Organization

```
dgx-web-ui/
├── src/
│   ├── components/      # Vue components
│   ├── composables/     # Reusable composition functions
│   ├── constants/       # App constants
│   ├── utils/          # Utility functions
│   └── config.js       # Configuration loader
├── backend/            # FastAPI backend
│   ├── main.py         # API server
│   └── Dockerfile      # Backend container
├── public/             # Static assets
│   ├── config.js       # Runtime config
│   ├── manifest.json   # PWA manifest
│   └── icons/          # App icons
├── docs/              # Documentation (optional)
└── tests/             # Tests (optional)
```

## Adding New Features

### New API Endpoint

1. Add to `backend/main.py`
2. Document in docstring
3. Add error handling
4. Test with curl/Postman

### New UI Component

1. Create in `src/components/`
2. Use existing patterns
3. Make responsive
4. Add to appropriate view

### New Service Integration

1. Add to backend API
2. Update frontend composable
3. Add to management page
4. Document in README/SETUP

## Documentation

When adding features:

- Update README.md with usage
- Update SETUP.md with configuration
- Add JSDoc comments for functions
- Include examples

## Versioning

We use Semantic Versioning (SemVer):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

## Questions?

- Open an issue for questions
- Check existing documentation
- Ask in discussions (if enabled)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Your contributions make this project better for everyone!
