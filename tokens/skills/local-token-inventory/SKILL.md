---
name: local-token-inventory
description: Set up or review the Local Token Inventory Python app for local Claude Code and Codex JSONL counters, with explicit data-sharing scope. Use for this app's installation, usage summaries and interval attribution reviews; not provider account access or billing claims.
---

Start the installed app with `token-inventory` or `python -m tokens.inventory`. It binds to the printed loopback address and reads no counter files until connected. To explore without private records, use `--demo`.

The Python app and CLI make no external requests. Your coding agent may use a hosted model: any paths, usage, project names or transcript text returned into this conversation can go to that model provider. Before CLI discovery, scan, summary, review or transcript access, explain that boundary and obtain the user's permission for the specific data scope. Starting the server or synthetic demo needs no private-data permission. Prefer browser-only connection when the user wants the data to stay entirely on their machine.

## Setup

Install the supplied wheel with `python -m pip install ./local_token_inventory-0.1.0-py3-none-any.whl`, or install a clean source directory with `python -m pip install .`. Python 3.10+ is required; the runtime has no third-party dependencies. Do not install, sign in to or copy credentials from a coding-agent client as part of setup.

Open the printed address. Let the user choose Claude Code and/or Codex and connect the desired local JSONL directories. Counter permission, structural metadata suggestions, optional folder hints and per-session transcript text are distinct controls. Cursor counters, cloud-only history and deleted records are unsupported. Missing compatible records do not prove no usage.

## Consented review

The agent CLI only accepts an HTTP loopback address. For a non-default port, pass `--url` with the printed address.

- `token-inventory-agent discover`: directory discovery only; returned paths can still be private.
- `token-inventory-agent scan --allow-counters --allow-attribution --harness 'Claude Code' --harness Codex`: read explicitly chosen counters and structural metadata. Omit `--allow-attribution` for counters alone. Optional folder hints require `--allow-folders`.
- `token-inventory-agent summary --allow-summary`: aggregate counters for all connected records. Inspect the source scope and coverage limits.
- `token-inventory-agent review --allow-summary`: uncertain intervals. Use returned row IDs, never filesystem paths.
- `token-inventory-agent assign --allow-assignment --row-id <actual-id> --project '<chosen-project>' --category 'Project work'`: change only that interval's reviewed metadata. Valid categories: Project work, Admin, Agent-to-agent, Unknown, Mixed. Keep uncertainty when evidence is insufficient. A relay can still belong to the project it supports.

Do not equate token volume with waste, output quality or money paid. Rates are optional caller-supplied flat estimates. Unknown model prices remain unknown. No exact token causality or cross-file duplicate elimination is promised.

For a plain-text agent response, the user can preview and prepare a summary in the browser. Read it with `token-inventory-agent context --allow-summary`, then return a local text file with `token-inventory-agent reply --allow-reply --reply-file <file>`. Replies are displayed as text, not executed.

Transcript text requires a separate explicit grant for a selected already-scanned session: `token-inventory-agent transcript --allow-transcript --session <actual-id>`. Masking is best effort; other sensitive text can remain. Never treat counter permission as transcript or upload permission.

Use `token-inventory-agent revoke --allow-revoke` or the browser privacy action to clear current server rows and grants. A restart also clears them. Browser review choices persist separately until forgotten. No source records are modified.
