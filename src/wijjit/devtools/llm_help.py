"""A single paste-able Wijjit briefing for LLMs (``wijjit llm-help``).

The output is one self-contained Markdown document: enough to write a correct
Wijjit app from scratch, plus the commands to check the result. It is meant to
be piped into a coding agent's context::

    wijjit llm-help > WIJJIT.md
    wijjit llm-help | pbcopy

Why generate it instead of shipping a static file
-------------------------------------------------
The riskiest part of any cheat sheet is the attribute list -- a stale or
invented attribute name is exactly the failure mode this document exists to
prevent. So the tag reference is not written by hand: it is introspected from
the live Jinja environment (every registered extension's ``_render_<tag>``
signature) at the moment the command runs. Prose that explains *concepts* is
curated below; the part that would drift is generated, and therefore cannot.
"""

from __future__ import annotations

import inspect

# Tags grouped for presentation. Anything registered but not listed here still
# appears, under "Other" -- so a newly added tag can never silently vanish from
# the reference.
TAG_GROUPS: list[tuple[str, tuple[str, ...]]] = [
    (
        "Layout",
        ("vstack", "hstack", "frame", "grid", "colspan", "rowspan", "splitpanel"),
    ),
    ("Text", ("text", "link")),
    (
        "Input",
        (
            "textinput",
            "textarea",
            "button",
            "checkbox",
            "checkboxgroup",
            "radio",
            "radiogroup",
            "select",
            "selectitem",
            "slider",
            "toggle",
            "codeeditor",
            "datagrid",
        ),
    ),
    (
        "Display",
        (
            "table",
            "tree",
            "treeitem",
            "listview",
            "logview",
            "contentview",
            "progressbar",
            "spinner",
            "statusbar",
            "status",
            "status_indicator",
            "imageview",
            "pager",
            "page",
            "tabbedpanel",
            "tab",
        ),
    ),
    (
        "Charts",
        ("sparkline", "barchart", "columnchart", "linechart", "gauge", "heatmap"),
    ),
    (
        "Overlays and menus",
        (
            "modal",
            "dropdown",
            "contextmenu",
            "menuitem",
            "alertdialog",
            "confirmdialog",
            "inputdialog",
        ),
    ),
]


def _collect_tags() -> dict[str, list[str]]:
    """Introspect the live Jinja environment for every tag and its attributes.

    Returns
    -------
    dict
        Tag name -> ordered attribute names, taken from the extension's
        ``_render_<tag>`` signature (minus the Jinja plumbing).
    """
    from wijjit.core.renderer import Renderer

    env = Renderer().env
    found: dict[str, list[str]] = {}
    for extension in env.extensions.values():
        for tag in getattr(extension, "tags", set()):
            handler = getattr(extension, f"_render_{tag}", None)
            if handler is None:
                found.setdefault(str(tag), [])
                continue
            params = [
                name
                for name in inspect.signature(handler).parameters
                if name not in ("self", "caller", "kwargs")
            ]
            found[str(tag)] = params
    return found


def build_tag_reference() -> str:
    """Render the generated tag/attribute reference as Markdown."""
    tags = _collect_tags()
    grouped: set[str] = set()
    lines: list[str] = []

    for title, names in TAG_GROUPS:
        present = [n for n in names if n in tags]
        if not present:
            continue
        grouped.update(present)
        lines.append(f"### {title}\n")
        for name in present:
            attrs = ", ".join(tags[name]) or "(no attributes)"
            lines.append(f"- `{{% {name} %}}` - {attrs}")
        lines.append("")

    leftover = sorted(set(tags) - grouped)
    if leftover:
        lines.append("### Other\n")
        for name in leftover:
            attrs = ", ".join(tags[name]) or "(no attributes)"
            lines.append(f"- `{{% {name} %}}` - {attrs}")
        lines.append("")

    return "\n".join(lines).rstrip()


