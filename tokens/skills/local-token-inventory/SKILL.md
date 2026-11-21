---
name: local-token-inventory
description: Set up or review the Local Token Inventory Python app for local Claude Code, Codex and Cursor counters, with explicit data-sharing scope. Use for this app's installation, usage summaries and interval attribution reviews; not provider account access or billing claims.
---

Start the installed app with `token-inventory` or `python -m tokens.inventory`. It binds to the printed loopback address and reads no counter files until connected. To explore without private records, use `--demo`.

The Python app and CLI make no external requests. Your coding agent may use a hosted model: any paths, usage, project names or transcript text returned into this conversation can go to that model provider. Before CLI discovery, scan, summary, review or transcript access, explain that boundary and obtain the user's permission for the specific data scope. Starting the server or synthetic demo needs no private-data permission. Prefer browser-only connection when the user wants the data to stay entirely on their machine.

## Setup

Install the supplied wheel with `python -m pip install ./local_token_inventory-0.1.2-py3-none-any.whl`, or install a clean source directory with `python -m pip install .`. Python 3.10+ is required; the runtime has no third-party dependencies. Do not install, sign in to or copy credentials from a coding-agent client as part of setup.

Open the printed address. Let the user choose Claude Code, Codex and/or Cursor and connect the desired local directories. Counter permission, structural metadata suggestions, optional folder hints and per-session transcript text are distinct controls. Cursor has no token counters in its agent transcripts. Offer `python -m tokens.cursor_hook --install` only after the user agrees to a local stop hook; it appends counters to `~/.cursor/usage-ledger/turns.jsonl` and does not read transcripts or call Cursor. Cloud-only history, subagent tokens and deleted records stay absent. Missing compatible records do not prove no usage.

For Python library use, `read_usage(roots)` defaults to counters alone (`attribute=False`), with Unknown project/activity labels and hidden folder basenames. Only pass `attribute=True` after permission for structural attribution and folder basenames.

## Consented review

The agent CLI only accepts an HTTP loopback address. For a non-default port, pass `--url` with the printed address.

- `token-inventory-agent discover`: directory discovery only; returned paths can still be private.
- `token-inventory-agent scan --allow-counters --allow-attribution --harness 'Claude Code' --harness Codex --harness Cursor`: read explicitly chosen counters and structural metadata. Omit `--allow-attribution` for counters alone. Optional folder hints require `--allow-folders`. Omit `--harness Cursor` unless the user has installed the local ledger hook and agreed to include it.
- `token-inventory-agent summary --allow-summary`: aggregate counters for all connected records. Inspect the source scope and coverage limits.
- `token-inventory-agent review --allow-summary`: uncertain intervals. Use returned row IDs, never filesystem paths.
- `token-inventory-agent assign --allow-assignment --row-id <actual-id> --project '<chosen-project>' --category 'Project work'`: change only that interval's reviewed metadata. Valid categories: Project work, Admin, Agent-to-agent, Unknown, Mixed. Keep uncertainty when evidence is insufficient. A relay can still belong to the project it supports.

Do not equate token volume with waste, output quality or money paid. Rates are optional caller-supplied flat estimates. Unknown model prices remain unknown. No exact token causality or cross-file duplicate elimination is promised.

For a plain-text agent response, the user can preview and prepare a summary in the browser. Read it with `token-inventory-agent context --allow-summary`, then return a local text file with `token-inventory-agent reply --allow-reply --reply-file <file>`. Replies are displayed as text, not executed.

Transcript text requires a separate explicit grant for a selected already-scanned session: `token-inventory-agent transcript --allow-transcript --session <actual-id>`. Masking is best effort; other sensitive text can remain. Never treat counter permission as transcript or upload permission.

Use `token-inventory-agent revoke --allow-revoke` or the browser privacy action to clear current server rows and grants. A restart also clears them. Browser review choices persist separately until forgotten. No source records are modified.
