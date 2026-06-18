"""Pager Demo.

Demonstrates the Pager element for linear pagination through multiple pages.

Features:
- Keyboard navigation (Left/Right and PgUp/PgDown to change pages)
- Home/End to jump to first/last page
- Mouse click navigation (click Prev/Next buttons)
- Page indicator showing "Page X of Y"
- Optional page titles
- Loop mode for continuous navigation
- Multiple nav_position options (top, bottom, both)
- State persistence

Controls:
- Left/PgUp: Previous page
- Right/PgDown: Next page
- Home: First page
- End: Last page
- Mouse click: Click Prev/Next buttons
- q or Ctrl+Q: Quit
"""

from wijjit import Wijjit
from wijjit.logging_config import configure_logging

# Enable debug logging to file
configure_logging("pager-debug.log", level="DEBUG")

app = Wijjit(enable_mouse=True)


@app.view("main", default=True)
def main_view():
    template = """
    {% vstack spacing=1 padding=1 %}
        {% frame title="Pager Demo - Linear Pagination" border="double" %}
            Use Left/Right or PgUp/PgDown to navigate pages | Home/End for first/last
        {% endframe %}

        {% pager id="main_pager" nav_position="bottom" show_indicator=True
                 show_titles=True width=78 height=20 border="single" %}

            {% page title="Welcome" %}
Welcome to the Wijjit Pager Demo!

This demonstrates a linear pagination interface - similar to
a book or slideshow where you navigate through pages sequentially.

Key Features:
- Navigate with Left/Right or PgUp/PgDown keys
- Jump to first/last page with Home/End
- Click Prev/Next buttons with your mouse
- Page indicator shows current position
- Optionally display page titles

Unlike tabs which show all options at once, the pager
provides a cleaner interface for step-by-step content
like wizards, tutorials, or presentations.

Press Right arrow or click "Next >" to continue...
            {% endpage %}

            {% page title="Navigation" %}
Navigation Guide

Keyboard Shortcuts:
- Left Arrow or PgUp    : Previous page
- Right Arrow or PgDown : Next page
- Home                  : First page
- End                   : Last page

Mouse Controls:
- Click "< Prev" button for previous page
- Click "Next >" button for next page

The navigation bar can be positioned:
- top    : Nav bar at the top
- bottom : Nav bar at the bottom (default)
- both   : Nav bars at top AND bottom

Try the keyboard shortcuts to navigate!
            {% endpage %}

            {% page title="Use Cases" %}
Common Use Cases for the Pager Element

1. Setup Wizards
   Guide users through multi-step processes
   like configuration or installation.

2. Tutorials
   Present information in digestible chunks
   that users can move through at their pace.

3. Presentations
   Create simple slideshow-style interfaces
   for terminal-based presentations.

4. Multi-page Forms
   Break long forms into manageable sections
   to reduce cognitive load.

5. Documentation
   Display documentation pages that users
   can browse through sequentially.

6. Onboarding Flows
   Walk new users through features and
   capabilities step by step.
            {% endpage %}

            {% page title="Configuration" %}
Pager Configuration Options

Template Attributes:
- id             : Element identifier
- width          : Pager width (default: 60)
- height         : Pager height (default: 20)
- nav_position   : "top", "bottom", or "both"
- show_indicator : Show "Page X of Y" (default: True)
- show_titles    : Show page title in indicator
- loop           : Wrap from last to first page
- border_style   : "single", "double", "rounded", "none"
- current_page   : Initial page index or state key

Example usage:
  pager id="wizard" nav_position="bottom"
         show_indicator=True loop=False
      page title="Step 1"
          Content...
      endpage
  endpager

(Wrap tag names with curly-brace-percent in templates)
            {% endpage %}

            {% page title="Interactive" %}
This page demonstrates interactive elements within a pager.
Use Tab to move between form fields, Enter to activate buttons.

{% vstack spacing=1 %}
    {% textinput id="username" placeholder="Enter your name" width=40 %}{% endtextinput %}

    {% hstack spacing=2 %}
        {% checkbox id="newsletter" %}Subscribe to newsletter{% endcheckbox %}
        {% checkbox id="updates" %}Receive updates{% endcheckbox %}
    {% endhstack %}

    {% hstack spacing=2 %}
        {% button action="submit" %}Submit{% endbutton %}
        {% button action="clear" %}Clear{% endbutton %}
    {% endhstack %}
{% endvstack %}

Try typing in the text field above and toggling the checkboxes!
            {% endpage %}

            {% page title="About" %}
Wijjit Pager Element
Version 1.0.0

A declarative TUI framework for Python

The Pager element provides linear pagination for:
- Step-by-step navigation
- Sequential content browsing
- Wizard-style interfaces
- Tutorial presentations

Part of the Wijjit component library alongside:
- TabbedPanel (tabbed navigation)
- ListView (scrollable lists)
- Table (data grids)
- And many more...

Developer: Tom Villani
Framework: Wijjit - "Flask for the Console"

Press Home to go back to the first page,
or press 'q' to quit this demo.
            {% endpage %}

        {% endpager %}

        {% frame title="Controls" border="single" %}
Left/PgUp: prev | Right/PgDown: next | Home/End: first/last | Q: quit
        {% endframe %}
    {% endvstack %}
    """

    return {
        "template": template,
    }


@app.on_key("q")
def quit_app(event):
    app.quit()


@app.on_action("submit")
def handle_submit(event):
    """Handle form submission."""
    name = app.state.get("username", "")
    newsletter = app.state.get("newsletter", False)
    updates = app.state.get("updates", False)
    app.notify(f"Submitted: {name}, newsletter={newsletter}, updates={updates}")


@app.on_action("clear")
def handle_clear(event):
    """Clear the form."""
    app.state["username"] = ""
    app.state["newsletter"] = False
    app.state["updates"] = False
    app.notify("Form cleared!")


if __name__ == "__main__":
    app.run()
