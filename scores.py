"""Reading, checking and labelling the score submissions this repository collects.

The playground notebook in `aihpi/workshop-rag` opens one issue per attempt. This
module is the other half: it reads those issues back, checks each one against the
template the notebook writes, and applies the `session-YYYY-MM-DD` label that makes
a session count.

    uv run marimo run instructor.py

Reads work without any credentials, only more slowly. Every write needs `gh` logged
in as someone with triage rights here, so a stranger who clones this repository and
runs it gets a 403 rather than a labelled session. No credential belongs in this
file, or in any other file of this repository.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from datetime import datetime
from io import BytesIO
from typing import Any
from urllib.error import URLError

SCORES_REPO = 'aihpi/workshop-rag-scores'
API = 'https://api.github.com'
SESSION_PREFIX = 'session-'
SCORE_LABEL = 'score'

#: the grid the playground scores against, read straight from the workshop repository so the
#: `best known` line stays right as new configurations are measured
GRID_URL = ('https://raw.githubusercontent.com/aihpi/workshop-rag/main/'
            'notebooks/data/grid/grid_scores.parquet')

#: exactly what the notebook writes; anything else in a body means the issue was not opened by it
TEMPLATE_KEYS = ('handle', 'try', 'config', 'recall_at_5', 'mrr', 'ndcg_at_5', 'evaluations_used')
METRIC_KEYS = ('recall_at_5', 'mrr', 'ndcg_at_5')
HANDLE_RE = re.compile(r'^[a-z]+-[a-z]+-\d{2}$')
BUDGET = 8  # evaluations per round, as the playground enforces


# --- transport ---------------------------------------------------------------

def _gh(args: list[str]) -> subprocess.CompletedProcess | None:
    """Run `gh`, or None when it is not installed. A failed call still comes back for its stderr."""
    try:
        return subprocess.run(['gh', *args], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None


def _get(path: str) -> Any:
    """GitHub REST through `gh` when it is authenticated (5 000 requests an hour), else plain HTTP (60)."""
    done = _gh(['api', path])
    if done is not None and done.returncode == 0:
        try:
            return json.loads(done.stdout)
        except json.JSONDecodeError:
            pass
    request = urllib.request.Request(f'{API}/{path}', headers={'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


# --- the payload -------------------------------------------------------------

def decode_body(body: str) -> dict[str, str]:
    """The `key: value` lines of a submission, ignoring anything a participant typed around them."""
    out = {}
    for line in (body or '').splitlines():
        key, sep, value = line.partition(':')
        if sep and key.strip() and ' ' not in key.strip():
            out[key.strip()] = value.strip()
    return out


def check_submission(row: dict[str, str], known_configs: set[str] | None = None) -> list[str]:
    """Everything about a submission that does not match the template, as plain sentences.

    Submissions are expected to look exactly as the notebook writes them. An issue anyone can open
    is an issue anyone can write by hand, so the instructor is shown what deviates instead of the
    tool quietly trusting it or quietly dropping it.
    """
    problems = []

    missing = [key for key in TEMPLATE_KEYS if key not in row]
    if missing:
        problems.append(f"missing {', '.join(missing)}")
    unexpected = [key for key in row if key not in TEMPLATE_KEYS]
    if unexpected:
        problems.append(f"unexpected {', '.join(sorted(unexpected))}")

    handle = row.get('handle')
    if handle is not None and not HANDLE_RE.match(handle):
        problems.append(f'handle {handle!r} is not an adjective-animal-NN name')

    attempt = row.get('try')
    if attempt is not None and attempt not in ('1', '2'):
        problems.append(f'try {attempt!r} is neither 1 nor 2')

    for key in METRIC_KEYS:
        if key not in row:
            continue
        try:
            value = float(row[key])
        except ValueError:
            problems.append(f'{key} {row[key]!r} is not a number')
            continue
        if not 0.0 <= value <= 1.0:
            problems.append(f'{key} {value} is outside 0 to 1')

    used = row.get('evaluations_used')
    if used is not None:
        try:
            count = int(used)
        except ValueError:
            problems.append(f'evaluations_used {used!r} is not a whole number')
        else:
            if not 1 <= count <= BUDGET:
                problems.append(f'evaluations_used {count} is outside 1 to {BUDGET}')

    config = row.get('config')
    if config is not None and known_configs and config not in known_configs:
        problems.append(f'config {config!r} was never measured')

    return problems


def by_handle(submissions: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    """Recall@5 per handle and round, keeping the participants who only sent one of the two."""
    out: dict[str, dict[str, float]] = {}
    for row in submissions:
        handle, attempt = row.get('handle'), row.get('try')
        if not handle or attempt not in ('1', '2'):
            continue
        try:
            out.setdefault(handle, {})[attempt] = float(row['recall_at_5'])
        except (KeyError, ValueError):
            continue
    return dict(sorted(out.items()))


def pair_tries(submissions: list[dict[str, str]]) -> list[dict[str, Any]]:
    """One row per handle with its first and second try, dropping anything unpaired."""
    return [{'handle': handle, 'first': tries['1'], 'second': tries['2']}
            for handle, tries in by_handle(submissions).items()
            if '1' in tries and '2' in tries]


def today_label() -> str:
    """The label that confirms today's submissions."""
    return f'{SESSION_PREFIX}{datetime.now().astimezone().date().isoformat()}'


