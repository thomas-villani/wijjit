"""Tests for the main Wijjit application class.

Tests cover:
- App initialization
- View registration with decorator
- View configuration
- Navigation between views
- Lifecycle hooks (on_enter, on_exit)
- Event handler registration
- State change triggering re-render
- Error handling
"""

from unittest.mock import patch

import pytest

from wijjit.core.app import ViewConfig, Wijjit
from wijjit.core.events import EventType, HandlerScope, KeyEvent
from wijjit.core.state import State
from wijjit.terminal.input import Key, KeyType


class TestViewConfig:
    """Tests for ViewConfig dataclass."""

    def test_view_config_creation(self):
        """Test creating a ViewConfig."""

        def data_func():
            return {"name": "World"}

        def on_enter():
            pass

        config = ViewConfig(
            name="main",
            template="Hello {{ name }}!",
            data=data_func,
            on_enter=on_enter,
            is_default=True,
        )

        assert config.name == "main"
        assert config.template == "Hello {{ name }}!"
        assert config.data == data_func
        assert config.on_enter == on_enter
        assert config.is_default is True

    def test_view_config_minimal(self):
        """Test ViewConfig with minimal fields."""
        config = ViewConfig(
            name="simple",
            template="Simple view",
        )

        assert config.name == "simple"
        assert config.template == "Simple view"
        assert config.data is None
        assert config.on_enter is None
        assert config.on_exit is None
        assert config.is_default is False


class TestWijjitInit:
    """Tests for Wijjit initialization."""

    def test_app_initialization(self):
        """Test creating a Wijjit app."""
        app = Wijjit()

        assert isinstance(app.state, State)
        assert app.renderer is not None
        assert app.focus_manager is not None
        assert app.handler_registry is not None
        assert app.screen_manager is not None
        assert app.input_handler is not None
        assert app.views == {}
        assert app.current_view is None
        assert app.running is False
        assert app.needs_render is True

    def test_app_with_initial_state(self):
        """Test app with initial state."""
        app = Wijjit(initial_state={"count": 0})

        assert app.state["count"] == 0

    def test_app_with_template_dir(self):
        """Test app with template directory."""
        import tempfile

        # Create a temporary directory for templates
        with tempfile.TemporaryDirectory() as tmpdir:
            app = Wijjit(template_dir=tmpdir)

            # Renderer should be initialized with file loader
            assert app.renderer is not None
            assert app.renderer.using_file_loader is True
            assert app.renderer.template_dir == tmpdir

    def test_app_with_invalid_template_dir(self):
        """Test app with non-existent template directory raises error."""
        import pytest

        with pytest.raises(
            FileNotFoundError, match="Template directory.*does not exist"
        ):
            Wijjit(template_dir="/nonexistent/templates")


class TestViewRegistration:
    """Tests for view registration."""

    def test_register_view_with_decorator(self):
        """Test registering a view using decorator."""
        app = Wijjit()

        @app.view("main")
        def main_view():
            return {
                "template": "Hello World!",
            }

        assert "main" in app.views
        assert app.views["main"].name == "main"

        # Initialize view to access properties
        app._initialize_view(app.views["main"])
        assert app.views["main"].template == "Hello World!"

    def test_register_view_with_data(self):
        """Test registering a view with data function."""
        app = Wijjit()

        @app.view("greeting")
        def greeting_view():
            return {
                "template": "Hello {{ name }}!",
                "data": {"name": "Alice"},
            }

        assert "greeting" in app.views
        view = app.views["greeting"]

        # Initialize view to access properties
        app._initialize_view(view)
        assert view.data is not None

        # Data function should return the data dict
        data = view.data()
        assert data == {"name": "Alice"}

    def test_register_default_view(self):
        """Test registering a default view."""
        app = Wijjit()

        @app.view("main", default=True)
        def main_view():
            return {"template": "Main"}

        assert app.views["main"].is_default is True
        assert app.current_view == "main"

    def test_register_view_with_lifecycle_hooks(self):
        """Test registering a view with lifecycle hooks."""
        app = Wijjit()
        entered = []
        exited = []

        def on_enter():
            entered.append(True)

        def on_exit():
            exited.append(True)

        @app.view("hookview")
        def hook_view():
            return {
                "template": "View with hooks",
                "on_enter": on_enter,
                "on_exit": on_exit,
            }

        view = app.views["hookview"]

        # Initialize view to access properties
        app._initialize_view(view)
        assert view.on_enter is not None
        assert view.on_exit is not None

    def test_multiple_views(self):
        """Test registering multiple views."""
        app = Wijjit()

        @app.view("view1")
        def view1():
            return {"template": "View 1"}

        @app.view("view2")
        def view2():
            return {"template": "View 2"}

        assert len(app.views) == 2
        assert "view1" in app.views
        assert "view2" in app.views


