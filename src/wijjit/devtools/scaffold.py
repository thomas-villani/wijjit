"""Project scaffolding for ``wijjit new``.

Generates a runnable starter app so the first minute with Wijjit is spent
reading working code rather than assembling it from documentation.

Two layouts:

``single`` (default)
    One file, ~60 lines, runnable immediately. Matches how the 74 bundled
    examples ship and how a small CLI tool actually starts life. Uses
    :func:`~wijjit.render_template_string`, so the whole app -- state, template,
    handlers -- reads top to bottom in one place.

``project``
    A directory with the template in its own ``templates/`` file, a headless
    harness test, and a ``pyproject.toml``. Costs more ceremony but teaches the
    file-based :func:`~wijjit.render_template` path and hands over a working
    test, which is the habit most worth seeding.

Every generated app is held to the same bar the docs tell users to apply: the
test suite runs ``wijjit validate`` over both layouts and drives them through
:class:`~wijjit.testing.WijjitHarness`. A scaffold that emits a mistake teaches
that mistake to every user who runs it.

Notes
-----
Templates here are substituted with :meth:`str.replace` over ``__TOKEN__``
placeholders rather than :meth:`str.format` or f-strings: the generated sources
are full of literal ``{% ... %}`` and ``{{ ... }}`` braces that ``format`` would
try to read as replacement fields.
"""

from __future__ import annotations

import keyword
import re
from pathlib import Path

#: Layout names accepted by ``wijjit new --template``.
LAYOUTS = ("single", "project")


class ScaffoldError(Exception):
    """Raised when a project cannot be generated.

    Carries a message intended to be shown to the user verbatim, without a
    traceback.
    """


def to_module_name(name: str) -> str:
    """Convert a project name to a valid Python module name.

    Parameters
    ----------
    name : str
        User-supplied project name, e.g. ``"My Tasks"`` or ``"task-list"``.

    Returns
    -------
    str
        A lowercase, underscore-separated identifier, e.g. ``"task_list"``.

    Raises
    ------
    ScaffoldError
        If no valid identifier can be derived from ``name``.

    Examples
    --------
    >>> to_module_name("task-list")
    'task_list'
    >>> to_module_name("My Tasks!")
    'my_tasks'
    """
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()
    slug = re.sub(r"_+", "_", slug)
    if not slug:
        raise ScaffoldError(
            f"Cannot derive a module name from {name!r}. "
            f"Use letters, digits, hyphens or underscores."
        )
    if slug[0].isdigit():
        slug = f"app_{slug}"
    if keyword.iskeyword(slug):
        slug = f"{slug}_app"
    return slug


def to_title(name: str) -> str:
    """Convert a project name to a human-readable title.

    Parameters
    ----------
    name : str
        User-supplied project name.

    Returns
    -------
    str
        Title-cased words, e.g. ``"task-list"`` -> ``"Task List"``.
    """
    words = [w for w in re.split(r"[^0-9a-zA-Z]+", name) if w]
    return " ".join(w if w.isupper() else w.capitalize() for w in words) or "App"


