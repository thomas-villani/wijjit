"""End-to-end tests for form submission workflows.

These tests simulate complete user journeys from form display through
input entry, validation, submission, and result handling.
"""

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.events import ActionEvent

from .helpers import (
    assert_element_focused,
    get_element_by_id,
    get_rendered_text,
    render_view,
    simulate_button_click,
    simulate_tab_navigation,
    simulate_typing,
)

pytestmark = pytest.mark.e2e


class TestLoginFormJourney:
    """Test complete login form user journey."""

    def test_successful_login_flow(self):
        """Test end-to-end successful login flow.

        Journey:
        1. App displays login form
        2. User enters username
        3. User tabs to password field
        4. User enters password
        5. User tabs to login button
        6. User clicks login button
        7. App validates credentials
        8. App navigates to dashboard
        9. Dashboard shows user information
        """
        app = Wijjit(
            initial_state={
                "logged_in": False,
                "current_user": None,
                "login_error": None,
            }
        )

        # Register action handler for login button
        @app.on_action("login")
        def handle_login(event: ActionEvent):
            # Get values from state (via two-way binding)
            username = app.state.get("username", "")
            password = app.state.get("password", "")

            # Validate credentials
            if username == "admin" and password == "secret":
                app.state["logged_in"] = True
                app.state["current_user"] = username
                app.navigate("dashboard")
            else:
                app.state["login_error"] = "Invalid credentials"

        # Define views
        @app.view("login", default=True)
        def login_view():
            return {
                "template": """
{% frame width=45 height=15 title="Login" %}
    {% if login_error %}
        Error: {{ login_error }}
    {% endif %}

    Username:
    {% textinput id="username" bind=True %}{% endtextinput %}

    Password:
    {% textinput id="password" bind=True %}{% endtextinput %}

    {% button id="login_btn" action="login" %}Login{% endbutton %}
{% endframe %}
                """
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

        # Step 2: Render login form to create elements
        output, elements = render_view(app, "login")

        # Get form elements
        username_input = get_element_by_id(elements, "username")
        password_input = get_element_by_id(elements, "password")
        login_button = get_element_by_id(elements, "login_btn")

        assert username_input is not None, "Username input should exist"
        assert password_input is not None, "Password input should exist"
        assert login_button is not None, "Login button should exist"

        # Step 3: User enters username
        simulate_typing(username_input, "admin")
        assert username_input.value == "admin"
        assert app.state["username"] == "admin"  # Two-way binding

        # Step 4: User tabs to password field
        simulate_tab_navigation(app)
        assert_element_focused(app, "password")

        # Step 5: User enters password
        simulate_typing(password_input, "secret")
        assert password_input.value == "secret"
        assert app.state["password"] == "secret"  # Two-way binding

        # Step 6: User tabs to login button
        simulate_tab_navigation(app)
        assert_element_focused(app, "login_btn")

        # Step 7: User clicks login button
        simulate_button_click(login_button)

        # Step 8: Verify action handler fired and state updated
        assert app.state["logged_in"] is True
        assert app.state["current_user"] == "admin"
        assert app.current_view == "dashboard"

        # Step 9: Verify dashboard renders correctly
        output, _ = render_view(app, "dashboard")
        rendered_text = get_rendered_text(app)
        assert "Welcome, admin" in rendered_text

    def test_failed_login_flow(self):
        """Test end-to-end failed login flow.

        Journey:
        1. App displays login form
        2. User enters invalid credentials
        3. User clicks login button
        4. App shows error message
        5. User remains on login page
        """
        app = Wijjit(
            initial_state={
                "logged_in": False,
                "current_user": None,
                "login_error": None,
            }
        )

        # Register action handler for login button
        @app.on_action("login")
        def handle_login(event: ActionEvent):
            username = app.state.get("username", "")
            password = app.state.get("password", "")

            if username == "admin" and password == "secret":
                app.state["logged_in"] = True
                app.state["current_user"] = username
                app.navigate("dashboard")
            else:
                app.state["login_error"] = "Invalid credentials"

        # Define login view
        @app.view("login", default=True)
        def login_view():
            return {
                "template": """
{% frame width=45 height=15 title="Login" %}
    {% if login_error %}
        Error: {{ login_error }}
    {% endif %}

    Username:
    {% textinput id="username" bind=True %}{% endtextinput %}

    Password:
    {% textinput id="password" bind=True %}{% endtextinput %}

    {% button id="login_btn" action="login" %}Login{% endbutton %}
{% endframe %}
                """
            }

        # Step 1: Verify initial state
        assert app.current_view == "login"
        assert not app.state["logged_in"]

        # Step 2: Render and get elements
        output, elements = render_view(app, "login")
        username_input = get_element_by_id(elements, "username")
        password_input = get_element_by_id(elements, "password")
        login_button = get_element_by_id(elements, "login_btn")

        # Step 3: User enters invalid credentials
        simulate_typing(username_input, "wronguser")
        simulate_typing(password_input, "wrongpass")

        # Step 4: User clicks login button
        simulate_button_click(login_button)

        # Step 5: Verify error state and no navigation
        assert app.state["login_error"] == "Invalid credentials"
        assert not app.state["logged_in"]
        assert app.current_view == "login"  # Still on login page

        # Verify error message appears when re-rendered
        output, _ = render_view(app, "login")
        rendered_text = get_rendered_text(app)
        assert "Invalid credentials" in rendered_text


class TestRegistrationFormJourney:
    """Test complete registration form user journey."""

    def test_successful_registration_flow(self):
        """Test end-to-end registration flow.

        Journey:
        1. Display registration form
        2. User fills out all required fields
        3. User clicks register button
        4. App validates form data
        5. App creates account
        6. App navigates to success page
        """
        app = Wijjit(
            initial_state={
                "registration_complete": False,
                "validation_errors": [],
                "new_user": None,
            }
        )

        # Register action handler with validation
        @app.on_action("register")
        def handle_register(event: ActionEvent):
            username = app.state.get("username", "")
            email = app.state.get("email", "")
            password = app.state.get("password", "")

            # Validate form data
            validation_errors = []
            if not username:
                validation_errors.append("Username required")
            if not email or "@" not in email:
                validation_errors.append("Valid email required")
            if not password or len(password) < 6:
                validation_errors.append("Password must be at least 6 characters")

            if not validation_errors:
                app.state["registration_complete"] = True
                app.state["new_user"] = username
                app.navigate("success")
            else:
                app.state["validation_errors"] = validation_errors

        # Define views
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

    Username:
    {% textinput id="username" bind=True %}{% endtextinput %}

    Email:
    {% textinput id="email" bind=True %}{% endtextinput %}

    Password:
    {% textinput id="password" bind=True %}{% endtextinput %}

    {% button id="register_btn" action="register" %}Register{% endbutton %}
{% endframe %}
                """
            }

        @app.view("success")
        def success_view():
            return {
                "template": """
{% frame width=50 height=10 title="Success" %}
    Registration successful for {{ new_user }}!
{% endframe %}
                """
            }

        # Step 1: Verify initial state
        assert app.current_view == "register"

        # Step 2: Render and get elements
        output, elements = render_view(app, "register")
        username_input = get_element_by_id(elements, "username")
        email_input = get_element_by_id(elements, "email")
        password_input = get_element_by_id(elements, "password")
        register_button = get_element_by_id(elements, "register_btn")

        # Step 3: User fills out all fields
        simulate_typing(username_input, "newuser")
        simulate_typing(email_input, "user@example.com")
        simulate_typing(password_input, "secure123")

        # Verify state binding worked
        assert app.state["username"] == "newuser"
        assert app.state["email"] == "user@example.com"
        assert app.state["password"] == "secure123"

        # Step 4: User clicks register button
        simulate_button_click(register_button)

        # Step 5 & 6: Verify validation passed and navigation occurred
        assert len(app.state["validation_errors"]) == 0
        assert app.state["registration_complete"] is True
        assert app.state["new_user"] == "newuser"
        assert app.current_view == "success"

        # Verify success message renders
        output, _ = render_view(app, "success")
        rendered_text = get_rendered_text(app)
        assert "Registration successful for newuser" in rendered_text


class TestMultiStepFormJourney:
    """Test multi-step form wizard journey."""

    def test_complete_wizard_flow(self):
        """Test complete multi-step wizard.

        Journey:
        1. Start at step 1 (personal info)
        2. User clicks Next to proceed to step 2
        3. User clicks Next to proceed to step 3
        4. User clicks Submit
        5. App navigates to confirmation
        """
        app = Wijjit(
            initial_state={"wizard_step": 1, "form_data": {}, "submitted": False}
        )

        # Register action handlers for wizard navigation
        @app.on_action("next1")
        def handle_next1(event: ActionEvent):
            app.state["wizard_step"] = 2

        @app.on_action("next2")
        def handle_next2(event: ActionEvent):
            app.state["wizard_step"] = 3

        @app.on_action("submit")
        def handle_submit(event: ActionEvent):
            app.state["submitted"] = True
            app.navigate("confirmation")

        # Define views
        @app.view("wizard", default=True)
        def wizard_view():
            template = """
{% frame width=50 height=15 title="Wizard - Step {{ wizard_step }}" %}
{% if wizard_step == 1 %}
    Step 1: Personal Info
    {% button id="next1_btn" action="next1" %}Next{% endbutton %}
{% elif wizard_step == 2 %}
    Step 2: Address
    {% button id="next2_btn" action="next2" %}Next{% endbutton %}
{% elif wizard_step == 3 %}
    Step 3: Review
    {% button id="submit_btn" action="submit" %}Submit{% endbutton %}
{% endif %}
{% endframe %}
            """
            return {"template": template}

        @app.view("confirmation")
        def confirmation_view():
            return {
                "template": """
{% frame width=50 height=10 title="Confirmation" %}
    Thank you! Your submission is complete.
{% endframe %}
                """
            }

        # Step 1: Verify initial state
        assert app.state["wizard_step"] == 1

        # Step 2: Render step 1 and click Next
        output, elements = render_view(app, "wizard")
        rendered_text = get_rendered_text(app)
        assert "Step 1: Personal Info" in rendered_text
        next1_button = get_element_by_id(elements, "next1_btn")
        assert next1_button is not None
        simulate_button_click(next1_button)

        # Verify moved to step 2
        assert app.state["wizard_step"] == 2

        # Step 3: Re-render for step 2 and click Next
        output, elements = render_view(app, "wizard")
        rendered_text = get_rendered_text(app)
        assert "Step 2: Address" in rendered_text
        next2_button = get_element_by_id(elements, "next2_btn")
        assert next2_button is not None
        simulate_button_click(next2_button)

        # Verify moved to step 3
        assert app.state["wizard_step"] == 3

        # Step 4: Re-render for step 3 and click Submit
        output, elements = render_view(app, "wizard")
        rendered_text = get_rendered_text(app)
        assert "Step 3: Review" in rendered_text
        submit_button = get_element_by_id(elements, "submit_btn")
        assert submit_button is not None
        simulate_button_click(submit_button)

        # Step 5: Verify submission and navigation
        assert app.state["submitted"] is True
        assert app.current_view == "confirmation"

        # Verify confirmation message
        output, _ = render_view(app, "confirmation")
        rendered_text = get_rendered_text(app)
        assert "Thank you! Your submission is complete." in rendered_text


class TestFormValidationJourney:
    """Test form validation throughout user journey."""

    def test_inline_validation_flow(self):
        """Test real-time validation during form entry.

        Journey:
        1. User starts entering email
        2. Validation checks format after each keystroke
        3. Error shown for invalid format
        4. User corrects email
        5. Validation passes
        6. Form can be submitted
        """
        app = Wijjit(
            initial_state={"email": "", "email_error": None, "can_submit": False}
        )

        # Set up state change listener for validation
        def validate_email(key, old_value, new_value):
            if key == "email":
                if new_value and "@" not in new_value:
                    app.state["email_error"] = "Invalid email format"
                    app.state["can_submit"] = False
                elif new_value and "@" in new_value:
                    app.state["email_error"] = None
                    app.state["can_submit"] = True
                else:
                    app.state["email_error"] = None
                    app.state["can_submit"] = False

        app.state.on_change(validate_email)

        @app.view("form", default=True)
        def form_view():
            return {
                "template": """
{% frame width=40 height=10 title="Email Form" %}
    Email:
    {% textinput id="email" bind=True %}{% endtextinput %}

    {% if email_error %}
        Error: {{ email_error }}
    {% endif %}

    {% button id="submit_btn" action="submit" %}Submit{% endbutton %}
{% endframe %}
                """
            }

        # Render form
        output, elements = render_view(app, "form")
        email_input = get_element_by_id(elements, "email")
        submit_button = get_element_by_id(elements, "submit_btn")

        # Step 1-3: User types invalid email
        simulate_typing(email_input, "notanemail")

        # Verify validation error set
        assert app.state["email"] == "notanemail"
        assert app.state["email_error"] == "Invalid email format"
        assert app.state["can_submit"] is False

        # Re-render to verify error message appears
        output, _ = render_view(app, "form")
        rendered_text = get_rendered_text(app)
        assert "Invalid email format" in rendered_text

        # Step 4-5: User corrects email (clear and retype)
        email_input.value = ""  # Clear the field
        app.state["email"] = ""  # Clear state

        simulate_typing(email_input, "valid@example.com")

        # Verify validation passes
        assert app.state["email"] == "valid@example.com"
        assert app.state["email_error"] is None
        assert app.state["can_submit"] is True

        # Re-render to verify no error shown
        output, _ = render_view(app, "form")
        rendered_text = get_rendered_text(app)
        assert "Invalid email format" not in rendered_text


class TestFormNavigationJourney:
    """Test navigation within and between forms."""

    def test_form_to_form_navigation(self):
        """Test navigating between different forms.

        Journey:
        1. User fills out contact form
        2. User clicks Next to navigate to preferences
        3. User fills preferences form
        4. User clicks Review to navigate to review page
        5. Data from both forms persists and displays
        """
        app = Wijjit(initial_state={"name": "", "email": "", "theme": "", "notify": ""})

        # Register navigation actions
        @app.on_action("go_to_preferences")
        def go_to_preferences(event: ActionEvent):
            app.navigate("preferences")

        @app.on_action("go_to_review")
        def go_to_review(event: ActionEvent):
            app.navigate("review")

        # Define views
        @app.view("contact", default=True)
        def contact_view():
            return {
                "template": """
{% frame width=50 height=12 title="Contact Form" %}
    Name:
    {% textinput id="name" bind=True %}{% endtextinput %}

    Email:
    {% textinput id="email" bind=True %}{% endtextinput %}

    {% button id="next_btn" action="go_to_preferences" %}Next{% endbutton %}
{% endframe %}
                """
            }

        @app.view("preferences")
        def preferences_view():
            return {
                "template": """
{% frame width=50 height=12 title="Preferences" %}
    Theme:
    {% textinput id="theme" bind=True %}{% endtextinput %}

    Notifications:
    {% textinput id="notify" bind=True %}{% endtextinput %}

    {% button id="review_btn" action="go_to_review" %}Review{% endbutton %}
{% endframe %}
                """
            }

        @app.view("review")
        def review_view():
            return {
                "template": """
{% frame width=50 height=15 title="Review" %}
    Contact Info:
    Name: {{ name }}
    Email: {{ email }}

    Preferences:
    Theme: {{ theme }}
    Notify: {{ notify }}
{% endframe %}
                """
            }

        # Step 1: Fill contact form
        output, elements = render_view(app, "contact")
        name_input = get_element_by_id(elements, "name")
        email_input = get_element_by_id(elements, "email")
        next_button = get_element_by_id(elements, "next_btn")

        simulate_typing(name_input, "Alice")
        simulate_typing(email_input, "alice@example.com")

        assert app.state["name"] == "Alice"
        assert app.state["email"] == "alice@example.com"

        # Step 2: Navigate to preferences
        simulate_button_click(next_button)
        assert app.current_view == "preferences"

        # Step 3: Fill preferences form
        output, elements = render_view(app, "preferences")
        theme_input = get_element_by_id(elements, "theme")
        notify_input = get_element_by_id(elements, "notify")
        review_button = get_element_by_id(elements, "review_btn")

        simulate_typing(theme_input, "dark")
        simulate_typing(notify_input, "yes")

        assert app.state["theme"] == "dark"
        assert app.state["notify"] == "yes"

        # Step 4: Navigate to review
        simulate_button_click(review_button)
        assert app.current_view == "review"

        # Step 5: Verify all data persists in review
        output, _ = render_view(app, "review")
        rendered_text = get_rendered_text(app)
        assert "Alice" in rendered_text
        assert "alice@example.com" in rendered_text
        assert "dark" in rendered_text
        assert "yes" in rendered_text


class TestFormWithDynamicContent:
    """Test forms with dynamic content based on selections."""

    def test_conditional_form_fields(self):
        """Test form with conditional field visibility.

        Journey:
        1. User selects business account type
        2. Additional business fields appear
        3. User fills type-specific fields
        4. Form state contains correct data structure
        """
        app = Wijjit(
            initial_state={
                "account_type": "",
                "business_name": "",
                "tax_id": "",
            }
        )

        # Register action for account type selection
        @app.on_action("select_business")
        def select_business(event: ActionEvent):
            app.state["account_type"] = "business"

        @app.view("signup", default=True)
        def signup_view():
            template = """
{% frame width=50 height=15 title="Account Signup" %}
    Account Type: {{ account_type or "Not selected" }}

    {% if not account_type %}
        {% button id="business_btn" action="select_business" %}Business Account{% endbutton %}
    {% endif %}

    {% if account_type == "business" %}
        Business Name:
        {% textinput id="business_name" bind=True %}{% endtextinput %}

        Tax ID:
        {% textinput id="tax_id" bind=True %}{% endtextinput %}
    {% endif %}
{% endframe %}
            """
            return {"template": template}

        # Step 1: Render initial form (no account type selected)
        output, elements = render_view(app, "signup")
        rendered_text = get_rendered_text(app)
        assert "Not selected" in rendered_text
        business_button = get_element_by_id(elements, "business_btn")
        assert business_button is not None

        # User selects business account type
        simulate_button_click(business_button)
        assert app.state["account_type"] == "business"

        # Step 2: Re-render to show business fields
        output, elements = render_view(app, "signup")
        rendered_text = get_rendered_text(app)
        assert "Business Name:" in rendered_text
        assert "Tax ID:" in rendered_text

        # Verify business fields are now available
        business_name_input = get_element_by_id(elements, "business_name")
        tax_id_input = get_element_by_id(elements, "tax_id")
        assert business_name_input is not None
        assert tax_id_input is not None

        # Step 3: Fill business-specific fields
        simulate_typing(business_name_input, "Acme Corp")
        simulate_typing(tax_id_input, "12-3456789")

        # Step 4: Verify data structure
        assert app.state["account_type"] == "business"
        assert app.state["business_name"] == "Acme Corp"
        assert app.state["tax_id"] == "12-3456789"