class TestNavigation:
    """Tests for navigation between views."""

    def test_navigate_to_view(self):
        """Test navigating to a different view."""
        app = Wijjit()

        @app.view("view1", default=True)
        def view1():
            return {"template": "View 1"}

        @app.view("view2")
        def view2():
            return {"template": "View 2"}

        assert app.current_view == "view1"

        app.navigate("view2")

        assert app.current_view == "view2"
        assert app.needs_render is True

    def test_navigate_to_nonexistent_view(self):
        """Test navigating to a view that doesn't exist."""
        app = Wijjit()

        @app.view("view1")
        def view1():
            return {"template": "View 1"}

        with pytest.raises(ValueError, match="View 'nonexistent' not found"):
            app.navigate("nonexistent")

    def test_navigate_calls_lifecycle_hooks(self):
        """Test that navigation calls on_exit and on_enter hooks."""
        app = Wijjit()
        hooks_called = []

        def view1_enter():
            hooks_called.append("view1_enter")

        def view1_exit():
            hooks_called.append("view1_exit")

        def view2_enter():
            hooks_called.append("view2_enter")

        def view2_exit():
            hooks_called.append("view2_exit")

        @app.view("view1", default=True)
        def view1():
            return {
                "template": "View 1",
                "on_enter": view1_enter,
                "on_exit": view1_exit,
            }

        @app.view("view2")
        def view2():
            return {
                "template": "View 2",
                "on_enter": view2_enter,
                "on_exit": view2_exit,
            }

        # Navigate to view2
        app.navigate("view2")

        # Should have called view1_exit and view2_enter
        assert "view1_exit" in hooks_called
        assert "view2_enter" in hooks_called

    def test_navigate_clears_view_handlers(self):
        """Test that navigation clears view-scoped handlers."""
        app = Wijjit()

        @app.view("view1", default=True)
        def view1():
            return {"template": "View 1"}

        @app.view("view2")
        def view2():
            return {"template": "View 2"}

        # Register a view-scoped handler for view1
        def handler(event):
            pass

        app.handler_registry.register(
            callback=handler,
            scope=HandlerScope.VIEW,
            view_name="view1",
        )

        # Verify the view-scoped handler was registered
        view1_handlers_before = [
            h
            for h in app.handler_registry.handlers
            if h.scope == HandlerScope.VIEW and h.view_name == "view1"
        ]
        assert len(view1_handlers_before) == 1

        # Navigate to view2
        app.navigate("view2")

        # View1 handlers should be cleared
        # Check that no handlers are for view1
        view1_handlers = [
            h
            for h in app.handler_registry.handlers
            if h.scope == HandlerScope.VIEW and h.view_name == "view1"
        ]
        assert len(view1_handlers) == 0

    def test_navigate_with_params(self):
        """Test navigating with parameters."""
        app = Wijjit()

        @app.view("view1")
        def view1():
            return {"template": "View 1"}

        app.navigate("view1", user_id=123)

        assert app.current_view_params == {"user_id": 123}

    def test_navigate_updates_handler_registry_view(self):
        """Test that navigation updates the handler registry's current view."""
        app = Wijjit()

        @app.view("view1", default=True)
        def view1():
            return {"template": "View 1"}

        @app.view("view2")
        def view2():
            return {"template": "View 2"}

        app.navigate("view2")

        assert app.handler_registry.current_view == "view2"