# The starter app. Deliberately small enough to read in one sitting, while
# covering the four things every Wijjit app needs: state, a template, an action
# handler, and a key handler.
#
# Frame height is not arbitrary. Content is 1 (input row) + 10 (an 8-row
# listview plus its border) + 1 (status) + 2 (vstack spacing) = 14, plus 2 for
# vstack padding and 2 for the frame border = 18. Undersize it and the frame
# silently becomes scrollable -- which also makes it focusable and puts it ahead
# of the input in the tab order.
_APP_BODY = '''from wijjit import Wijjit, render_template_string

app = Wijjit(
    initial_state={
        "entry": "",
        "tasks": [],
        "status": "Type a task and press Enter.",
    }
)

# The whole UI. Every tag comes in a pair -- there are no self-closing tags.
# Elements bind to state by id: the textinput below reads and writes
# state["entry"], and the listview renders state["tasks"].
TEMPLATE = """
{% frame title="__TITLE__" border="rounded" width=54 height=18 %}
  {% vstack spacing=1 padding=1 %}

    {% hstack spacing=1 %}
      {% textinput id="entry" placeholder="New task" width="fill"
         action="add" autofocus=True %}
      {% endtextinput %}
      {% button id="add_btn" action="add" %}Add{% endbutton %}
    {% endhstack %}

    {% listview id="tasks" height=8 %}{% endlistview %}

    {% text %}{{ state.status }}{% endtext %}

  {% endvstack %}
{% endframe %}
"""


@app.view("main", default=True)
def main_view():
    """Render the task list.

    A synchronous view is re-invoked on every render, so anything computed
    here stays live. Pass changing values as context kwargs to
    render_template_string -- never format them into the template source,
    which would defeat the compiled-template cache.
    """
    return render_template_string(TEMPLATE)
'''

_APP_HANDLERS = '''

@app.on_action("add")
def add_task(event):
    """Add the typed task to the list.

    Fired by the Add button and by Enter in the textinput -- both name
    ``action="add"``, so neither needs its own callback.
    """
    text = app.state["entry"].strip()
    if not text:
        app.state["status"] = "Nothing to add."
        return
    # Rebind rather than mutate: assigning to a state key is what notifies
    # watchers and schedules the re-render.
    app.state["tasks"] = [*app.state["tasks"], text]
    app.state["entry"] = ""
    app.state["status"] = f"{len(app.state['tasks'])} task(s). Press c to clear."


@app.on_key("c")
def clear_tasks(event):
    """Clear every task. Ctrl+Q is reserved for quitting."""
    app.state["tasks"] = []
    app.state["status"] = "Cleared. Type a task and press Enter."


if __name__ == "__main__":
    app.run()
'''

SINGLE_FILE = (
    '''"""__TITLE__ - a Wijjit terminal app.

Run it::

    wijjit run __MODULE__.py

Inspect it without a terminal -- these need no TTY, so they work in CI and in
an agent's shell::

    wijjit validate __MODULE__.py --render
    wijjit render __MODULE__.py --keys "type:buy milk,enter"
    wijjit tree __MODULE__.py

The input takes focus on start (autofocus). Tab and Shift+Tab move
between the input and the button. Ctrl+Q quits.
"""

'''
    + _APP_BODY
    + _APP_HANDLERS
)

# -- project layout ------------------------------------------------------

PROJECT_APP = (
    '''"""__TITLE__ - a Wijjit terminal app.

Run it::

    wijjit run app.py

Test it (drives the app headlessly, no TTY)::

    pytest

The template lives in ``templates/main.wij.j2``. Wijjit discovers a
``templates/`` directory next to this module automatically, the way Flask does,
so no configuration is needed to load it.
"""

import copy

from wijjit import Wijjit, render_template

# Kept as a named constant so the tests can restore it between runs. ``app`` is
# a module-level singleton -- the same object every test drives -- so without a
# reset, state written by one test leaks into the next.
INITIAL_STATE = {
    "entry": "",
    "tasks": [],
    "status": "Type a task and press Enter.",
}

app = Wijjit(initial_state=copy.deepcopy(INITIAL_STATE))


@app.view("main", default=True)
def main_view():
    """Render the task list from templates/main.wij.j2."""
    return render_template("main.wij.j2")

'''
    + _APP_HANDLERS
)