GUIDE_HEADER = """\
# Wijjit for LLMs

Wijjit builds terminal UIs from **Jinja2 templates** plus Flask-style
decorators. If you know Flask and Jinja, you already know the shape of this.

Everything below is accurate for wijjit __WIJJIT_VERSION__. The tag reference near the
end is generated from this installation, not written from memory -- trust it
over anything you recall.

## The one-minute model

    template (Jinja2 + custom tags)
      -> VNode tree      (immutable description of the UI)
      -> reconciler      (diffs against the previous tree)
      -> element tree    (stateful widgets, reused across renders)
      -> layout -> paint -> ANSI

Two consequences worth holding on to:

1. **Re-rendering is cheap and safe.** The reconciler reuses elements, so
   cursor position, scroll offset, and selection survive a re-render. Do not
   hand-manage them.
2. **The template is a static artifact.** Tools can read it without running the
   app -- which is why you can lint and drive a Wijjit app headlessly (see
   "Check your work").

## Starting from a scaffold

`wijjit new NAME` writes a runnable starter app -- one file by default, or
`--template project` for a version with the template in `templates/`, headless
harness tests, and packaging metadata. Prefer it to writing a file from scratch:
the generated app is linted and driven in Wijjit's own test suite, so it is
known-good starting shape.

## A complete app

```python
from wijjit import Wijjit, render_template_string

app = Wijjit(initial_state={"name": "", "greeting": ""})

TEMPLATE = \"\"\"
{% frame title="Hello" border="rounded" width=50 height=9 %}
  {% vstack spacing=1 padding=1 %}
    {% text %}{{ state.greeting or "What's your name?" }}{% endtext %}
    {% hstack spacing=1 %}
      {% textinput id="name" placeholder="Your name" width="fill"
         action="greet" %}{% endtextinput %}
      {% button action="greet" %}Greet{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
\"\"\"


@app.view("main", default=True)
def main_view():
    return render_template_string(TEMPLATE)


@app.on_action("greet")
def greet(event):
    app.state["greeting"] = f"Hello, {app.state['name']}!"


@app.on_key("r")
def reset(event):
    app.state["greeting"] = ""


if __name__ == "__main__":
    app.run()
```

Run it with `python app.py`, or `wijjit run app.py`.

**Ctrl+Q already quits** -- it is reserved, and binding it raises
`KeyBindingError`. Call `app.quit()` from any handler to exit programmatically.

## The rules that matter

**Every tag needs a closing tag.** `{% button %}...{% endbutton %}`,
`{% textinput %}{% endtextinput %}` -- even when the body is empty. There are no
self-closing tags.

**State binding is automatic and id-based.** An input with `id="name"` reads and
writes `state["name"]`. That is what `bind` controls; pass `bind=False` to opt
out, or `bind="other_key"` to point elsewhere. You rarely need to set a `value`
by hand.

**Read state in templates as `state.foo`.** Extra context passed to
`render_template_string(TEMPLATE, total=n)` is available as `{{ total }}`.

**Pass changing values as context, never by formatting the template string.**

```python
# CORRECT - the compiled template is cached and reused
return render_template_string(TEMPLATE, total=len(items))

# WRONG - a new template source every render, defeating the cache
return render_template_string(f"{{% text %}}{len(items)}{{% endtext %}}")
```

**Views re-run on every render.** A synchronous view function is called each
frame, so anything it computes stays live. Async views resolve once -- drive
those from `state` instead.

**Actions, not callbacks.** Give an element `action="save"` and handle it with
`@app.on_action("save")`. Handlers may be sync or async; both are supported.

**Sizes** are `50` (fixed columns), `"fill"` (take remaining space), `"auto"`
(fit content), or `"50%"`. Quote everything except bare integers.

**Do not put Unicode or emoji in framework-facing Python code.** Templates and
displayed strings are fine; box-drawing is handled for you.

## Layout

`{% vstack %}` stacks children vertically, `{% hstack %}` horizontally, and
`{% frame %}` draws a titled box around whatever it contains. `hstack` supports
flexbox-style `justify`, `wrap`, and `gap` / `row_gap` / `column_gap`.

A frame whose content does not fit becomes scrollable, which also makes it
focusable and puts it in the Tab order. If you did not want that, give the
frame more height.

## Focus

Nothing is focused when an app starts, so keystrokes go nowhere until the user
presses Tab. Give the field the user should start in `autofocus=True`:

```
{% textinput id="entry" width="fill" autofocus=True %}{% endtextinput %}
```

It applies whenever focus would otherwise be unset -- on the first render, and
again if the focused element disappears -- and never steals focus from an
element that already has it. One per view; `tabindex="-1"` excludes an element
from autofocus as it does from Tab. `app.focus_element_by_id("entry")` does the
same thing imperatively, but only after the first render has built the
elements.

## Common mistakes

| Mistake | Correct |
|---|---|
| `{% button %}Save{% end %}` | `{% endbutton %}` -- closing tags are tag-specific |
| `{{ name }}` for state | `{{ state.name }}` (or pass it as context) |
| `on_click=` / `onclick=` | `action="save"` + `@app.on_action("save")` |
| `width=fill` | `width="fill"` -- quote non-integer sizes |
| Formatting values into the template source | Pass them as context kwargs |
| Setting `value=` on every input each render | Let `bind` handle it |
| Expecting the first field to be focused | Mark it `autofocus=True` |
| Looping without `key=` | Give repeated elements stable unique ids |

## Check your work

Do not guess whether a template is right -- the toolchain answers statically,
with no terminal involved:

```bash
wijjit new app --template project # a known-good starting point
wijjit validate app.py            # unknown tags, undefined vars, bad attributes
wijjit validate app.py --json     # same, machine-readable, non-zero exit on error
wijjit tree app.py --json         # the VNode "DOM" the template produces
wijjit render app.py --size 80x24 # the actual rendered screen, no TTY
wijjit render app.py --keys "tab,type:alice,enter"
```

`--keys` steps: a key name (`tab`, `enter`, `space`, `ctrl+q`), `type:TEXT`,
`click:X,Y`, `tick:N` (advance animation frames), `settle:N` (pump event-loop
frames so background async work finishes).

**Always run `wijjit validate` on a template you just wrote.** It catches the
errors in the table above before the app runs.

For tests, drive the app headlessly:

```python
from wijjit.testing import WijjitHarness

with WijjitHarness(app, size=(80, 24)) as h:
    h.press("tab")
    h.type("alice")
    h.press("enter")
    h.assert_text("Hello, alice!")
    h.assert_no_errors()
```

Installing wijjit also registers pytest fixtures (`wijjit_harness`,
`wijjit_make_app`), and `wijjit.testing.app_from_template(TEMPLATE, state=...)`
builds a drivable app from a bare template with no boilerplate.

## Tag reference

Generated from this installation. Attributes are listed in signature order;
`id`, `bind`, `class`, and `tabindex` are widely accepted. Charts that colour by
*mode* use `color_mode` ("default"/"gradient"/"threshold"); `color` means a
literal colour string (`"#ff0000"`, `"red"`, `"rgb(255,0,0)"`) on the charts
that take one.
"""

GUIDE_FOOTER = """\

## Where to look next

- `wijjit validate` / `tree` / `render` -- the fastest ground truth.
- Bundled examples: 74 runnable demos under `examples/`, indexed in
  `examples/README.md` with screenshots in `examples/GALLERY.md`.
- Full docs: https://thomas-villani.github.io/wijjit/
"""


def render_llm_help() -> str:
    """Build the complete Markdown briefing.

    Returns
    -------
    str
        Curated prose with a freshly introspected tag reference spliced in.
    """
    from wijjit import __version__

    # A plain replace, not str.format: the guide is full of literal "{% %}"
    # braces that format() would try to read as replacement fields.
    header = GUIDE_HEADER.replace("__WIJJIT_VERSION__", __version__)
    return header + "\n" + build_tag_reference() + "\n" + GUIDE_FOOTER
