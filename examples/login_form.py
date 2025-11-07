"""Login form example demonstrating template-based forms with automatic event wiring.

This example showcases:
- Template-based UI with frames, vstacks, textinputs, and buttons
- Automatic state binding from element IDs to app.state
- Action handlers using @app.on_action() decorator
- Automatic Tab/Shift+Tab navigation between fields
- Automatic key routing to focused elements
"""

from wijjit import Wijjit

# Create app with initial state
app = Wijjit(initial_state={
    'username': '',
    'password': '',
    'status': 'Please enter your credentials',
    'logged_in': False,
})


@app.view("login", default=True)
def login_view():
    """Login form view."""
    return {
        "template": """
{% frame title="Login" border="single" width=50 height=15 %}
  {% vstack spacing=1 padding=1 %}
    {{ state.status }}

    {% vstack spacing=0 %}
      Username:
      {% textinput id="username" placeholder="Enter username" width=30 %}{% endtextinput %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Password:
      {% textinput id="password" placeholder="Enter password" width=30 action="login" %}{% endtextinput %}
    {% endvstack %}

    {% hstack spacing=2 %}
      {% button id="login_btn" action="login" %}Login{% endbutton %}
      {% button id="clear_btn" action="clear" %}Clear{% endbutton %}
      {% button id="quit_btn" action="quit" %}Quit{% endbutton %}
    {% endhstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("login")
def handle_login(event):
    """Handle login action."""
    username = app.state.get('username', '')
    password = app.state.get('password', '')

    if not username:
        app.state['status'] = 'Error: Username is required'
    elif not password:
        app.state['status'] = 'Error: Password is required'
    elif username == 'admin' and password == 'password':
        app.state['status'] = f'Success! Welcome, {username}!'
        app.state['logged_in'] = True
    else:
        app.state['status'] = 'Error: Invalid credentials'
        app.state['password'] = ''  # Clear password on failed login


@app.on_action("clear")
def handle_clear(event):
    """Handle clear action."""
    app.state['username'] = ''
    app.state['password'] = ''
    app.state['status'] = 'Form cleared'


@app.on_action("quit")
def handle_quit(event):
    """Handle quit action."""
    app.quit()


if __name__ == '__main__':
    # Run the app
    # Press Tab to navigate between fields
    # Press Enter in password field or click Login button to submit
    # Try credentials: admin / password
    app.run()