PROJECT_TEMPLATE = """\
{# The UI for __TITLE__. Every tag comes in a pair -- there are no
   self-closing tags. Elements bind to state by id: the textinput reads and
   writes state["entry"], and the listview renders state["tasks"].

   The frame height is content-derived: 1 (input row) + 10 (an 8-row listview
   plus its border) + 1 (status) + 2 (vstack spacing), plus 2 for padding and 2
   for the border. Undersize it and the frame silently becomes scrollable --
   which also makes it focusable and puts it ahead of the input in the tab
   order. #}
{% frame title="__TITLE__" border="rounded" width=54 height=18 %}
  {% vstack spacing=1 padding=1 %}

    {% hstack spacing=1 %}
      {% textinput id="entry" placeholder="New task" width="fill"
         action="add" autofocus=True %}
      {% endtextinput %}
      {% button id="add_btn" action="add" %}Add{% endbutton %}
    {% endhstack %}

    {% listview id="tasks" height=8 %}{% endlistview %}

    {% text %}{{ state.status }}{% endtext %}

  {% endvstack %}
{% endframe %}
"""

PROJECT_TEST = '''"""Tests for __TITLE__, driven headlessly through the Wijjit harness.

No terminal is involved: the harness feeds scripted keys through the real
event-loop dispatch and exposes the rendered screen as text, so these run
anywhere pytest does -- including CI.

The ``wijjit_harness`` fixture comes from Wijjit's pytest plugin, which is
registered on install -- there is no conftest.py to write.
"""

import copy

import pytest

from app import INITIAL_STATE, app


@pytest.fixture(autouse=True)
def fresh_state():
    """Reset the shared app state before every test.

    ``app`` is created once at import, so every test drives the same object.
    Without this, a task added by one test is still there in the next -- the
    kind of ordering dependency that only shows up once the suite grows.
    """
    app.state.update(copy.deepcopy(INITIAL_STATE))


def test_adding_a_task_shows_it_in_the_list(wijjit_harness):
    with wijjit_harness(app, size=(60, 22)) as h:
        # Focus by id rather than counting Tab presses. Focus, like state,
        # lives on the shared app, so "one Tab from the start" means something
        # different depending on which test ran first.
        app.focus_element_by_id("entry")
        h.type("buy milk")
        h.press("enter")          # fires action="add"

        h.assert_text("buy milk")
        h.assert_text("1 task(s)")
        h.assert_no_errors()


def test_blank_input_is_rejected(wijjit_harness):
    with wijjit_harness(app, size=(60, 22)) as h:
        app.focus_element_by_id("entry")
        h.press("enter")

        h.assert_text("Nothing to add.")
        assert app.state["tasks"] == []


def test_c_clears_the_list(wijjit_harness):
    with wijjit_harness(app, size=(60, 22)) as h:
        app.focus_element_by_id("entry")
        h.type("buy milk")
        h.press("enter")
        assert app.state["tasks"] == ["buy milk"]

        # Move focus off the input, or "c" is typed into it rather than
        # reaching the @app.on_key("c") handler.
        app.focus_element_by_id("add_btn")
        h.press("c")

        assert app.state["tasks"] == []
        h.assert_text("Cleared.")
'''

PROJECT_PYPROJECT = """\
[project]
name = "__DIST__"
version = "0.1.0"
description = "__TITLE__ - a Wijjit terminal app"
requires-python = ">=3.11"
dependencies = ["wijjit"]

[dependency-groups]
dev = ["pytest"]

[tool.pytest.ini_options]
# Put the project root on sys.path so tests can "from app import app".
pythonpath = ["."]
"""

PROJECT_README = """\
# __TITLE__

A terminal app built with [Wijjit](https://github.com/thomas-villani/wijjit).

## Run it

```bash
uv run wijjit run app.py
```

The input takes focus on start (`autofocus=True` in the template), so you can
type straight away. Tab and Shift+Tab move between the input and the button.
Press `c` (with the input unfocused) to clear the list. Ctrl+Q quits.

## Test it

```bash
uv run pytest
```

The tests drive the app headlessly through `WijjitHarness` -- no terminal
required, so they run unchanged in CI.

## Inspect it

The UI is a template, which means tooling can read it without running the app:

```bash
uv run wijjit validate app.py --render   # lint it, and show the screen
uv run wijjit tree app.py                # dump the element tree
uv run wijjit render app.py --keys "type:buy milk,enter"
```

## Layout

```
app.py                 state, view, and action handlers
templates/main.wij.j2  the UI (auto-discovered next to app.py)
tests/test_app.py      headless harness tests
```
"""

