# Breaking Changes

## [Skill Engine v2] nginx gateway added — backend port 8000 no longer public

**Date:** 2026-04-22

### What changed

A dedicated nginx reverse-proxy container (`chatbot/nginx/`) has been added to the
Docker Compose stack. It is the sole publicly exposed service (port 80).

| Before | After |
|--------|-------|
| `backend` exposed on `:8000` | `backend` internal-only (`expose: 8000`) |
| `frontend` exposed on `:4200` | `frontend` internal-only (`expose: 80`) |
| No gateway nginx | `nginx` gateway on `:80` |

### Impact

- **Docker deployment:** Direct access to `http://localhost:8000` no longer works.
  All traffic must go through `http://localhost` (port 80).
- **Health checks / monitoring:** Update any probes that ping `localhost:8000` to
  use `localhost/health` instead.
- **Firewall / security groups:** Only port 80 (and optionally 443) need to be open.
  Port 8000 and 6379 should be blocked externally.

### Migration steps

1. Pull the latest code.
2. Run `chatbot/scripts/rebuild.sh` (macOS) or `chatbot/scripts/rebuild.ps1` (Windows).
3. Update any bookmark, health-check URL, or integration that targeted `:8000` to use `:80`.

### Local development (no Docker)

Local dev is unaffected. The Angular dev server (`ng serve`) proxies via `proxy.conf.json`
to `localhost:8000` as before. No changes to the local dev workflow.
