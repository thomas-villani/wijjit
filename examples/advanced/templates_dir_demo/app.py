"""Templates-directory demo: file-based templates with auto-discovery.

Most Wijjit examples keep their UI in inline ``render_template_string`` strings.
This one shows the Flask-style alternative: the UI lives in ``templates/*.tui``
files that sit next to this module, and views load them with
:func:`wijjit.render_template`.

Because no ``template_dir`` is passed to ``Wijjit()``, the framework
auto-discovers the sibling ``templates/`` directory - the same convention Flask
uses. The two views share a header through Jinja's ``{% include %}``, which is
exactly how file templates compose on the web.

Run it::

    python examples/advanced/templates_dir_demo/app.py

Layout::

    templates_dir_demo/
        app.py
        templates/
            _header.tui      # shared partial, {% include %}-ed by both views
            home.tui         # the default "home" view
            dashboard.tui    # the "dashboard" view
"""

from wijjit import Wijjit, render_template

# No template_dir= argument: Wijjit auto-discovers ./templates next to this file.
app = Wijjit(
    initial_state={
        "clicks": 0,
        "user": "operator",
    }
)


@app.view("home", default=True)
def home_view():
    # render_template loads templates/home.tui from the discovered directory.
    # Context is passed as keyword arguments, just like render_template_string;
    # because the view re-runs every render, "clicks" stays live.
    return render_template(
        "home.tui",
        title="Home",
        clicks=app.state.clicks,
    )


@app.view("dashboard")
def dashboard_view():
    rows = [
        {"label": "Sessions", "value": 128},
        {"label": "Errors", "value": 3},
        {"label": "Uptime", "value": "17h 42m"},
    ]
    return render_template(
        "dashboard.tui",
        title="Dashboard",
        rows=rows,
        clicks=app.state.clicks,
    )


@app.on_action("increment")
def increment(event):
    app.state.clicks += 1


@app.on_action("go_dashboard")
def go_dashboard(event):
    app.navigate("dashboard")


@app.on_action("go_home")
def go_home(event):
    app.navigate("home")


@app.on_action("quit")
def quit_app(event):
    app.quit()


if __name__ == "__main__":
    app.run()
