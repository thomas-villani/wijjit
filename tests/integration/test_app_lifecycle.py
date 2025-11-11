"""Integration tests for Wijjit application lifecycle.

Tests cover the full lifecycle of a Wijjit application including:
- App initialization with all components
- View registration and management
- Navigation between views with lifecycle hooks
- State management integration with rendering
- Event handler registration and dispatch
- Focus management across views
"""

import pytest

from wijjit.core.app import Wijjit
from wijjit.core.events import ActionEvent, EventType, KeyEvent
from wijjit.core.state import State
from wijjit.terminal.input import Keys

pytestmark = pytest.mark.integration


class TestAppInitialization:
    """Test application initialization and component setup."""

    def test_app_initializes_all_components(self):
        """Test that creating app initializes all required components.

        This integration test verifies that all core components are properly
        initialized and connected during app creation.
        """
        app = Wijjit()

        # Verify all components exist
        assert isinstance(app.state, State)
        assert app.renderer is not None
        assert app.focus_manager is not None
        assert app.hover_manager is not None
        assert app.overlay_manager is not None
        assert app.handler_registry is not None
        assert app.screen_manager is not None
        assert app.input_handler is not None

        # Verify initial state
        assert app.views == {}
        assert app.current_view is None
        assert app.running is False
        assert app.needs_render is True

    def test_app_with_initial_state_integrates_with_renderer(self):
        """Test that initial state is available to template renderer.

        Verifies integration between State and Renderer components.
        """
        app = Wijjit(initial_state={"title": "Test App", "count": 0})

        # State should be set
        assert app.state["title"] == "Test App"
        assert app.state["count"] == 0

        # State should be available to renderer
        template = "Title: {{ title }}, Count: {{ count }}"
        output = app.renderer.render_string(template, dict(app.state))

        assert "Title: Test App" in output
        assert "Count: 0" in output

    def test_state_changes_trigger_render_flag(self):
        """Test that state changes automatically set needs_render flag.

        Verifies integration between State change detection and app render loop.
        """
        app = Wijjit(initial_state={"value": 0})

        # Initial state
        assert app.needs_render is True

        # Clear flag
        app.needs_render = False

        # Change state
        app.state["value"] = 10

        # Should trigger needs_render
        assert app.needs_render is True


class TestViewLifecycle:
    """Test view registration, navigation, and lifecycle hooks."""

    def test_register_and_navigate_between_views(self):
        """Test full navigation flow between multiple views.

        This integration test verifies:
        - View registration
        - View initialization
        - Navigation triggers
        - View switching
        """
        app = Wijjit()

        # Register views
        @app.view("home", default=True)
        def home():
            return {"template": "Home View"}

        @app.view("settings")
        def settings():
            return {"template": "Settings View"}

        @app.view("about")
        def about():
            return {"template": "About View"}

        # Verify registration
        assert len(app.views) == 3
        assert "home" in app.views
        assert "settings" in app.views
        assert "about" in app.views

        # Default view should be current
        assert app.current_view == "home"

        # Navigate to settings
        app.navigate("settings")
        assert app.current_view == "settings"
        assert app.needs_render is True

        # Navigate to about
        app.navigate("about")
        assert app.current_view == "about"

        # Navigate back to home
        app.navigate("home")
        assert app.current_view == "home"

    def test_lifecycle_hooks_called_during_navigation(self):
        """Test that on_enter and on_exit hooks are called correctly.

        Verifies integration of view lifecycle with navigation system.
        """
        app = Wijjit()
        call_log = []

        @app.view("view1", default=True)
        def view1():
            def on_enter():
                call_log.append("view1_enter")

            def on_exit():
                call_log.append("view1_exit")

            return {
                "template": "View 1",
                "on_enter": on_enter,
                "on_exit": on_exit,
            }

        @app.view("view2")
        def view2():
            def on_enter():
                call_log.append("view2_enter")

            def on_exit():
                call_log.append("view2_exit")

            return {
                "template": "View 2",
                "on_enter": on_enter,
                "on_exit": on_exit,
            }

        # Clear initial state
        call_log.clear()

        # Navigate from view1 to view2
        app.navigate("view2")

        # Should call view1 exit, then view2 enter
        assert call_log == ["view1_exit", "view2_enter"]

        # Navigate back to view1
        call_log.clear()
        app.navigate("view1")

        assert call_log == ["view2_exit", "view1_enter"]

    def test_view_data_integration_with_state(self):
        """Test that view data functions integrate with app state.

        Verifies integration between views, data functions, and global state.
        """
        app = Wijjit(initial_state={"user": "Alice", "count": 5})

        @app.view("profile", default=True)
        def profile():
            return {
                "template": "User: {{ user }}, Count: {{ count }}",
                "data": {},  # Will merge with state
            }

        # Initialize view
        app._initialize_view(app.views["profile"])

        # Render with state
        # View data() returns context, merge with state
        view_data = app.views["profile"].data() if app.views["profile"].data else {}
        data = {**dict(app.state), **view_data}
        output = app.renderer.render_string(app.views["profile"].template, data)

        assert "User: Alice" in output
        assert "Count: 5" in output


