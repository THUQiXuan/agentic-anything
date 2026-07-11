---
name: requests
description: Agent-native resource pack for https://github.com/psf/requests/tree/v2.34.2 (74 units captured; generated without LLM).
---

# requests

## Overview

This `code` pack is a structured capture of https://github.com/psf/requests/tree/v2.34.2 made on 2026-07-11T00:00:00Z in `ingest` mode. It contains 74 evidence unit(s), an interface inventory, and markdown views an agent can read directly.

## Resource map

| page_id | type | title |
|---|---|---|
| `repo__000__tree` | code | Repository tree: requests-2.34.2 |
| `file__readme-md` | code | README.md |
| `file__tests--certs--readme-md` | code | tests/certs/README.md |
| `file__tests--certs--expired--readme-md` | code | tests/certs/expired/README.md |
| `file__tests--certs--mtls--readme-md` | code | tests/certs/mtls/README.md |
| `file__authors-rst` | code | AUTHORS.rst |
| `file__history-md` | code | HISTORY.md |
| `file__license` | code | LICENSE |
| `file__makefile` | code | Makefile |
| `file__pyproject-toml` | code | pyproject.toml |
| `file__requirements-dev-txt` | code | requirements-dev.txt |
| `file__setup-py` | code | setup.py |
| `file__tox-ini` | code | tox.ini |
| `file__docs--makefile` | code | docs/Makefile |
| `file__docs--api-rst` | code | docs/api.rst |
| `file__docs--conf-py` | code | docs/conf.py |
| `file__docs--index-rst` | code | docs/index.rst |
| `file__docs--requirements-txt` | code | docs/requirements.txt |
| `file__ext--license` | code | ext/LICENSE |
| `file__tests--init-py` | code | tests/__init__.py |
| `file__tests--compat-py` | code | tests/compat.py |
| `file__tests--conftest-py` | code | tests/conftest.py |
| `file__tests--test-adapters-py` | code | tests/test_adapters.py |
| `file__tests--test-help-py` | code | tests/test_help.py |
| `file__tests--test-hooks-py` | code | tests/test_hooks.py |
| `file__tests--test-lowlevel-py` | code | tests/test_lowlevel.py |
| `file__tests--test-packages-py` | code | tests/test_packages.py |
| `file__tests--test-requests-py` | code | tests/test_requests.py |
| `file__tests--test-structures-py` | code | tests/test_structures.py |
| `file__tests--test-testserver-py` | code | tests/test_testserver.py |
| `file__tests--test-utils-py` | code | tests/test_utils.py |
| `file__tests--utils-py` | code | tests/utils.py |
| `file__docs--static--custom-css` | code | docs/_static/custom.css |
| `file__docs--themes--license` | code | docs/_themes/LICENSE |
| `file__docs--themes--flask-theme-support-py` | code | docs/_themes/flask_theme_support.py |
| `file__docs--community--faq-rst` | code | docs/community/faq.rst |
| `file__docs--community--out-there-rst` | code | docs/community/out-there.rst |
| `file__docs--community--recommended-rst` | code | docs/community/recommended.rst |
| `file__docs--community--release-process-rst` | code | docs/community/release-process.rst |
| `file__docs--community--support-rst` | code | docs/community/support.rst |
| `file__docs--community--updates-rst` | code | docs/community/updates.rst |
| `file__docs--community--vulnerabilities-rst` | code | docs/community/vulnerabilities.rst |
| `file__docs--dev--authors-rst` | code | docs/dev/authors.rst |
| `file__docs--dev--contributing-rst` | code | docs/dev/contributing.rst |
| `file__docs--user--advanced-rst` | code | docs/user/advanced.rst |
| `file__docs--user--authentication-rst` | code | docs/user/authentication.rst |
| `file__docs--user--install-rst` | code | docs/user/install.rst |
| `file__docs--user--quickstart-rst` | code | docs/user/quickstart.rst |
| `file__src--requests--init-py` | code | src/requests/__init__.py |
| `file__src--requests--version-py` | code | src/requests/__version__.py |
| `file__src--requests--internal-utils-py` | code | src/requests/_internal_utils.py |
| `file__src--requests--types-py` | code | src/requests/_types.py |
| `file__src--requests--adapters-py` | code | src/requests/adapters.py |
| `file__src--requests--api-py` | code | src/requests/api.py |
| `file__src--requests--auth-py` | code | src/requests/auth.py |
| `file__src--requests--certs-py` | code | src/requests/certs.py |
| `file__src--requests--compat-py` | code | src/requests/compat.py |
| `file__src--requests--cookies-py` | code | src/requests/cookies.py |
| `file__src--requests--exceptions-py` | code | src/requests/exceptions.py |
| `file__src--requests--help-py` | code | src/requests/help.py |
| `file__src--requests--hooks-py` | code | src/requests/hooks.py |
| `file__src--requests--models-py` | code | src/requests/models.py |
| `file__src--requests--packages-py` | code | src/requests/packages.py |
| `file__src--requests--sessions-py` | code | src/requests/sessions.py |
| `file__src--requests--status-codes-py` | code | src/requests/status_codes.py |
| `file__src--requests--structures-py` | code | src/requests/structures.py |
| `file__src--requests--utils-py` | code | src/requests/utils.py |
| `file__tests--testserver--server-py` | code | tests/testserver/server.py |
| `file__tests--certs--expired--makefile` | code | tests/certs/expired/Makefile |
| `file__tests--certs--mtls--makefile` | code | tests/certs/mtls/Makefile |
| `file__tests--certs--expired--ca--makefile` | code | tests/certs/expired/ca/Makefile |
| `file__tests--certs--expired--server--makefile` | code | tests/certs/expired/server/Makefile |
| `file__tests--certs--mtls--client--makefile` | code | tests/certs/mtls/client/Makefile |
| `file__tests--certs--valid--server--makefile` | code | tests/certs/valid/server/Makefile |

## Reading the pack

```bash
cat agent-pack.json                 # what's in this pack
cat site.json | python -m json.tool # page index + frontier
cat pages/repo__000__tree.md
cat api/apis.json                   # every discovered interface
```

- `pages/<page_id>.md` — human/agent-readable view of each page
- `pages/<page_id>.json` — structured manifest (content, links, forms, provenance)



## Interfaces and actions

No machine interfaces were discovered; use page content in `pages/`.

## Common workflows

1. **Answer a question about the site**: search markdown views (`grep -ril '<keyword>' pages/`), read the matching `pages/<id>.md`.
2. **Inspect a specific page**: `cat pages/<page_id>.json` for structure, links and forms with provenance.
3. **Call an interface**: pick an entry from `api/apis.json`, then use the documented method + URL (verify with the site's terms first).

## For AI Agents

- Prefer `pages/*.md` for reading; switch to `pages/*.json` when you need structure.
- Never invent endpoints: only those in `api/apis.json` are evidenced.
- Cross-check important claims against `html/` evidence when present.
- `site.json` → `frontier` lists what exists but was NOT captured.
- Respect the site's robots.txt and terms of service for live calls.

## Caveats

- Captured 2026-07-11T00:00:00Z; content may have changed since.
- Page budget was None; 0 known URL(s) were left uncaptured.
- Generated without an LLM (deterministic mode): descriptions are terse; regenerate with an OPENROUTER_API_KEY for richer guidance.
