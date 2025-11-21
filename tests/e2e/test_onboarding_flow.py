"""End-to-end onboarding wizard tests.

These tests cover a multi-view onboarding journey that exercises
navigation, validation, focus handling, and state binding end to end.
"""

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.events import ActionEvent
from wijjit.terminal.input import Keys

from .helpers import (
    assert_element_focused,
    get_element_by_id,
    get_rendered_text,
    render_view,
    simulate_button_click,
    simulate_key_press,
    simulate_tab_navigation,
    simulate_typing,
)

pytestmark = pytest.mark.e2e


def build_onboarding_app() -> Wijjit:
    """Create a Wijjit app configured with a multi-step onboarding flow."""
    app = Wijjit(
        initial_state={
            "step": "welcome",
            "full_name": "",
            "email": "",
            "team_size": "",
            "wants_updates": False,
            "profile_error": "",
            "preferences_error": "",
            "completed": False,
        }
    )

    @app.on_action("start_onboarding")
    def start_onboarding(event: ActionEvent) -> None:
        app.state["step"] = "profile"
        app.navigate("profile")

    @app.on_action("profile_continue")
    def profile_continue(event: ActionEvent) -> None:
        name = app.state.get("full_name", "").strip()
        email = app.state.get("email", "").strip()
        if not name or not email:
            app.state["profile_error"] = "Please provide name and email"
            return
        app.state["profile_error"] = ""
        app.state["step"] = "preferences"
        app.navigate("preferences")

    @app.on_action("preferences_continue")
    def preferences_continue(event: ActionEvent) -> None:
        team_size = app.state.get("team_size", "").strip()
        if not team_size.isdigit():
            app.state["preferences_error"] = "Team size must be numeric"
            return
        app.state["preferences_error"] = ""
        app.state["step"] = "review"
        app.navigate("review")

    @app.on_action("complete_onboarding")
    def complete_onboarding(event: ActionEvent) -> None:
        app.state["completed"] = True
        app.state["step"] = "dashboard"
        app.navigate("dashboard")

    @app.view("welcome", default=True)
    def welcome_view():
        return {
            "template": """
{% frame title="Welcome" width=60 height=10 %}
    {% vstack spacing=1 %}
        Ready to set up your workspace?
        {% button id="start_button" action="start_onboarding" %}Start onboarding{% endbutton %}
    {% endvstack %}
{% endframe %}
            """
        }

    @app.view("profile")
    def profile_view():
        return {
            "template": """
{% frame title="Profile" width=70 height=18 %}
    {% vstack spacing=1 %}
        Tell us about yourself
        {% textinput id="full_name" bind=True placeholder="Full name" width=40 %}{% endtextinput %}
        {% textinput id="email" bind=True placeholder="you@example.com" width=40 %}{% endtextinput %}
        {% if profile_error %}
            Error: {{ profile_error }}
        {% endif %}
        {% button id="profile_next" action="profile_continue" %}Continue{% endbutton %}
    {% endvstack %}
{% endframe %}
            """
        }

    @app.view("preferences")
    def preferences_view():
        return {
            "template": """
{% frame title="Preferences" width=70 height=18 %}
    {% vstack spacing=1 %}
        Team size
        {% textinput id="team_size" bind=True placeholder="e.g. 8" width=10 %}{% endtextinput %}
        {% checkbox id="wants_updates" bind=True label="Send me product updates" %}{% endcheckbox %}
        {% if preferences_error %}
            Error: {{ preferences_error }}
        {% endif %}
        {% button id="preferences_next" action="preferences_continue" %}Continue{% endbutton %}
    {% endvstack %}
{% endframe %}
            """
        }

    @app.view("review")
    def review_view():
        return {
            "template": """
{% frame title="Review" width=70 height=18 %}
    {% vstack spacing=1 %}
        Name: {{ full_name }}
        Email: {{ email }}
        Team size: {{ team_size }}
        Updates: {{ "Yes" if wants_updates else "No" }}
        {% button id="finish_button" action="complete_onboarding" %}Finish setup{% endbutton %}
    {% endvstack %}
{% endframe %}
            """
        }

    @app.view("dashboard")
    def dashboard_view():
        return {
            "template": """
{% frame title="Dashboard" width=60 height=10 %}
    Welcome {{ full_name }}! Setup complete.
{% endframe %}
            """
        }

    return app


class TestOnboardingFlow:
    """End-to-end coverage for the onboarding wizard."""

    def test_successful_onboarding_journey(self):
        """Simulate the entire onboarding flow end to end."""
        app = build_onboarding_app()

        # Welcome -> Profile
        output, elements = render_view(app, "welcome")
        start_button = get_element_by_id(elements, "start_button")
        assert start_button is not None, "Start button should exist"
        simulate_button_click(start_button)
        assert app.current_view == "profile"

        # Profile input and validation
        output, elements = render_view(app, "profile")
        name_input = get_element_by_id(elements, "full_name")
        email_input = get_element_by_id(elements, "email")
        profile_next = get_element_by_id(elements, "profile_next")
        assert name_input is not None and email_input is not None
        assert profile_next is not None

        simulate_typing(name_input, "Avery Admin")
        assert app.state["full_name"] == "Avery Admin"

        simulate_tab_navigation(app)  # move focus forward
        simulate_typing(email_input, "avery@example.com")
        assert app.state["email"] == "avery@example.com"

        simulate_tab_navigation(app)  # move to button
        assert_element_focused(app, "profile_next")
        simulate_button_click(profile_next)
        assert app.current_view == "preferences"

        # Preferences input
        output, elements = render_view(app, "preferences")
        team_input = get_element_by_id(elements, "team_size")
        updates_toggle = get_element_by_id(elements, "wants_updates")
        preferences_next = get_element_by_id(elements, "preferences_next")

        assert team_input is not None and updates_toggle is not None
        assert preferences_next is not None

        simulate_typing(team_input, "12")
        assert app.state["team_size"] == "12"

        simulate_key_press(updates_toggle, Keys.SPACE)
        assert app.state["wants_updates"] is True

        simulate_button_click(preferences_next)
        assert app.current_view == "review"

        # Review -> Dashboard
        output, elements = render_view(app, "review")
        review_text = get_rendered_text(app)
        assert "Avery Admin" in review_text
        assert "avery@example.com" in review_text
        assert "Team size: 12" in review_text

        finish_button = get_element_by_id(elements, "finish_button")
        assert finish_button is not None
        simulate_button_click(finish_button)
        assert app.current_view == "dashboard"
        assert app.state["completed"] is True

        output, _ = render_view(app, "dashboard")
        rendered_text = get_rendered_text(app)
        assert "Welcome Avery Admin" in rendered_text

    def test_profile_validation_blocks_progress(self):
        """Missing profile data should surface validation errors."""
        app = build_onboarding_app()

        # Enter profile step
        render_view(app, "welcome")
        start_button = get_element_by_id(app.positioned_elements, "start_button")
        assert start_button is not None
        simulate_button_click(start_button)
        assert app.current_view == "profile"

        output, elements = render_view(app, "profile")
        profile_next = get_element_by_id(elements, "profile_next")
        assert profile_next is not None

        simulate_button_click(profile_next)
        assert app.current_view == "profile", "Should remain on profile when invalid"
        assert app.state["profile_error"] == "Please provide name and email"

        render_view(app, "profile")
        plain_text = get_rendered_text(app)
        assert "Please provide name and email" in plain_text