PROJECT_GITIGNORE = """\
__pycache__/
*.py[cod]
.venv/
.pytest_cache/
dist/
"""


def _substitute(text: str, module: str, title: str, dist: str) -> str:
    """Fill the ``__TOKEN__`` placeholders in a scaffold template."""
    return (
        text.replace("__MODULE__", module)
        .replace("__TITLE__", title)
        .replace("__DIST__", dist)
    )


def _plan(name: str, layout: str) -> dict[str, str]:
    """Build the mapping of relative path -> file contents for a layout.

    Parameters
    ----------
    name : str
        User-supplied project name.
    layout : str
        One of :data:`LAYOUTS`.

    Returns
    -------
    dict
        Relative POSIX paths mapped to fully substituted file contents.

    Raises
    ------
    ScaffoldError
        If ``layout`` is not a known layout.
    """
    if layout not in LAYOUTS:
        raise ScaffoldError(
            f"Unknown layout {layout!r}. Choose one of: {', '.join(LAYOUTS)}."
        )

    module = to_module_name(name)
    title = to_title(name)
    dist = module.replace("_", "-")

    def fill(text: str) -> str:
        return _substitute(text, module, title, dist)

    if layout == "single":
        return {f"{module}.py": fill(SINGLE_FILE)}

    return {
        f"{module}/app.py": fill(PROJECT_APP),
        f"{module}/templates/main.wij.j2": fill(PROJECT_TEMPLATE),
        f"{module}/tests/test_app.py": fill(PROJECT_TEST),
        f"{module}/pyproject.toml": fill(PROJECT_PYPROJECT),
        f"{module}/README.md": fill(PROJECT_README),
        f"{module}/.gitignore": PROJECT_GITIGNORE,
    }


def create(
    name: str,
    directory: Path | None = None,
    layout: str = "single",
    force: bool = False,
) -> list[Path]:
    """Generate a starter Wijjit app.

    Parameters
    ----------
    name : str
        Project name. Non-identifier characters are folded to underscores for
        filenames and title-cased for display.
    directory : Path, optional
        Directory to generate into (default: the current directory).
    layout : {'single', 'project'}, optional
        ``'single'`` writes one runnable ``.py`` file; ``'project'`` writes a
        directory with a file-based template, tests, and packaging metadata.
    force : bool, optional
        Overwrite existing files instead of refusing (default: False).

    Returns
    -------
    list of Path
        Absolute paths of the files written, in creation order.

    Raises
    ------
    ScaffoldError
        If the name is unusable, the layout is unknown, or any target file
        already exists and ``force`` is False.
    """
    root = Path.cwd() if directory is None else Path(directory)
    plan = _plan(name, layout)

    # Check every target before writing any of them, so a collision cannot
    # leave a half-generated project behind.
    if not force:
        clashes = [rel for rel in plan if (root / rel).exists()]
        if clashes:
            listed = ", ".join(sorted(clashes))
            raise ScaffoldError(
                f"Refusing to overwrite existing file(s): {listed}. "
                f"Pass --force to overwrite."
            )

    written: list[Path] = []
    for rel, content in plan.items():
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")
        written.append(dst)
    return written


def next_steps(name: str, layout: str) -> list[str]:
    """Build the shell commands to print after generating a project.

    Parameters
    ----------
    name : str
        The project name that was passed to :func:`create`.
    layout : {'single', 'project'}
        The layout that was generated.

    Returns
    -------
    list of str
        Commands to run next, in order.
    """
    module = to_module_name(name)
    if layout == "single":
        return [
            f"wijjit run {module}.py",
            f"wijjit validate {module}.py --render",
        ]
    return [
        f"cd {module}",
        "wijjit run app.py",
        "pytest",
    ]
