"""Comprehensive Form Demo - Demonstrates form validation and error handling.

This example showcases:
- Multiple input types (text, email, select, checkbox, radio)
- Field validation with error messages
- Required and optional fields
- Real-time validation feedback
- Form submission with validation
- Reset functionality

Run with: python examples/advanced/form_demo.py

Controls:
- Tab/Shift+Tab: Navigate between fields
- q: Quit
"""

import re

from wijjit import Wijjit

# Email validation regex
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Create app with initial state
app = Wijjit(
    initial_state={
        "name": "",
        "email": "",
        "age": "",
        "country": "",
        "role": "developer",
        "newsletter": False,
        "terms": False,
        # Validation states
        "name_error": "",
        "email_error": "",
        "age_error": "",
        "country_error": "",
        "terms_error": "",
        "status": "Please fill out the registration form",
        "submitted": False,
    }
)


def validate_name(name):
    """Validate name field.

    Parameters
    ----------
    name : str
        Name to validate

    Returns
    -------
    str
        Error message or empty string if valid
    """
    if not name or not name.strip():
        return "Name is required"
    if len(name.strip()) < 2:
        return "Name must be at least 2 characters"
    if not name.strip().replace(" ", "").isalpha():
        return "Name must contain only letters"
    return ""


def validate_email(email):
    """Validate email field.

    Parameters
    ----------
    email : str
        Email to validate

    Returns
    -------
    str
        Error message or empty string if valid
    """
    if not email or not email.strip():
        return "Email is required"
    if not EMAIL_REGEX.match(email.strip()):
        return "Invalid email format"
    return ""


def validate_age(age):
    """Validate age field.

    Parameters
    ----------
    age : str
        Age to validate

    Returns
    -------
    str
        Error message or empty string if valid
    """
    if not age or not age.strip():
        return "Age is required"
    try:
        age_int = int(age.strip())
        if age_int < 13:
            return "Must be at least 13 years old"
        if age_int > 120:
            return "Invalid age"
    except ValueError:
        return "Age must be a number"
    return ""


def validate_country(country):
    """Validate country field.

    Parameters
    ----------
    country : str
        Country to validate

    Returns
    -------
    str
        Error message or empty string if valid
    """
    if not country or not country.strip():
        return "Country is required"
    return ""


def validate_terms(terms):
    """Validate terms checkbox.

    Parameters
    ----------
    terms : bool
        Terms acceptance status

    Returns
    -------
    str
        Error message or empty string if valid
    """
    if not terms:
        return "You must agree to the terms"
    return ""


@app.view("main", default=True)
def main_view():
    """Main registration form view."""
    return {
        "template": """
{% frame title="Registration Form" border="double" width=90 height=38 %}
  {% vstack spacing=1 padding=1 %}
    {% vstack spacing=0 %}
      {{ state.status }}
    {% endvstack %}

    {% vstack spacing=0 %}
      Name: *
      {% textinput id="name" placeholder="Enter your full name" width=50 action="validate_name" %}{% endtextinput %}
      {% if state.name_error %}
      Error: {{ state.name_error }}
      {% endif %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Email: *
      {% textinput id="email" placeholder="your@email.com" width=50 action="validate_email" %}{% endtextinput %}
      {% if state.email_error %}
      Error: {{ state.email_error }}
      {% endif %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Age: *
      {% textinput id="age" placeholder="18" width=20 action="validate_age" %}{% endtextinput %}
      {% if state.age_error %}
      Error: {{ state.age_error }}
      {% endif %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Country: *
      {% select id="country" width=50 border_style="single" title="" %}
        {"value": "", "label": "Select your country"}
        United States
        Canada
        United Kingdom
        Germany
        France
        Spain
        Italy
        Japan
        Australia
        Other
      {% endselect %}
      {% if state.country_error %}
      Error: {{ state.country_error }}
      {% endif %}
    {% endvstack %}

    {% vstack spacing=0 %}
      Role: *
      {% radiogroup id="role" orientation="horizontal" %}
        {% radio value="developer" %}Developer{% endradio %}
        {% radio value="designer" %}Designer{% endradio %}
        {% radio value="manager" %}Manager{% endradio %}
        {% radio value="other" %}Other{% endradio %}
      {% endradiogroup %}
    {% endvstack %}

    {% vstack spacing=0 %}
      {% checkbox id="newsletter" label="Subscribe to newsletter (optional)" %}{% endcheckbox %}
    {% endvstack %}

    {% vstack spacing=0 %}
      {% checkbox id="terms" label="I agree to the terms and conditions *" %}{% endcheckbox %}
      {% if state.terms_error %}
      Error: {{ state.terms_error }}
      {% endif %}
    {% endvstack %}

    {% if state.submitted %}
      {% vstack spacing=1 %}
        Registration Successful!
      {% endvstack %}

      {% vstack spacing=0 padding_left=2 %}
        Name: {{ state.name }}
        Email: {{ state.email }}
        Age: {{ state.age }}
        Country: {{ state.country }}
        Role: {{ state.role }}
        Newsletter: {{ 'Yes' if state.newsletter else 'No' }}
      {% endvstack %}
    {% endif %}

    {% hstack spacing=2 %}
      {% button action="submit" %}Register{% endbutton %}
      {% button action="reset" %}Reset{% endbutton %}
      {% button action="quit" %}Quit{% endbutton %}
    {% endhstack %}

    {% vstack spacing=0 %}
      * = Required field | [Tab/Shift+Tab] Navigate | [q] Quit
    {% endvstack %}
  {% endvstack %}
{% endframe %}
        """,
        "data": {},
    }


@app.on_action("validate_name")
def handle_validate_name(event):
    """Validate name field on blur."""
    name = app.state.get("name", "")
    app.state["name_error"] = validate_name(name)


@app.on_action("validate_email")
def handle_validate_email(event):
    """Validate email field on blur."""
    email = app.state.get("email", "")
    app.state["email_error"] = validate_email(email)


@app.on_action("validate_age")
def handle_validate_age(event):
    """Validate age field on blur."""
    age = app.state.get("age", "")
    app.state["age_error"] = validate_age(age)


@app.on_action("submit")
def handle_submit(event):
    """Handle form submission with full validation."""
    # Validate all fields
    name_err = validate_name(app.state.get("name", ""))
    email_err = validate_email(app.state.get("email", ""))
    age_err = validate_age(app.state.get("age", ""))
    country_err = validate_country(app.state.get("country", ""))
    terms_err = validate_terms(app.state.get("terms", False))

    # Update error states
    app.state["name_error"] = name_err
    app.state["email_error"] = email_err
    app.state["age_error"] = age_err
    app.state["country_error"] = country_err
    app.state["terms_error"] = terms_err

    # Check if any errors exist
    if any([name_err, email_err, age_err, country_err, terms_err]):
        app.state["status"] = "Please fix the errors above"
        app.state["submitted"] = False
        return

    # All valid - submit form
    app.state["submitted"] = True
    app.state["status"] = "Registration successful! Welcome aboard."


@app.on_action("reset")
def handle_reset(event):
    """Reset form to initial state."""
    app.state["name"] = ""
    app.state["email"] = ""
    app.state["age"] = ""
    app.state["country"] = ""
    app.state["role"] = "developer"
    app.state["newsletter"] = False
    app.state["terms"] = False
    app.state["name_error"] = ""
    app.state["email_error"] = ""
    app.state["age_error"] = ""
    app.state["country_error"] = ""
    app.state["terms_error"] = ""
    app.state["submitted"] = False
    app.state["status"] = "Form reset - please fill out the registration form"


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