class TestEventHandlers:
    """Tests for event handler registration."""

    def test_register_global_handler(self):
        """Test registering a global event handler."""
        app = Wijjit()
        called = []

        def handler(event):
            called.append(event)

        app.on(EventType.KEY, handler)

        # Verify the handler was registered (may have other global handlers like Tab)
        test_handlers = [
            h for h in app.handler_registry.handlers if h.callback == handler
        ]
        assert len(test_handlers) == 1

        # Dispatch an event
        event = KeyEvent(key="a")
        app.handler_registry.dispatch(event)

        assert len(called) == 1

    def test_register_view_handler(self):
        """Test registering a view-scoped handler."""
        app = Wijjit()
        called = []

        def handler(event):
            called.append(event)

        app.on(
            EventType.KEY,
            handler,
            scope=HandlerScope.VIEW,
            view_name="main",
        )

        # Handler shouldn't fire without matching view
        event = KeyEvent(key="a")
        app.handler_registry.dispatch(event)
        assert len(called) == 0

        # Set current view and dispatch again
        app.handler_registry.current_view = "main"
        app.handler_registry.dispatch(KeyEvent(key="b"))
        assert len(called) == 1


class TestStateIntegration:
    """Tests for state integration and re-rendering."""

    def test_state_change_triggers_render(self):
        """Test that state changes set needs_render flag."""
        app = Wijjit()

        app.needs_render = False
        app.state["count"] = 0

        # Changing state should trigger needs_render
        assert app.needs_render is True

    def test_state_available_in_template_context(self):
        """Test that state is available in template rendering."""
        app = Wijjit(initial_state={"name": "World"})

        @app.view("main")
        def main():
            return {"template": "Hello {{ state.name }}!"}

        # Mock the rendering to check state is passed
        with patch.object(app.renderer, "render_string") as mock_render:
            mock_render.return_value = "rendered"

            app.current_view = "main"
            app._render()

            # Check that render_string was called with state in context
            mock_render.assert_called_once()
            call_kwargs = mock_render.call_args[1]
            assert "context" in call_kwargs
            assert "state" in call_kwargs["context"]
            assert call_kwargs["context"]["state"] == app.state


class TestAppHelpers:
    """Tests for app helper methods."""

    def test_quit(self):
        """Test quitting the app."""
        app = Wijjit()
        app.running = True

        app.quit()

        assert app.running is False

    def test_refresh(self):
        """Test forcing a refresh."""
        app = Wijjit()
        app.needs_render = False

        app.refresh()

        assert app.needs_render is True


class TestErrorHandling:
    """Tests for error handling."""

    def test_navigate_with_error_in_on_exit(self):
        """Test that errors in on_exit don't crash navigation."""
        app = Wijjit()

        def bad_exit():
            raise ValueError("Exit error")

        @app.view("view1", default=True)
        def view1():
            return {
                "template": "View 1",
                "on_exit": bad_exit,
            }

        @app.view("view2")
        def view2():
            return {"template": "View 2"}

        # Should handle error gracefully
        with patch.object(app, "_handle_error") as mock_error:
            app.navigate("view2")

            # Should have called error handler
            mock_error.assert_called_once()
            # Should still have navigated
            assert app.current_view == "view2"

    def test_navigate_with_error_in_on_enter(self):
        """Test that errors in on_enter don't crash navigation."""
        app = Wijjit()

        def bad_enter():
            raise ValueError("Enter error")

        @app.view("view1", default=True)
        def view1():
            return {"template": "View 1"}

        @app.view("view2")
        def view2():
            return {
                "template": "View 2",
                "on_enter": bad_enter,
            }

        with patch.object(app, "_handle_error") as mock_error:
            app.navigate("view2")

            # Should have called error handler
            mock_error.assert_called_once()
            # Should still have navigated
            assert app.current_view == "view2"

    def test_render_with_template_error(self):
        """Test that template errors are handled gracefully."""
        app = Wijjit()

        @app.view("main", default=True)
        def main():
            return {"template": "{{ undefined_var }}"}

        with patch.object(
            app.renderer, "render_string", side_effect=Exception("Template error")
        ):
            with patch.object(app, "_handle_error") as mock_error:
                app._render()

                # Should have called error handler
                mock_error.assert_called_once()


