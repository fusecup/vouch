# AGENTS Guidelines for This Repository

## ⚠️ CRITICAL: Docker-First Development

**ALL code execution happens inside Docker containers. NEVER assume commands run on the local machine.**

- Always use `docker exec -it <container-name>` or `docker compose run --rm <service>`
- Default backend container: `fusecup-backend-1`
- See [README.md](README.md) for detailed Docker commands

## Key Technologies

### Core Stack

- **Django 5.x** (Python 3.12+) - Web framework
- **PostgreSQL 17.x** - Primary database
- **Redis 7.x** - Cache and message broker
- **Celery 5.x** - Background task queue
- **UV** - Python package manager (not pip)
- **PNPM** - Node.js package manager

### Frontend

- **TailwindCSS 4.x** - Utility-first CSS
- **HTMX** - Dynamic interactions
- **Alpine.js** - Lightweight JS framework
- **Django-cotton** - UI component library

### Authentication & APIs

- **Django-allauth** - Auth + social providers (Google OAuth)
- **Gunicorn/Uvicorn** - WSGI/ASGI servers

### Development Tools

- **Ruff** - Python linter/formatter
- **Pytest** - Testing framework
- **IPython/Jupyter** - Interactive development (port 2222)
- **Django-debug-toolbar** - Debug panel (DEBUG mode only)
- **Flower** - Celery monitoring (port 5555)
- **MailCatcher** - Email testing (port 1080)

### Key Django Packages

- **django-extensions** - Enhanced management commands (shell_plus)
- **django-import-export** - Data import/export
- **django-compressor** - CSS/JS compression
- **django-countries** - Country fields
- **django-timezone-field** - Timezone support

### Monitoring & Analytics

- **Sentry** - Error tracking
- **PostHog** - Product analytics

## Docker Commands

**⚠️ See [README.md](README.md) for complete command reference.**

### Essential Patterns

```bash
# All Django commands via Docker
docker exec -it fusecup-backend-1 python manage.py <command>

# Access container shell (use ZSH)
docker exec -it fusecup-backend-1 zsh

# Package management (UV only, not pip)
docker exec -it fusecup-backend-1 uv add <package>
docker exec -it fusecup-backend-1 uv sync --frozen
```

### Makefile Shortcuts

```bash
make migrate / make migrations
make shell / make zsh
make manage ARGS="<command>"
make ruff
```

## Development Guidelines

### Django Architecture

- Apps location: `src/fusecup/apps/`
- Class-based views for complex logic, function-based for simple cases
- Business logic in models/forms, keep views light
- Use `select_related`/`prefetch_related` for query optimization
- Error handling at view level with try-except blocks

### Frontend Stack

- Use Django Templates + TailwindCSS + HTMX + Alpine.js
- **Never edit `tw-styles.css`** - use Tailwind classes only
- Implement fully without TODOs or placeholders
- Focus on readability and modern UX patterns

### Package Management

- Python: Use `uv` (not pip)
- Frontend: Use `pnpm` (not npm)
- All commands via Docker containers

## Contextual Guidance

- Use `@Docs` or context7 MCP for technical documentation
- Refer to [README.md](README.md) for setup, operations, and troubleshooting
- Check `.cursor/rules/` for framework-specific patterns
