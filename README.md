# Local Token Inventory

See what your coding-agent usage supported. Project identity stays separate from agent communication and other activity. Review uncertain intervals without changing their recorded counters.

The public demo contains entirely invented projects, counters, model names and rates. It has no connection to anyone's private dashboard. Your installed app runs on your own machine; no account or API key is required by the inventory.

Public companion: https://github.com/Morkeeth/where-did-the-tokens-go-public

The repository and release publication are separate from the private local app. No package-index publication is required.

## Run privately

Requires Python 3.10 or newer and a browser. The runtime has no third-party Python dependencies.

From the source ZIP, open a terminal in its extracted directory:

```sh
python3 -m tokens.inventory --demo
```

Open the printed loopback address. This mode uses only synthetic counters and invented illustrative rates. Stop with Ctrl-C.

For your own usage, restart without `--demo`:

```sh
python3 -m tokens.inventory
```

No counter files are read on startup. In the browser, select Claude Code and/or Codex and explicitly connect the local record folders. Structural metadata suggestions and visible folder hints have separate controls. Transcript permission is separate again and scoped to one selected session. Revoking access clears the running server's rows, scan grants and agent exchange; it does not delete source records. Browser review choices persist until forgotten.

Default JSONL roots are `~/.claude/projects`, `~/.codex/sessions` and `~/.codex/archived_sessions`. Override them in the browser or with `--claude PATH` and repeatable `--codex PATH`. An empty or missing compatible root does not establish no usage. This app does not install or sign in to either client. Cursor counters, provider billing, cloud-only sessions and deleted records are unsupported.

## Install the Python library and CLI

Install the supplied wheel, or a clean source checkout:

```sh
python3 -m pip install ./local_token_inventory-0.1.0-py3-none-any.whl
# Or, in the source directory:
python3 -m pip install .
token-inventory --demo
```

These commands use local artifacts; this candidate does not claim a published package-index release. The console commands are `token-inventory` and `token-inventory-agent`.

For programmatic use, a caller explicitly chooses the directories to read:

```python
from tokens.inventory import read_usage
from tokens.pricing import estimate_usage

usage = read_usage([("Claude Code", "/absolute/path/to/chosen/jsonl-root")], attribute=False)
# Structural metadata is optional: pass attribute=True only for that scope.
estimated = estimate_usage(usage, rates={})  # No configured model prices: unknown.
```

Library calls do not open a browser, scan by themselves on import, contact a provider or execute recorded commands. They read the roots supplied by the caller when invoked. Counter results exclude prompt/reply prose. For compatibility, the library defaults to structural attribution and returns folder basenames; pass attribute=False to disable attribution. The browser and CLI hide folder hints unless separately allowed. Project metadata and folder basenames may themselves be sensitive.

## Pricing

API-equivalent estimates are not invoices or subscriptions. No prices are downloaded. Unknown model rates remain unknown; a partially priced view shows a known-rate subtotal.

Supply a local JSON file mapping exact model names to flat USD rates per million tokens:

```json
{
  "Your configured model": {"input": 1.0, "output": 4.0, "cache_read": 0.2, "cache_write": 1.2}
}
```

Those numbers are a format example, not a provider price list. Run `token-inventory --prices /path/to/your-rates.json`. Long-context tiers, discounts and billing adjustments are not modeled. The synthetic demo's rates are fictional.

## Use a coding agent

The CLI starts no model and makes only HTTP loopback requests, bypassing network proxies. It exposes no shell or model invocation through returned replies. Local permissions are explicit:

```sh
token-inventory-agent discover
token-inventory-agent scan --allow-counters --allow-attribution --harness 'Claude Code' --harness Codex
token-inventory-agent summary --allow-summary
token-inventory-agent review --allow-summary
```

Use `--url http://127.0.0.1:PORT` for the actual printed port. Discovery returns configured paths. Scan/review results can include project identities and hashed session IDs. Summaries omit paths, IDs and transcripts, but project names can still be private.

**If your coding agent uses a hosted model, results brought into that conversation go to its provider.** Inspect locally first and grant that handoff explicitly. The Python app does not make that provider connection for you. Counter or summary permission does not grant transcript or publication permission.

For interval correction, use an actual `row_id` returned by review:

```sh
token-inventory-agent assign --allow-assignment --row-id <actual-row-id> --project '<chosen-project>' --category 'Project work'
```

Categories are Project work, Admin, Agent-to-agent, Unknown and Mixed. A correction applies only to the selected counter interval and leaves counters intact. Project identity and work category are independent heuristic axes. Mixed and parent-derived assignments stay reviewable. Prompt/reply prose is not used for automatic attribution.

The browser's Local agent view can preview a summary and prepare it for a local agent. Read that approved context with `token-inventory-agent context --allow-summary`; return a plain-text file with `token-inventory-agent reply --allow-reply --reply-file review.txt`. No reply is executed.

Transcript preview requires separate consent for an already-scanned session: `token-inventory-agent transcript --allow-transcript --session <actual-session-id>`. Common keys, emails and local paths are masked; other sensitive text can remain. Tool outputs, images and audio are omitted. Inspect before sharing. Revoke with `token-inventory-agent revoke --allow-revoke` or the browser action.

## Packaged skill

Run `token-inventory --show-skill` to locate the installed `SKILL.md`. Copy its `local-token-inventory` folder into a skill directory your agent is configured to read. A separate skill ZIP is also provided. The skill explains the local-data and hosted-model boundary before requesting private data. It does not configure a client or authorize uploads.

The CLI can be used by any local tool-capable client. This package includes no MCP server, provider plugin, credential bridge or automatic account connection; those integrations are not claimed.

## Measurement limits and privacy

Claude streaming message counters use positive per-message updates. Codex cumulative counters are differenced per file; cached input is subtracted before counting uncached input. Counter resets begin new segments. Copies across files can duplicate usage. Attribution uses recorded metadata intervals, not fractional allocations or exact project causality. Tokens do not establish useful output, efficiency or money paid.

The app binds to `127.0.0.1`, checks the Host header, requires a page capability for counter/agent actions, serves no arbitrary files, and has no analytics or external assets. It is a local single-user tool, not an authenticated multi-user service. Do not expose it through a tunnel, public reverse proxy or shared host.

The static demo uses embedded synthetic data with browser-side interactions and a restrictive no-connect policy. It cannot read local files or contact a private inventory. Review edits in that demo stay in that browser's storage.

## Build and verify

With Python build tools available, run `python3 tools/build_release.py /path/to/output`. It creates a wheel, source distribution, source ZIP, skill ZIP and a static synthetic demo. Release files are built from an explicit source allowlist. Local data, credentials, build intermediates, private configuration, screenshots and Git history are excluded.

Run `python3 -m unittest discover -s tests`. The release audit scans source, every file in archives, static output and all Git revisions. Such a scan supports the clean-source provenance; keyword matching alone cannot prove that arbitrary data is synthetic.
