"""Best-effort key masking for a separately consented transcript preview.
Other sensitive text may remain; inspect locally before sharing.
"""
import re

KEY_SHAPES = re.compile(
    r'sk-[A-Za-z0-9_\-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9\-]{10,}'
    r'|AIza[0-9A-Za-z_\-]{30,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}'
    r'|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----')
KEY_ASSIGN = re.compile(r'(?i)((?:api[_-]?key|secret|token|password|passwd|bearer)["\']?\s*[:=]\s*["\']?)([A-Za-z0-9_\-+/=]{24,})')


def redact_keys(text):
    text = KEY_SHAPES.sub('[redacted: looks like a key]', text)
    return KEY_ASSIGN.sub(lambda m: m.group(1) + '[redacted: looks like a key]', text)


def label(exc):
    text = str(exc)
    return text if text.startswith('not shown') else 'not shown: ' + text
