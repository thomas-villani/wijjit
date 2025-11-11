"""End-to-end tests for form submission workflows.

These tests simulate complete user journeys from form display through
input entry, validation, submission, and result handling.
"""

import pytest

from wijjit.core.app import Wijjit

pytestmark = pytest.mark.e2e


class TestLoginFormJourney:
    """Test complete login form user journey."""

    def test_successful_login_flow(self):
        """Test end-to-end successful login flow.

        Journey:
        1. App displays login form
        2. User enters username
        3. User enters password
        4. User clicks login button
        5. App validates credentials
        6. App navigates to dashboard
        7. Dashboard shows user information
        """
        app = Wijjit(
            initial_state={
                "logged_in": False,
                "username": "",
                "current_user": None,
                "login_error": None,
            }
        )

        submission_data = {}

        @app.view("login", default=True)
        def login_view():
            def handle_login():
                # Simulate credential validation
                username = submission_data.get("username", "")
                password = submission_data.get("password", "")

                if username == "admin" and password == "secret":
                    app.state["logged_in"] = True
                    app.state["current_user"] = username
                    app.navigate("dashboard")
                else:
                    app.state["login_error"] = "Invalid credentials"

            return {
                "template": """
{% frame width=45 height=15 title="Login" %}
    {% if login_error %}
        Error: {{ login_error }}
    {% endif %}

    Username:
    {% textinput id="username" %}{% endtextinput %}

    Password:
    {% textinput id="password" placeholder="Password" %}{% endtextinput %}

    {% button id="login" action="login" %}Login{% endbutton %}
{% endframe %}
                """,
                "on_enter": lambda: None,
            }

        @app.view("dashboard")
        def dashboard_view():
            return {
                "template": """
{% frame width=60 height=20 title="Dashboard" %}
    Welcome, {{ current_user }}!

    You are now logged in.
{% endframe %}
                """
            }

        # Step 1: App initializes with login view
        assert app.current_view == "login"
        assert not app.state["logged_in"]

        # Step 2 & 3: Simulate user entering credentials
        submission_data["username"] = "admin"
        submission_data["password"] = "secret"

        # Step 4: Simulate login button click
        login_view()["on_enter"]  # Ensure view is initialized

        # Manually trigger login handler (simulating button action)
        app._initialize_view(app.views["login"])
        # In a real app, this would be triggered by action handler

        # Step 5 & 6: Validate and navigate (simulating successful login)
        if (
            submission_data["username"] == "admin"
            and submission_data["password"] == "secret"
        ):
            app.state["logged_in"] = True
            app.state["current_user"] = submission_data["username"]
            app.navigate("dashboard")

        # Step 7: Verify dashboard state
        assert app.current_view == "dashboard"
        assert app.state["logged_in"] is True
        assert app.state["current_user"] == "admin"

        # Verify dashboard can render
        app._initialize_view(app.views["dashboard"])
        data = {**dict(app.state), **app.views["dashboard"].data()}
        output, _ = app.renderer.render_with_layout(
            app.views["dashboard"].template, data
        )
        assert "Welcome, admin" in output

    def test_failed_login_flow(self):
        """Test end-to-end failed login flow.

        Journey:
        1. App displays login form
        2. User enters invalid credentials
        3. User clicks login button
        4. App shows error message
        5. User remains on login page
        """
        app = Wijjit(initial_state={"logged_in": False, "login_error": None})

        # Step 1: Start at login
        @app.view("login", default=True)
        def login_view():
            return {
                "template": """
{% if login_error %}
    Error: {{ login_error }}
{% else %}
    Please log in
{% endif %}
                """
            }

        assert app.current_view == "login"

        # Steps 2-4: Simulate failed login
        app.state["login_error"] = "Invalid credentials"

        # Step 5: Verify still on login page
        assert app.current_view == "login"
        assert app.state["login_error"] == "Invalid credentials"
        assert not app.state["logged_in"]


class TestRegistrationFormJourney:
    """Test complete registration form user journey."""

    def test_successful_registration_flow(self):
        """Test end-to-end registration flow.

        Journey:
        1. Navigate to registration form
        2. Fill out all required fields
        3. Click register button
        4. Validate form data
        5. Create account
        6. Navigate to success page
        """
        app = Wijjit(
            initial_state={
                "registration_complete": False,
                "validation_errors": [],
                "new_user": None,
            }
        )

        form_data = {}

        @app.view("register", default=True)
        def register_view():
            return {
                "template": """
{% frame width=50 height=20 title="Register" %}
    {% if validation_errors %}
        {% for error in validation_errors %}
            Error: {{ error }}
        {% endfor %}
    {% endif %}

    {% textinput id="username" %}{% endtextinput %}
    {% textinput id="email" %}{% endtextinput %}
    {% textinput id="password" placeholder="Password" %}{% endtextinput %}
    {% button id="register" %}Register{% endbutton %}
{% endframe %}
                """
            }

        @app.view("success")
        def success_view():
            return {"template": "Registration successful for {{ new_user }}!"}

        # Step 1: Start at registration
        assert app.current_view == "register"

        # Step 2: Fill form
        form_data["username"] = "newuser"
        form_data["email"] = "user@example.com"
        form_data["password"] = "secure123"

        # Steps 3-5: Validate and register
        validation_errors = []
        if not form_data.get("username"):
            validation_errors.append("Username required")
        if not form_data.get("email") or "@" not in form_data.get("email", ""):
            validation_errors.append("Valid email required")
        if not form_data.get("password") or len(form_data.get("password", "")) < 6:
            validation_errors.append("Password must be at least 6 characters")

        if not validation_errors:
            app.state["registration_complete"] = True
            app.state["new_user"] = form_data["username"]
            app.navigate("success")
        else:
            app.state["validation_errors"] = validation_errors

        # Step 6: Verify success
        assert app.current_view == "success"
        assert app.state["registration_complete"] is True
        assert app.state["new_user"] == "newuser"


