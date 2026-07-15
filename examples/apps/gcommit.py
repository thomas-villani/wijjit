"""gcommit - an interactive git commit builder that lives in your scrollback.

A small, genuinely useful terminal tool built on Wijjit's *inline* mode
(:class:`~wijjit.InlineApp`): it renders in place - no alternate screen - so the
final summary stays in your terminal history like ordinary command output, and
it composes with the shell the way ``git`` does.

What it does
------------
1. Reads ``git status`` and lists every change as a checkbox (files with staged
   changes start checked, matching git's mental model of "ready to commit").
2. You toggle which files to include and type a commit message.
3. On Ctrl+Q it builds an exact, WYSIWYG commit: ``git add`` the checked files,
   then ``git commit`` limited to those same paths - so nothing you left
   unchecked sneaks in, even if it was already staged.

Safety
------
Because this ships as a runnable example, it is **dry-run by default**: it prints
the precise commands it *would* run and leaves your repository untouched. Pass
``--run`` to actually stage and commit. Either way the result stays in
scrollback.

Usage
-----
    python examples/apps/gcommit.py           # preview the commands (safe)
    python examples/apps/gcommit.py --run      # actually stage + commit

Controls
--------
- Tab / Shift+Tab: move between the file checkboxes and the message box
- Space: stage / unstage the focused file
- Type in the message box (Enter inserts a newline)
- Ctrl+Q: finish (an empty message or no files selected cancels)
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from dataclasses import dataclass

from wijjit import InlineApp


@dataclass
class Change:
    """One entry from ``git status --porcelain``.

    Attributes
    ----------
    code : str
        The two-character status code (e.g. ``" M"``, ``"A "``, ``"??"``).
    path : str
        The working-tree path the change applies to.
    staged : bool
        True when the index column shows a change (the file is already staged).
    """

    code: str
    path: str
    staged: bool


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command and capture its output.

    Parameters
    ----------
    *args : str
        Arguments passed after ``git`` (e.g. ``"status", "--porcelain"``).

    Returns
    -------
    subprocess.CompletedProcess[str]
        The completed process with captured ``stdout``/``stderr``.
    """
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def parse_status(porcelain: str) -> list[Change]:
    """Parse ``git status --porcelain`` output into Change entries.

    Parameters
    ----------
    porcelain : str
        Raw output of ``git status --porcelain``.

    Returns
    -------
    list[Change]
        One entry per changed path (renames resolve to their new path).
    """
    changes: list[Change] = []
    for line in porcelain.splitlines():
        if len(line) < 4:
            continue
        code, rest = line[:2], line[3:]
        # Renames/copies are reported as "old -> new"; commit the new path.
        path = rest.split(" -> ", 1)[-1].strip()
        # Untracked ("??") is not staged; otherwise a non-space index column
        # (the first character) means the change is already staged.
        staged = code[0] not in (" ", "?")
        changes.append(Change(code=code, path=path, staged=staged))
    return changes


def build_commit_commands(paths: list[str], message: str) -> list[list[str]]:
    """Build the git commands that stage and commit exactly ``paths``.

    Both commands are limited to the given pathspec so that only the selected
    files are committed - anything left unchecked stays out of the commit even
    if it was already staged.

    Parameters
    ----------
    paths : list[str]
        The working-tree paths to include.
    message : str
        The commit message.

    Returns
    -------
    list[list[str]]
        The argv lists to run in order (``git add ...`` then ``git commit ...``).
    """
    return [
        ["git", "add", "--", *paths],
        ["git", "commit", "-m", message, "--", *paths],
    ]


def current_branch() -> str:
    """Return the current branch name (or a short label if detached)."""
    result = run_git("rev-parse", "--abbrev-ref", "HEAD")
    branch = result.stdout.strip()
    return branch if branch and branch != "HEAD" else "(detached HEAD)"


TEMPLATE = """
{% frame title=state.header border="rounded" width="fill" %}
  {% vstack spacing=1 padding=1 %}

    {% text %}{{ state.changes | length }} changed file(s). Space to stage/unstage, Tab to move.{% endtext %}

    {% frame title="Changes" border="single" %}
      {% vstack spacing=0 %}
        {% for change in state.changes %}
          {% checkbox id="file_" ~ loop.index0 checked=change.staged %}[{{ change.code }}] {{ change.path }}{% endcheckbox %}
        {% endfor %}
      {% endvstack %}
    {% endframe %}

    {% text %}Commit message:{% endtext %}
    {% textarea id="message" value=state.message width="fill" height=4 wrap_mode="soft" %}{% endtextarea %}

    {% text %}Ctrl+Q: finish and commit  -  an empty message cancels{% endtext %}

  {% endvstack %}
{% endframe %}
"""


async def run_gcommit(changes: list[Change], header: str) -> tuple[list[str], str]:
    """Drive the inline UI and return the user's selection.

    Parameters
    ----------
    changes : list[Change]
        The changes to present as checkboxes.
    header : str
        The frame title (repo/branch context).

    Returns
    -------
    tuple[list[str], str]
        ``(selected_paths, message)`` after the user presses Ctrl+Q.
    """
    initial_state: dict[str, object] = {
        "header": header,
        "changes": changes,
        "message": "",
    }
    # Seed each checkbox's bound state so already-staged files start checked.
    for index, change in enumerate(changes):
        initial_state[f"file_{index}"] = change.staged

    async with InlineApp(
        TEMPLATE,
        enable_input=True,
        quit_key="ctrl+q",
        initial_state=initial_state,
    ) as app:
        await app.wait()

        selected = [
            change.path
            for index, change in enumerate(changes)
            if app.state.get(f"file_{index}")
        ]
        message = str(app.state.get("message", "")).strip()

    return selected, message


def _format_command(argv: list[str]) -> str:
    """Render an argv list as a copy-pasteable shell command."""
    parts = []
    for arg in argv:
        parts.append(f'"{arg}"' if (" " in arg or not arg) else arg)
    return " ".join(parts)


def main() -> int:
    """Entry point: gather changes, run the UI, then preview or execute."""
    execute = "--run" in sys.argv[1:]

    status = run_git("status", "--porcelain")
    if status.returncode != 0:
        message = status.stderr.strip() or "not a git repository"
        print(f"gcommit: {message}")
        return 1

    changes = parse_status(status.stdout)
    if not changes:
        print("gcommit: nothing to commit, working tree clean.")
        return 0

    header = f"gcommit  -  {current_branch()}"
    selected, message = asyncio.run(run_gcommit(changes, header))

    if not selected or not message:
        print("gcommit: cancelled (need at least one file and a message).")
        return 0

    commands = build_commit_commands(selected, message)

    if not execute:
        print(
            f"gcommit: would commit {len(selected)} file(s). Preview (--run to apply):"
        )
        for argv in commands:
            print(f"  {_format_command(argv)}")
        return 0

    for argv in commands:
        result = run_git(*argv[1:])
        output = (result.stdout + result.stderr).strip()
        if output:
            print(output)
        if result.returncode != 0:
            print(f"gcommit: '{_format_command(argv)}' failed.")
            return result.returncode

    print(f"gcommit: committed {len(selected)} file(s) on {current_branch()}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
