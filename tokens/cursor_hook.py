"""Cursor stop hook. Append one local counter line and never fail the turn.

Usage:
  python -m tokens.cursor_hook              # read a stop payload on stdin
  python -m tokens.cursor_hook --print      # show the hooks.json command
  python -m tokens.cursor_hook --install    # add that command to ~/.cursor/hooks.json
"""
import argparse
import json
import sys

from .cursor import DEFAULT_ROOT, append_turn, hook_command, install_user_hook, normalize_stop


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--print', action='store_true', help='Print the hook command and exit')
    parser.add_argument('--install', action='store_true', help='Add the stop hook to ~/.cursor/hooks.json')
    parser.add_argument('--ledger', default=DEFAULT_ROOT, help='Directory for the counters-only JSONL ledger')
    args = parser.parse_args(argv)
    if args.print or args.install:
        command = hook_command()
        if args.install:
            try:
                path = install_user_hook(Path_home(), command)
            except (OSError, ValueError, json.JSONDecodeError) as error:
                print('Cursor hook was not installed: ' + str(error), file=sys.stderr)
                return 1
            print('Cursor stop hook added in ' + str(path))
            print('Counters will append under ' + args.ledger + ' after the next agent turn.')
            return 0
        print(command)
        print('Add that command to the stop list in ~/.cursor/hooks.json, or rerun with --install.')
        print('It writes token counters only. It does not read transcripts or contact Cursor.')
        return 0
    try:
        raw = sys.stdin.buffer.read(1_000_001)
        if len(raw) <= 1_000_000:
            record = normalize_stop(json.loads(raw.decode()))
            if record is not None:
                append_turn(args.ledger, record)
    except Exception:
        pass
    sys.stdout.write('{}\n')
    return 0


def Path_home():
    from pathlib import Path
    return Path.home()


if __name__ == '__main__':
    sys.exit(main())
