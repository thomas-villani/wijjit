"""Simple test to verify {% markdown %} tag works."""

from wijjit import Wijjit

app = Wijjit(initial_state={"text": "# Hello World\n\nThis is a **test**.\n\n> Did it work?"})


@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% frame %}
{% markdown id="test" content=state.text width=40 height=20 %}
{% endmarkdown %}
{% endframe %}
        """,
        "data": {},
    }


if __name__ == "__main__":
    try:
        app.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