class TestRun:
    """Tests for the main run loop."""

    def test_run_requires_views(self):
        """Test that run() fails if no views registered."""
        app = Wijjit()

        with pytest.raises(RuntimeError, match="No views registered"):
            app.run()

    def test_run_uses_default_view(self):
        """Test that run() uses the default view."""

        app = Wijjit()

        @app.view("main", default=True)
        def main():
            return {"template": "Main"}

        # Mock components to avoid actual terminal operations
        with patch.object(app.screen_manager, "enter_alternate_buffer"):
            with patch.object(app.screen_manager, "exit_alternate_buffer"):
                # Mock async read_input_async
                async def mock_read(*args, **kwargs):
                    return Key("ctrl+q", KeyType.CONTROL, "\x11")

                with patch.object(
                    app.input_handler, "read_input_async", side_effect=mock_read
                ):
                    with patch.object(app, "_render"):
                        app.run()

                        # Should have set running to True (then stopped on Ctrl+Q)
                        assert app.running is False

    def test_run_calls_initial_on_enter(self):
        """Test that run() calls on_enter for initial view."""
        app = Wijjit()
        entered = []

        def on_enter():
            entered.append(True)

        @app.view("main", default=True)
        def main():
            return {
                "template": "Main",
                "on_enter": on_enter,
            }

        with patch.object(app.screen_manager, "enter_alternate_buffer"):
            with patch.object(app.screen_manager, "exit_alternate_buffer"):
                # Mock async read_input_async
                async def mock_read(*args, **kwargs):
                    return Key("ctrl+q", KeyType.CONTROL, "\x11")

                with patch.object(
                    app.input_handler, "read_input_async", side_effect=mock_read
                ):
                    with patch.object(app, "_render"):
                        app.run()

                        assert len(entered) == 1

    def test_run_enters_and_exits_screen(self):
        """Test that run() properly enters and exits alternate screen."""
        app = Wijjit()

        @app.view("main", default=True)
        def main():
            return {"template": "Main"}

        with patch.object(app.screen_manager, "enter_alternate_buffer") as mock_enter:
            with patch.object(app.screen_manager, "exit_alternate_buffer") as mock_exit:
                # Mock async read_input_async
                async def mock_read(*args, **kwargs):
                    return Key("ctrl+q", KeyType.CONTROL, "\x11")

                with patch.object(
                    app.input_handler, "read_input_async", side_effect=mock_read
                ):
                    with patch.object(app, "_render"):
                        app.run()

                        mock_enter.assert_called_once()
                        mock_exit.assert_called_once()

    def test_run_exits_screen_on_error(self):
        """Test that run() exits screen even if error occurs."""
        app = Wijjit()

        @app.view("main", default=True)
        def main():
            return {"template": "Main"}

        with patch.object(app.screen_manager, "enter_alternate_buffer"):
            with patch.object(app.screen_manager, "exit_alternate_buffer") as mock_exit:
                # Mock async read_input_async to raise error
                async def mock_read(*args, **kwargs):
                    raise Exception("Error")

                with patch.object(
                    app.input_handler, "read_input_async", side_effect=mock_read
                ):
                    with patch.object(app, "_render"):
                        try:
                            app.run()
                        except Exception:
                            pass

                        # Should still exit screen
                        mock_exit.assert_called_once()


class TestKeyHandlers:
    """Tests for on_key decorator."""

    def test_on_key_decorator(self):
        """Test registering a key handler with decorator."""
        app = Wijjit()
        called = []

        @app.on_key("d")
        def handle_d(event):
            called.append(event)

        # Verify handler was registered
        assert "d" in app._key_handlers
        assert app._key_handlers["d"] == handle_d

    def test_on_key_normalizes_case(self):
        """Test that key names are normalized to lowercase."""
        app = Wijjit()

        @app.on_key("D")
        def handle_d(event):
            pass

        # Should be stored as lowercase
        assert "d" in app._key_handlers
        assert "D" not in app._key_handlers

    def test_multiple_key_handlers(self):
        """Test registering multiple key handlers."""
        app = Wijjit()

        @app.on_key("d")
        def handle_d(event):
            pass

        @app.on_key("q")
        def handle_q(event):
            pass

        @app.on_key("enter")
        def handle_enter(event):
            pass

        assert "d" in app._key_handlers
        assert "q" in app._key_handlers
        assert "enter" in app._key_handlers
        assert len(app._key_handlers) == 3