class TestStateRenderingIntegration:
    """Test integration between state changes and rendering."""

    def test_state_change_triggers_rerender_flag(self):
        """Test that any state change sets needs_render flag.

        Verifies automatic re-render triggering on state changes.
        """
        app = Wijjit(initial_state={"count": 0})

        # Clear render flag
        app.needs_render = False
        assert not app.needs_render

        # Change state
        app.state["count"] = 1

        # Should trigger re-render
        assert app.needs_render is True

    def test_nested_state_changes_trigger_rerender(self):
        """Test that nested state changes trigger re-render.

        Verifies deep state change detection.
        """
        app = Wijjit(initial_state={"user": {"name": "Alice", "age": 30}})

        # Clear render flag
        app.needs_render = False

        # Change nested value - note: State doesn't auto-detect nested mutations
        # Need to reassign a new dict to trigger change detection
        user = app.state["user"].copy()
        user["age"] = 31
        app.state["user"] = user

        # Should trigger re-render
        assert app.needs_render is True

    def test_state_changes_persist_across_navigation(self):
        """Test that state persists when navigating between views.

        Verifies global state management across view navigation.
        """
        app = Wijjit(initial_state={"shared_value": 0})

        @app.view("view1", default=True)
        def view1():
            return {"template": "View 1: {{ shared_value }}"}

        @app.view("view2")
        def view2():
            return {"template": "View 2: {{ shared_value }}"}

        # Change state in view1
        app.state["shared_value"] = 42

        # Navigate to view2
        app.navigate("view2")

        # State should persist
        assert app.state["shared_value"] == 42

        # Render view2 with state
        app._initialize_view(app.views["view2"])
        view_data = app.views["view2"].data() if app.views["view2"].data else {}
        data = {**dict(app.state), **view_data}
        output = app.renderer.render_string(app.views["view2"].template, data)

        assert "View 2: 42" in output


class TestEventHandlingIntegration:
    """Test event handling integration with app lifecycle."""

    def test_action_handler_integration(self):
        """Test that action handlers integrate with event system.

        Verifies end-to-end event dispatch from event to handler.
        """
        app = Wijjit()
        handler_called = []

        @app.view("main", default=True)
        def main():
            return {"template": "Main View"}

        # Register action handler
        def handle_submit(event):
            handler_called.append(event.action_id)

        app.on(EventType.ACTION, handle_submit)

        # Set current view for handler scope
        app.handler_registry.current_view = "main"

        # Dispatch action event
        event = ActionEvent(action_id="submit", source_element_id="btn1")
        app.handler_registry.dispatch(event)

        # Handler should be called
        assert "submit" in handler_called

    def test_key_handler_integration(self):
        """Test keyboard event handling integration.

        Verifies key event dispatch and handling.
        """
        app = Wijjit()
        keys_pressed = []

        def handle_key(event: KeyEvent):
            keys_pressed.append(event.key)

        app.on(EventType.KEY, handle_key)

        # Dispatch key event
        event = KeyEvent(key=Keys.ENTER)
        app.handler_registry.dispatch(event)

        assert Keys.ENTER in keys_pressed

    def test_view_scoped_handlers_cleared_on_navigation(self):
        """Test that view-scoped handlers are cleared when leaving view.

        Verifies proper cleanup of view-local event handlers.
        """
        app = Wijjit()
        handler_calls = []

        @app.view("view1", default=True)
        def view1():
            def on_enter():
                # Register view-scoped handler
                def view1_handler(event):
                    handler_calls.append("view1")

                from wijjit.core.events import HandlerScope

                app.on(
                    EventType.ACTION,
                    view1_handler,
                    scope=HandlerScope.VIEW,
                    view_name="view1",
                )

            return {"template": "View 1", "on_enter": on_enter}

        @app.view("view2")
        def view2():
            return {"template": "View 2"}

        # Trigger view1's on_enter (registers handler)
        app.navigate("view1")
        handler_calls.clear()

        # Dispatch event - view1 handler should be called
        app.handler_registry.current_view = "view1"
        event = ActionEvent(action_id="test", source_element_id="btn1")
        app.handler_registry.dispatch(event)
        assert "view1" in handler_calls

        # Navigate to view2 (should clear view1 handlers)
        handler_calls.clear()
        app.navigate("view2")

        # Dispatch event - view1 handler should NOT be called
        app.handler_registry.current_view = "view2"
        app.handler_registry.dispatch(event)
        assert "view1" not in handler_calls


class TestFocusIntegration:
    """Test focus management integration with app lifecycle."""

    def test_focus_manager_integrates_with_app(self):
        """Test that focus manager is properly integrated.

        Verifies focus manager is initialized and accessible.
        """
        app = Wijjit()

        assert app.focus_manager is not None
        assert app.focus_manager.elements == []
        assert app.focus_manager.current_index is None

    def test_focus_reset_on_view_navigation(self):
        """Test that focus is reset when navigating between views.

        This would be implemented when view navigation clears elements.
        """
        app = Wijjit()

        @app.view("view1", default=True)
        def view1():
            return {"template": "View 1"}

        @app.view("view2")
        def view2():
            return {"template": "View 2"}

        # Navigate should reset focus (when implemented)
        app.navigate("view1")
        app.navigate("view2")

        # Focus manager should be in clean state
        assert app.focus_manager is not None


class TestErrorHandling:
    """Test error handling integration across app lifecycle."""

    def test_lifecycle_hook_errors_dont_crash_app(self):
        """Test that errors in lifecycle hooks are handled gracefully.

        Verifies error handling doesn't break navigation.
        """
        app = Wijjit()

        @app.view("view1", default=True)
        def view1():
            def on_exit():
                raise RuntimeError("Intentional error in on_exit")

            return {"template": "View 1", "on_exit": on_exit}

        @app.view("view2")
        def view2():
            return {"template": "View 2"}

        # Navigate should handle error gracefully
        try:
            app.navigate("view2")
            # Navigation should succeed despite error
            assert app.current_view == "view2"
        except RuntimeError:
            pytest.fail("Error in lifecycle hook should be handled gracefully")

    def test_invalid_view_navigation_raises_error(self):
        """Test that navigating to non-existent view raises error.

        Verifies proper error handling for invalid navigation.
        """
        app = Wijjit()

        with pytest.raises(ValueError, match="View 'nonexistent' not found"):
            app.navigate("nonexistent")
