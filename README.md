# Local Token Inventory

## TLDR

Review local coding-agent usage by project and inspect uncertain attribution.<br>
For people who want a private account of their own recorded agent work.<br>
Start with the synthetic public demo; private setup reads only the sources you choose.

## The problem and approach

The problem: coding agents write usage records to folders on your disk, and nothing turns them into a per-project picture you can review.

It reads the local JSONL records those clients already keep, asks for consent per source, lets you review uncertain intervals, and estimates a cost only once you give it model rates.

No account, no API key, no third-party dependency, and the running app makes no external requests. Try the synthetic demo first: https://morkeeth.github.io/where-did-the-tokens-go-public/

## Review and pick up the work

[Agent guide](AGENTS.md)

Start with the linked source, setup and evidence. Recorded demos and sample data keep their original scope; use the repository instructions for a fresh run.

A private, playful view of what your coding-agent usage supported. See projects, review uncertain work and keep agent communication attached to the project it serves.

[Try the synthetic mock-up](https://morkeeth.github.io/where-did-the-tokens-go-public/) · [Download packages](https://morkeeth.github.io/where-did-the-tokens-go-public/packages.html)

**The public demo is a synthetic mock-up.** Every project, counter, model name and rate is invented. It shows how your own private usage view could look; it does not connect to your computer or import your records. To see your own usage, install the local app below.

**The Python library is already available.** The downloadable wheel contains the library, browser app, two CLI commands and setup skill. Install that wheel directly; this project does not claim a PyPI package. No inventory account, API key or third-party runtime dependency is required.

## Start here: macOS or Linux

You need Python **3.10 or newer**, its `venv`/`pip` support, a terminal and a browser. Check `python3 --version` first. If Python is missing, install a current version from [python.org](https://www.python.org/downloads/). On Debian/Ubuntu, a missing `venv` or `ensurepip` message usually means you need the distribution's `python3-venv` package. The app does not install or sign in to Claude Code or Codex for you.

Verification: the fresh-home wheel install, demo and private consent path were exercised on macOS. Ubuntu CI has exercised the source tests and release build; this onboarding pass has not independently run the fresh-install commands on Linux. Windows/WSL remain unverified.

### 1. Install the existing wheel

Run these commands in a new terminal directory. No Git checkout or build tools are needed:

```sh
mkdir token-inventory
cd token-inventory
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps https://morkeeth.github.io/where-did-the-tokens-go-public/downloads/local_token_inventory-0.1.0-py3-none-any.whl
.venv/bin/token-inventory --demo
```

The download needs internet access; the running app makes no external requests. Open **http://127.0.0.1:58631/** and click **Explore example**. You should see invented projects and a blue API-price estimate. Those rates are fictional, not your bill. The terminal stays running while you use the page. Stop it with **Ctrl-C**.

If port 58631 is busy, append `--port 58632` and open http://127.0.0.1:58632/ instead. Keep the app on this machine; do not expose it through a tunnel or public host.

### 2. Connect your own records privately

In the same directory, start again without `--demo`:

```sh
.venv/bin/token-inventory
```

1. Open the printed loopback address. No usage records have been read yet.
2. Expand **Sources and privacy**. Select Claude Code and/or Codex, and check the record-folder paths. Unselect clients you do not use. Default roots are `~/.claude/projects`, `~/.codex/sessions` and `~/.codex/archived_sessions`.
3. For counters alone, uncheck **Use structural metadata**. Enable it only if you want local project/activity suggestions. Folder hints are a separate optional control; project names can still reveal private information.
4. Click **Connect local counters**. The overview now describes the selected records. Without configured model rates, the dollar estimate stays unknown; token counters still work.
5. Use **Review** to correct uncertain intervals. Reading one session's transcript needs separate permission. **Connections & privacy** revokes the current connection; **Forget browser review choices** removes separately saved browser choices.

The app reads existing compatible local JSONL records, not provider billing or cloud/deleted history. If a source is missing, use that client normally in a project, then recheck its actual record folder. An empty view is not proof of no usage. Cursor counters are unsupported. You can override folders in the browser or with `--claude PATH` and repeatable `--codex PATH`.

Stop with Ctrl-C. To return later, `cd token-inventory` from its parent directory and run `.venv/bin/token-inventory` again. Source records are never modified. Server rows and grants clear on exit; browser review choices remain until forgotten.

### Other ways to start

**Prefer a GitHub checkout?** These commands run the same app directly from public source, with no installation or runtime dependencies:

```sh
git clone https://github.com/Morkeeth/where-did-the-tokens-go-public.git
cd where-did-the-tokens-go-public
python3 -m tokens.inventory --demo
```

Stop with Ctrl-C, then run `python3 -m tokens.inventory` to follow the private connection steps above. The source ZIP works the same way after extraction.

**Already downloaded the wheel?** In the virtual environment above, replace the URL installation command with:

```sh
.venv/bin/python -m pip install --no-deps ./local_token_inventory-0.1.0-py3-none-any.whl
```

The wheel file must be in the current directory, or use its actual path. Building from source is covered at the end of this README.

### Windows PowerShell: not yet verified on Windows

Use an installed Python 3.10+ and the Python launcher. These commands avoid activation-script policy changes. They are provided as Windows syntax guidance, not a tested Windows compatibility claim:

```powershell
mkdir token-inventory
cd token-inventory
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-deps https://morkeeth.github.io/where-did-the-tokens-go-public/downloads/local_token_inventory-0.1.0-py3-none-any.whl
.\.venv\Scripts\token-inventory.exe --demo
```

Open the printed address, explore the synthetic example, then stop with Ctrl-C. For private use run `.\.venv\Scripts\token-inventory.exe` without `--demo`, and choose the actual local JSONL directories in Sources and privacy. WSL uses the Linux commands; records stored on Windows may need an explicit mounted path. Windows and WSL have not been exercised in this onboarding pass.

## Use the Python library

Installing the wheel makes `tokens` importable by that environment's Python from any directory. The app is one view over the same library, not a required hosted service:

```python
from pathlib import Path
from tokens.inventory import read_usage
from tokens.pricing import estimate_usage

# Invoke only after choosing and permitting this local record directory.
root = Path.home() / ".claude" / "projects"
usage = read_usage([("Claude Code", str(root))])
estimated = estimate_usage(usage, rates={})  # No model prices configured: unknown.
```

The library does nothing on import. Calling `read_usage` reads the supplied roots. Prompt/reply prose is excluded in both modes. With the default `attribute=False`, project/activity labels stay Unknown and folder basenames are hidden. Returned metadata still includes model names, dates, interval timestamps, counters, hashed session IDs and evidence strings, plus an issues count; inspect before sharing. It starts no server or model and executes no recorded commands.

Only with permission for that extra scope, pass `attribute=True` for structural attribution. It uses recorded repository/cwd fields and tool names and can return project/folder basenames and tool names. For an absolute recorded cwd it checks `.git` existence there and up to eight ancestors, possibly outside the chosen log roots. It reads no project-tree files or `.git` contents. Browser and CLI folder hints remain separately controlled.

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

## Optional companion: Transcripto

[Transcripto](https://github.com/Morkeeth/transcripto) is a separate tool for finding a remembered request and replaying its recorded work. Inventory answers “where did the recorded tokens go?”; replay can help inspect “what was requested and what result was recorded?” Its public README describes local search/replay and separately opt-in remote model features.

**Proposed addition, not implemented:** a user-selected inventory interval could open a matching local Transcripto replay after separate transcript consent. This would need an explicit source/line mapping; the inventory's hashed session IDs alone do not establish that link. Preserve unknown results and let the user inspect evidence before changing attribution. Do not install Transcripto, index transcripts, start a model or share content as part of this setup. The inventory remains usable on its own.

## Measurement limits and privacy

Claude streaming message counters use positive per-message updates. Codex cumulative counters are differenced per file; cached input is subtracted before counting uncached input. Counter resets begin new segments. Copies across files can duplicate usage. Attribution uses recorded metadata intervals, not fractional allocations or exact project causality. Tokens do not establish useful output, efficiency or money paid.

The app binds to `127.0.0.1`, checks the Host header, requires a page capability for counter/agent actions, serves no arbitrary files, and has no analytics or external assets. It is a local single-user tool, not an authenticated multi-user service. Do not expose it through a tunnel, public reverse proxy or shared host.

The static demo uses embedded synthetic data with browser-side interactions and a restrictive no-connect policy. It cannot read local files or contact a private inventory. Review edits in that demo stay in that browser's storage.

## Build and verify

Create an isolated build environment and install the build-only prerequisites (`setuptools>=77`, `packaging>=24.2` and `wheel`):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'setuptools>=77' 'packaging>=24.2' wheel
.venv/bin/python tools/build_release.py /path/to/output
```

These tools are only needed to build releases; the installed app still has no third-party runtime dependencies. It creates a wheel, source distribution, source ZIP, skill ZIP and a static synthetic demo. Release files are built from an explicit source allowlist. Local data, credentials, build intermediates, private configuration, screenshots and Git history are excluded.

Run `python3 -m unittest discover -s tests`. Run `python3 tools/audit_release.py /path/to/output` to scan source, every file in archives and static output, including from an extracted source ZIP or plain folder. Add `--history` only in a Git checkout to scan all Git revisions; extracted archives have no history and this option fails with an explicit error. Such a scan supports the clean-source provenance; keyword matching alone cannot prove that arbitrary data is synthetic.

## License and data boundaries

Code terms: [LICENSE](LICENSE). Data, provider responses, media, fonts and other third-party assets may have separate terms. Repository access alone does not grant rights to those materials. 
