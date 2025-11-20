"""Simple test to verify {% markdown %} tag works."""

from wijjit import Wijjit

app = Wijjit(initial_state={"text": "# Hello World\n\nThis is a **test**."})


@app.view("main", default=True)
def main_view():
    return {
        "template": """
{% markdown id="test" content=state.text width=40 height=10 %}
{% endmarkdown %}
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
