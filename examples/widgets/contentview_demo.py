"""ContentView Demo - Unified content display element.

This demo showcases the ContentView element which supports multiple
content types: plain, ansi, html, markdown, rich, and code.

Use Tab to cycle between different content views.
Use arrow keys to scroll within each view.
Press Ctrl+Q to quit.
"""

from wijjit import Wijjit

app = Wijjit()


# Sample content for each type
PLAIN_CONTENT = """This is plain text content.
It has no special formatting.

Multiple paragraphs are supported.
Line wrapping works automatically based on the width."""

ANSI_CONTENT = """\x1b[1mBold text\x1b[0m and \x1b[31mred text\x1b[0m
\x1b[32mGreen\x1b[0m, \x1b[33mYellow\x1b[0m, \x1b[34mBlue\x1b[0m
\x1b[1;35mBold Magenta\x1b[0m and \x1b[4;36mUnderlined Cyan\x1b[0m

ANSI escape codes are passed through directly."""

HTML_CONTENT = """<b>Bold</b> and <i>italic</i> text
<u>Underlined</u> and <s>strikethrough</s>
<style fg="red">Red text</style> and <style fg="green">green text</style>
<b><i>Combined bold and italic</i></b>

HTML tags are parsed for styling."""

MARKDOWN_CONTENT = """# Markdown Demo

This is **bold** and this is *italic*.

## Features
- Bullet points work
- Multiple items
- Nested content

### Code
Inline `code` is supported.

> Blockquotes look like this.

Regular paragraph text flows normally."""

RICH_CONTENT = """[bold]Bold text[/bold] and [italic]italic text[/italic]
[red]Red[/red], [green]Green[/green], [blue]Blue[/blue], [yellow]Yellow[/yellow]
[bold red]Bold Red[/bold red] and [underline cyan]Underlined Cyan[/underline cyan]

[dim]Dimmed text for less emphasis[/dim]
[reverse]Reversed video[/reverse]

Rich markup uses [green]square bracket[/green] syntax."""

CODE_CONTENT = '''def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Parameters
    ----------
    n : int
        The index of the Fibonacci number to calculate.

    Returns
    -------
    int
        The nth Fibonacci number.
    """
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


# Example usage
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")
'''


@app.view("main", default=True)
def main_view():
    """Main view showing all content types."""
    return {
        "template": """
{% frame border="double" title="ContentView Demo - Press Tab to navigate, Ctrl+Q to quit" %}
  {% hstack spacing=1 %}
    {% vstack width="50%" %}
      {% contentview id="plain" content_type="plain" title="Plain Text" height=10 %}
{{ plain_content }}
      {% endcontentview %}

      {% contentview id="ansi" content_type="ansi" title="ANSI" height=10 %}
{{ ansi_content }}
      {% endcontentview %}

      {% contentview id="html" content_type="html" title="HTML" height=10 %}
{{ html_content }}
      {% endcontentview %}
    {% endvstack %}

    {% vstack width="50%" %}
      {% contentview id="markdown" content_type="markdown" title="Markdown" height=10 %}
{{ markdown_content }}
      {% endcontentview %}

      {% contentview id="rich" content_type="rich" title="Rich Markup" height=10 %}
{{ rich_content }}
      {% endcontentview %}

      {% contentview id="code" content_type="code" language="python" show_line_numbers=true title="Code (Python)" height=10 %}
{{ code_content }}
      {% endcontentview %}
    {% endvstack %}
  {% endhstack %}
{% endframe %}
        """,
        "data": {
            "plain_content": PLAIN_CONTENT,
            "ansi_content": ANSI_CONTENT,
            "html_content": HTML_CONTENT,
            "markdown_content": MARKDOWN_CONTENT,
            "rich_content": RICH_CONTENT,
            "code_content": CODE_CONTENT,
        },
    }


if __name__ == "__main__":
    app.run()
