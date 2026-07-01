"""Autocomplete demo - Basic word completion for text inputs.

This example demonstrates the autocomplete feature with different configurations:
1. Inline word list (simplest usage)
2. State-based dynamic word list
3. Registered completer with auto-wiring
4. Callback-based dynamic suggestions

Controls:
- Tab/Shift+Tab: Navigate between inputs
- Ctrl+/: Trigger autocomplete popup (manual mode)
- Up/Down: Navigate suggestions
- Enter/Tab: Select suggestion
- Escape: Close popup
- Ctrl+Q: Quit
"""

from wijjit import Wijjit, render_template_string
from wijjit.autocomplete import CallbackCompleter, WordCompleter

# Sample data for completions
FRUITS = [
    "apple",
    "apricot",
    "avocado",
    "banana",
    "blueberry",
    "blackberry",
    "cherry",
    "coconut",
    "date",
    "elderberry",
    "fig",
    "grape",
    "grapefruit",
    "kiwi",
    "lemon",
    "lime",
    "mango",
    "melon",
    "nectarine",
    "orange",
    "papaya",
    "peach",
    "pear",
    "pineapple",
    "plum",
    "raspberry",
    "strawberry",
    "tangerine",
    "watermelon",
]

COLORS = [
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "indigo",
    "violet",
    "black",
    "white",
    "gray",
    "brown",
    "pink",
    "purple",
    "cyan",
    "magenta",
]

LANGUAGES = [
    "Python",
    "JavaScript",
    "TypeScript",
    "Rust",
    "Go",
    "Java",
    "C",
    "C++",
    "C#",
    "Ruby",
    "PHP",
    "Swift",
    "Kotlin",
    "Scala",
]


app = Wijjit()

# Register a completer by name for use in templates
app.register_completer(
    "languages", WordCompleter(LANGUAGES, trigger="auto", min_chars=1)
)

# Register a completer for a specific element ID (auto-wire)
app.register_completer("#color", WordCompleter(COLORS, trigger="auto", min_chars=1))


# Callback-based completer for dynamic filtering
def search_items(prefix: str, context: dict | None) -> list[str]:
    """Search through all items dynamically."""
    all_items = FRUITS + COLORS + LANGUAGES
    if not prefix:
        return all_items[:10]
    prefix_lower = prefix.lower()
    matches = [item for item in all_items if prefix_lower in item.lower()]
    return sorted(matches)[:10]


app.register_completer(
    "search", CallbackCompleter(search_items, trigger="auto", min_chars=1)
)

# Dynamic word list for the state-reference autocomplete. Set once at startup -
# view functions run every render, so one-time setup belongs out here, not in
# the view body.
app.state.tags = [
    "python",
    "javascript",
    "rust",
    "go",
    "typescript",
    "react",
    "vue",
    "angular",
    "svelte",
    "django",
    "flask",
]


@app.view("main", default=True)
def main_view():
    return render_template_string(
        """
{% frame border="single" title="Autocomplete Demo" width="fill" height="fill" %}
  {% vstack spacing=1 %}

    Text with explanation
    Press Ctrl+/ to trigger autocomplete, or type and see auto-suggestions.

    {% hstack spacing=2 %}
      {% frame border="single" title="1. Inline List (Manual)" width=40 %}
        {% vstack spacing=1 %}
          Fruit:
          {% textinput id="fruit" placeholder="Type a fruit..." width=30
                       autocomplete=["apple", "banana", "cherry", "date", "elderberry"] %}
          {% endtextinput %}
          (Press Ctrl+/ to trigger)
        {% endvstack %}
      {% endframe %}

      {% frame border="single" title="2. State Reference (Auto)" width=40 %}
        {% vstack spacing=1 %}
          Tag:
          {% textinput id="tag" placeholder="Type a tag..." width=30
                       autocomplete="state.tags" %}
          {% endtextinput %}
          (Auto-triggers after 1 char)
        {% endvstack %}
      {% endframe %}
    {% endhstack %}

    {% hstack spacing=2 %}
      {% frame border="single" title="3. Registered Completer" width=40 %}
        {% vstack spacing=1 %}
          Language:
          {% textinput id="lang" placeholder="Type a language..." width=30
                       autocomplete="languages" %}
          {% endtextinput %}
          (Uses app.completers["languages"])
        {% endvstack %}
      {% endframe %}

      {% frame border="single" title="4. Auto-Wire by ID" width=40 %}
        {% vstack spacing=1 %}
          Color:
          {% textinput id="color" placeholder="Type a color..." width=30
                       autocomplete=True %}
          {% endtextinput %}
          (Auto-wires to app.completers["#color"])
        {% endvstack %}
      {% endframe %}
    {% endhstack %}

    {% frame border="single" title="5. Callback Completer (Dynamic Search)" width="fill" %}
      {% vstack spacing=1 %}
        Search all items:
        {% textinput id="search" placeholder="Search fruits, colors, languages..." width=50
                     autocomplete="search" %}
        {% endtextinput %}
        (Searches across all categories dynamically)
      {% endvstack %}
    {% endframe %}

    {% hstack spacing=2 %}
      {% button action="show_values" %}Show Current Values{% endbutton %}
      {% button action="clear_all" %}Clear All{% endbutton %}
    {% endhstack %}

    Status: {{ state.status or "Ready - try typing in the inputs above" }}

  {% endvstack %}
{% endframe %}
        """
    )


@app.on_action("show_values")
def show_values(event):
    values = []
    for key in ["fruit", "tag", "lang", "color", "search"]:
        if key in app.state and app.state[key]:
            values.append(f"{key}={app.state[key]}")
    if values:
        app.state.status = "Values: " + ", ".join(values)
    else:
        app.state.status = "No values entered yet"


@app.on_action("clear_all")
def clear_all(event):
    for key in ["fruit", "tag", "lang", "color", "search"]:
        app.state[key] = ""
    app.state.status = "All fields cleared"


if __name__ == "__main__":
    app.run()
