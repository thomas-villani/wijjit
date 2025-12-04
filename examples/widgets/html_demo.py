"""HTML Content Demo - Demonstrates HTML formatting in Wijjit.

This demo showcases the HTML compatibility feature which allows HTML-like
formatting in template content:

- HTML text formatting with <b>, <i>, <u> tags via html=True parameter
- Inline color styling with <style fg="color" bg="color">
- Theme CSS class styling with custom elements like <text-danger>
- Link element for clickable inline text
- HTMLViewer element for scrollable HTML content

Controls:
- Tab/Shift+Tab: Navigate between focusable elements
- Enter/Space: Activate links
- Arrow keys: Scroll HTMLViewer content
- Ctrl+Q: Quit
"""

from wijjit import Wijjit

app = Wijjit()

# Demo template with various HTML features
TEMPLATE = """
{% frame border_style="single" title="HTML Content Demo" width="fill" height="fill" %}

    {% text %}Tab/Shift+Tab: Navigate | Enter/Space: Click | Arrows: Scroll | Ctrl+Q: Quit{% endtext %}

    {# Section 1: Basic HTML formatting in text #}
    {% frame border_style="single" title="1. HTML Text Formatting (html=true)" width=74 height=4 %}
      {% vstack %}
        {% text html=true wrap=false %}<b>Bold</b>, <i>Italic</i>, <u>Underline</u>, <b><i>Bold+Italic</i></b>, <s>Strikethrough</s>{% endtext %}
        {% text html=true wrap=false %}<style fg="red">Red</style>, <style fg="green">Green</style>, <style fg="#0088FF">Blue (#0088FF)</style>, <style fg="#F0F">Magenta (#F0F)</style>{% endtext %}
      {% endvstack %}
    {% endframe %}

    {# Section 2: Theme-styled HTML #}
    {% frame border_style="single" title="2. Theme CSS Classes in HTML" width=74 height=4 %}
      {% vstack %}
        {% text html=true wrap=false %}<text-danger>text-danger</text-danger> | <text-warning>text-warning</text-warning> | <text-success>text-success</text-success> | <text-info>text-info</text-info>{% endtext %}
        {% text html=true wrap=false %}<text-primary>text-primary</text-primary> | <text-secondary>text-secondary</text-secondary> | <text-muted>text-muted</text-muted>{% endtext %}
      {% endvstack %}
    {% endframe %}

    {# Section 3: Link elements #}
    {% frame border_style="single" title="3. Link Elements (focusable, clickable)" width=74 height=3 %}
      {% hstack spacing=3 %}
        {% link id="link1" action="link1" %}Default Link{% endlink %}
        {% link id="link2" action="link2" class="text-danger" %}Danger Link{% endlink %}
        {% link id="link3" action="link3" class="text-success" %}Success Link{% endlink %}
        {% link id="link4" action="link4" class="text-warning" %}Warning Link{% endlink %}
      {% endhstack %}
    {% endframe %}

    {# Section 4: HTMLViewer with scrolling #}
    {% htmlview id="html_content" width=74 height=10 border_style="rounded" title="4. Scrollable HTMLViewer" %}
<b>Welcome to HTMLViewer!</b>

This is a <i>scrollable</i> HTML content viewer. Use arrow keys or mouse wheel to scroll.

<u>Supported Features:</u>
- <b>Bold</b> and <i>italic</i> text formatting
- <u>Underlined</u> and <s>strikethrough</s> (shown as dim) text
- <style fg="red">Inline</style> <style fg="green">color</style> <style fg="#FF00FF">styling</style>
- Theme classes: <text-danger>danger</text-danger>, <text-success>success</text-success>

Keep scrolling...

<style fg="cyan">Line 10</style>
<style fg="cyan">Line 11</style>
<style fg="cyan">Line 12</style>

<b><style fg="yellow">End of scrollable content!</style></b>
    {% endhtmlview %}

    {# Status bar #}
    {% frame border_style="single" width=74 height=3 %}
      {% vstack %}
        {% text %}Last action: {{ state.last_action }}{% endtext %}
        {% text %}Click count: {{ state.click_count }}{% endtext %}
      {% endvstack %}
    {% endframe %}

{% endframe %}
"""


@app.view("main", default=True)
def main_view():
    """Main view showing HTML features."""
    return {"template": TEMPLATE}


@app.on_action("link1")
def on_link1(event):
    """Handle link1 click."""
    app.state.click_count += 1
    app.state.last_action = "Clicked 'Default Link'"


@app.on_action("link2")
def on_link2(event):
    """Handle link2 click."""
    app.state.click_count += 1
    app.state.last_action = "Clicked 'Danger Link'"


@app.on_action("link3")
def on_link3(event):
    """Handle link3 click."""
    app.state.click_count += 1
    app.state.last_action = "Clicked 'Success Link'"


@app.on_action("link4")
def on_link4(event):
    """Handle link4 click."""
    app.state.click_count += 1
    app.state.last_action = "Clicked 'Warning Link'"


def main():
    """Run the demo."""
    # Initialize state
    app.state.last_action = "(none)"
    app.state.click_count = 0

    # Run the app
    app.run()


if __name__ == "__main__":
    main()