# --- reading -----------------------------------------------------------------

def fetch_scores(repo: str = SCORES_REPO) -> list[dict[str, Any]]:
    """Every score submission, labelled or not, newest first."""
    issues = _get(f'repos/{repo}/issues?labels={SCORE_LABEL}&state=all&per_page=100')
    out = []
    for issue in issues:
        if 'pull_request' in issue:  # a pull request is not a submission
            continue
        labels = [lab['name'] for lab in issue.get('labels', [])]
        out.append({
            'number': issue['number'],
            'title': issue.get('title', ''),
            'author': (issue.get('user') or {}).get('login', ''),
            'created_at': issue.get('created_at', '')[:10],
            'sessions': [lab for lab in labels if lab.startswith(SESSION_PREFIX)],
            'body': decode_body(issue.get('body', '')),
        })
    return out


def open_pulls(repo: str = SCORES_REPO) -> list[dict[str, Any]]:
    """Open pull requests, which is someone trying to change this repository rather than score in it."""
    pulls = _get(f'repos/{repo}/pulls?state=open&per_page=100')
    return [{'number': p['number'], 'title': p.get('title', ''),
             'author': (p.get('user') or {}).get('login', '')} for p in pulls]


def session_labels(repo: str = SCORES_REPO) -> list[str]:
    """Every confirmed session, newest first."""
    labels = [lab['name'] for lab in _get(f'repos/{repo}/labels?per_page=100')]
    return sorted((lab for lab in labels if lab.startswith(SESSION_PREFIX)), reverse=True)


def fetch_session(label: str, repo: str = SCORES_REPO) -> list[dict[str, str]]:
    """The decoded submissions of one confirmed session."""
    issues = _get(f'repos/{repo}/issues?labels={label}&state=all&per_page=100')
    return [decode_body(issue.get('body', '')) for issue in issues if 'pull_request' not in issue]


def best_known(url: str = GRID_URL) -> tuple[float, set[str]]:
    """The best measured Recall@5 and every measured configuration id, from the workshop repository.

    Read over HTTP rather than vendored, because the grid grows and a stale copy would draw the
    room's reference line in the wrong place.
    """
    import pandas as pd

    request = urllib.request.Request(url, headers={'Accept': 'application/octet-stream'})
    with urllib.request.urlopen(request, timeout=30) as response:
        grid = pd.read_parquet(BytesIO(response.read()))
    return float(grid['Recall@5'].max()), set(grid['config_id'])


# --- writing, which needs `gh` -----------------------------------------------

class NotAuthenticated(RuntimeError):
    """`gh` is missing or not logged in, so nothing can be labelled."""


def _require_gh() -> None:
    done = _gh(['auth', 'status'])
    if done is None:
        raise NotAuthenticated('gh is not installed. See https://cli.github.com/')
    if done.returncode != 0:
        raise NotAuthenticated('gh is not logged in. Run `gh auth login`.')


def ensure_label(name: str, repo: str = SCORES_REPO, description: str = '') -> str:
    """Create the session label, or report that it was already there. Needs triage rights."""
    _require_gh()
    if name in session_labels(repo):
        return f'{name} already exists'
    done = _gh(['api', '-X', 'POST', f'repos/{repo}/labels',
                '-f', f'name={name}', '-f', 'color=0E8A16',
                '-f', f'description={description or "Confirmed workshop session"}'])
    if done is None or done.returncode != 0:
        raise NotAuthenticated(f'could not create {name}: {(done.stderr if done else "").strip()}')
    return f'created {name}'


def apply_label(numbers: list[int], label: str, repo: str = SCORES_REPO) -> list[str]:
    """Add the label to each issue, one line back per issue so a partial failure stays visible.

    Through `gh issue edit` rather than the REST endpoint, because the endpoint wants a JSON array
    and `gh api -f` can only send strings.
    """
    _require_gh()
    out = []
    for number in numbers:
        done = _gh(['issue', 'edit', str(number), '--repo', repo, '--add-label', label])
        ok = done is not None and done.returncode == 0
        out.append(f'#{number} labelled' if ok
                   else f'#{number} failed: {(done.stderr if done else "gh missing").strip()}')
    return out


def is_reachable() -> bool:
    """Whether GitHub answers at all, so the notebook can say so instead of showing a traceback."""
    try:
        _get('rate_limit')
    except (URLError, OSError, json.JSONDecodeError):
        return False
    return True