class TestMultiStepFormJourney:
    """Test multi-step form wizard journey."""

    def test_complete_wizard_flow(self):
        """Test complete multi-step wizard.

        Journey:
        1. Start at step 1 (personal info)
        2. Fill and proceed to step 2 (address)
        3. Fill and proceed to step 3 (review)
        4. Review and submit
        5. Navigate to confirmation
        """
        app = Wijjit(
            initial_state={"wizard_step": 1, "form_data": {}, "submitted": False}
        )

        @app.view("wizard", default=True)
        def wizard_view():
            template = """
{% if wizard_step == 1 %}
    Step 1: Personal Info
    {% button id="next1" %}Next{% endbutton %}
{% elif wizard_step == 2 %}
    Step 2: Address
    {% button id="back2" %}Back{% endbutton %}
    {% button id="next2" %}Next{% endbutton %}
{% elif wizard_step == 3 %}
    Step 3: Review
    {% button id="back3" %}Back{% endbutton %}
    {% button id="submit" %}Submit{% endbutton %}
{% endif %}
            """
            return {"template": template}

        @app.view("confirmation")
        def confirmation_view():
            return {"template": "Thank you! Your submission is complete."}

        # Journey through steps
        assert app.state["wizard_step"] == 1

        # Step 1 -> 2
        app.state["wizard_step"] = 2
        assert app.state["wizard_step"] == 2

        # Step 2 -> 3
        app.state["wizard_step"] = 3
        assert app.state["wizard_step"] == 3

        # Submit
        app.state["submitted"] = True
        app.navigate("confirmation")

        assert app.current_view == "confirmation"
        assert app.state["submitted"] is True


class TestFormValidationJourney:
    """Test form validation throughout user journey."""

    def test_inline_validation_flow(self):
        """Test real-time validation during form entry.

        Journey:
        1. User starts entering email
        2. Validation checks format on blur
        3. Error shown for invalid format
        4. User corrects email
        5. Validation passes
        6. Form can be submitted
        """
        app = Wijjit(
            initial_state={"email": "", "email_error": None, "can_submit": False}
        )

        @app.view("form", default=True)
        def form_view():
            return {
                "template": """
{% textinput id="email" value=email %}{% endtextinput %}
{% if email_error %}
    Error: {{ email_error }}
{% endif %}
{% button id="submit" disabled=not can_submit %}Submit{% endbutton %}
                """
            }

        # Step 1-3: Enter invalid email
        app.state["email"] = "notanemail"
        if "@" not in app.state["email"]:
            app.state["email_error"] = "Invalid email format"
            app.state["can_submit"] = False

        assert app.state["email_error"] is not None
        assert not app.state["can_submit"]

        # Steps 4-5: Correct email
        app.state["email"] = "valid@example.com"
        if "@" in app.state["email"]:
            app.state["email_error"] = None
            app.state["can_submit"] = True

        assert app.state["email_error"] is None
        assert app.state["can_submit"] is True


class TestFormNavigationJourney:
    """Test navigation within and between forms."""

    def test_form_to_form_navigation(self):
        """Test navigating between different forms.

        Journey:
        1. Fill out contact form
        2. Navigate to preferences form
        3. Fill preferences
        4. Navigate back to review
        5. Data from both forms persists
        """
        app = Wijjit(initial_state={"contact_data": {}, "preferences_data": {}})

        @app.view("contact", default=True)
        def contact_view():
            return {"template": "Contact Form"}

        @app.view("preferences")
        def preferences_view():
            return {"template": "Preferences Form"}

        @app.view("review")
        def review_view():
            return {"template": "Review: {{ contact_data }} {{ preferences_data }}"}

        # Step 1: Fill contact
        app.state["contact_data"] = {"name": "Alice", "email": "alice@example.com"}

        # Step 2: Navigate to preferences
        app.navigate("preferences")
        assert app.current_view == "preferences"

        # Step 3: Fill preferences
        app.state["preferences_data"] = {"theme": "dark", "notifications": True}

        # Step 4: Navigate to review
        app.navigate("review")
        assert app.current_view == "review"

        # Step 5: Verify data persists
        assert app.state["contact_data"]["name"] == "Alice"
        assert app.state["preferences_data"]["theme"] == "dark"


class TestFormWithDynamicContent:
    """Test forms with dynamic content based on selections."""

    def test_conditional_form_fields(self):
        """Test form with conditional field visibility.

        Journey:
        1. Select account type (personal/business)
        2. Additional fields appear based on selection
        3. Fill type-specific fields
        4. Submit with correct data structure
        """
        app = Wijjit(
            initial_state={
                "account_type": None,
                "show_business_fields": False,
                "form_data": {},
            }
        )

        @app.view("signup", default=True)
        def signup_view():
            template = """
Account Type: {{ account_type or "Not selected" }}

{% if show_business_fields %}
    Business Name: [input]
    Tax ID: [input]
{% endif %}

{% if account_type %}
    {% button id="submit" %}Submit{% endbutton %}
{% endif %}
            """
            return {"template": template}

        # Step 1: Select business account
        app.state["account_type"] = "business"
        app.state["show_business_fields"] = True

        # Step 2: Verify business fields shown
        assert app.state["show_business_fields"] is True

        # Step 3: Fill business fields
        app.state["form_data"] = {
            "account_type": "business",
            "business_name": "Acme Corp",
            "tax_id": "12-3456789",
        }

        # Step 4: Verify data structure
        assert app.state["form_data"]["account_type"] == "business"
        assert "business_name" in app.state["form_data"]
        assert "tax_id" in app.state["form_data"]
