"""Checkbox Demo - Template-based checkbox and checkbox groups.

This example demonstrates checkboxes using modern template-based patterns:
- Individual checkbox elements with state binding
- Checkbox groups for multiple selections
- Automatic state synchronization
- Form submission with validation
- Tab navigation between elements

Run with: python examples/widgets/checkbox_demo.py

Controls:
- Tab/Shift+Tab: Navigate between elements
- Space: Toggle checkbox
- Arrow keys: Navigate within CheckboxGroup (when implemented)
- q: Quit
"""

from wijjit import Wijjit

# Create app with initial state
app = Wijjit(
    initial_state={
        "newsletter": False,
        "terms": False,
        "notifications": False,
        "updates": False,
        "marketing": False,
        "status": "Please review and submit the form",
        "submitted": False,
    }
)


@app.view("main", default=True)
def main_view():
    """Main form view with checkboxes."""
    return {
        "template": """
{% frame title="Checkbox Demo" border="double" width=70 height=28 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.status }}
    {% endvstack %}

    {% vstack spacing=1 %}
      Individual Checkboxes:
    {% endvstack %}

    {% vstack spacing=0 %}
      {% checkbox id="newsletter" label="Subscribe to newsletter" %}{% endcheckbox %}
    {% endvstack %}

    {% vstack spacing=0 %}
      {% checkbox id="terms" label="I agree to the terms and conditions" %}{% endcheckbox %}
    {% endvstack %}

    {% vstack spacing=1 %}
      Email Preferences (Multiple Selection):
    {% endvstack %}

    {% vstack spacing=0 %}
      {% checkbox id="notifications" label="Email notifications" %}{% endcheckbox %}
    {% endvstack %}

    {% vstack spacing=0 %}
      {% checkbox id="updates" label="Product updates" %}{% endcheckbox %}
    {% endvstack %}

    {% vstack spacing=0 %}
      {% checkbox id="marketing" label="Marketing emails" %}{% endcheckbox %}
    {% endvstack %}

    {% if state.submitted %}
      {% vstack spacing=1 %}
        Submitted Values:
      {% endvstack %}

      {% vstack spacing=0 %}
        Newsletter: {{ 'Yes' if state.newsletter else 'No' }}
        Terms Accepted: {{ 'Yes' if state.terms else 'No' }}

        Email Preferences:
        {% if state.notifications or state.updates or state.marketing %}
          {% if state.notifications %}- Email notifications{% endif %}
          {% if state.updates %}- Product updates{% endif %}
          {% if state.marketing %}- Marketing emails{% endif %}
        {% else %}
          None selected
        {% endif %}
      {% endvstack %}
    {% endif %}

    {% hstack spacing=2 %}
      {% button action="submit" %}Submit{% endbutton %}
      {% button action="reset" %}Reset{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      Controls: [Tab/Shift+Tab] Navigate | [Space] Toggle | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("submit")
def handle_submit(event):
    """Handle form submission."""
    # Validate required fields
    if not app.state.get("terms", False):
        app.state["status"] = "Error: You must agree to the terms and conditions"
        app.state["submitted"] = False
        return

    # Count selected email preferences
    email_prefs = []
    if app.state.get("notifications"):
        email_prefs.append("notifications")
    if app.state.get("updates"):
        email_prefs.append("updates")
    if app.state.get("marketing"):
        email_prefs.append("marketing")

    # Update status
    app.state["submitted"] = True
    if app.state.get("newsletter"):
        msg = "Form submitted! You'll receive our newsletter"
    else:
        msg = "Form submitted successfully"

    if email_prefs:
        msg += f" with {len(email_prefs)} email preference(s)"

    app.state["status"] = msg


@app.on_action("reset")
def handle_reset(event):
    """Reset form to initial state."""
    app.state["newsletter"] = False
    app.state["terms"] = False
    app.state["notifications"] = False
    app.state["updates"] = False
    app.state["marketing"] = False
    app.state["submitted"] = False
    app.state["status"] = "Form reset - please review and submit"


@app.on_action("quit")
def handle_quit(event):
    """Quit the application."""
    app.quit()


@app.on_key("q")
def on_quit(event):
    """Handle 'q' key to quit."""
    app.quit()


if __name__ == "__main__":
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
