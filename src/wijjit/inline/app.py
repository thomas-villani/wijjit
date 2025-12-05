"""Interactive inline application for in-place updates.

This module provides InlineApp, an async context manager for creating
interactive inline displays that update in place without alternate screen.
"""

from __future__ import annotations

import asyncio
import shutil
import sys
import time
from typing import TYPE_CHECKING, Any

from wijjit.core.renderer import Renderer
from wijjit.core.state import State
from wijjit.inline.cursor import (
    carriage_return,
    clear_to_end_of_line,
    hide_cursor,
    move_cursor_up,
    restore_cursor_position,
    save_cursor_position,
    show_cursor,
)
from wijjit.inline.render import _calculate_content_height, _render_row_optimized

if TYPE_CHECKING:
    from types import TracebackType

    from wijjit.core.focus import FocusManager
    from wijjit.elements.base import Element
    from wijjit.terminal.input import InputHandler


class InlineApp:
    """Interactive inline application that updates in place.

    Uses cursor repositioning to update content without alternate screen.
    Content persists in terminal scrollback after exit.

    This is an async context manager - use with ``async with``.

    Parameters
    ----------
    template : str
        Wijjit template string to render
    height : int or "auto", optional
        Fixed height in lines, or "auto" to calculate from content.
        Default is "auto".
    width : int, optional
        Width in columns. If None, uses terminal width.
    initial_state : dict, optional
        Initial values for the state object
    refresh_interval : float, optional
        Interval in seconds for auto-refresh loop. Default is 0.1.
    enable_input : bool, optional
        Enable keyboard input handling. When True, the app accepts keyboard
        input and routes events to focused elements. Default is False.
    quit_key : str, optional
        Key binding to exit the app when input is enabled.
        Default is "ctrl+q". Set to None to disable quit key.

    Attributes
    ----------
    state : State
        Reactive state object. Changes trigger re-render.

    Examples
    --------
    Basic progress display (no input):

    >>> async with InlineApp(template, height=5) as app:
    ...     for i in range(100):
    ...         app.state.progress = i
    ...         await asyncio.sleep(0.05)

    Interactive form with input:

    >>> template = '''
    ... {% frame title="Input" %}
    ...   {% textinput id="name" placeholder="Enter name" %}{% endtextinput %}
    ... {% endframe %}
    ... '''
    >>> async with InlineApp(template, enable_input=True, quit_key="ctrl+q") as app:
    ...     await app.wait()  # Wait until quit key pressed
    ... print(f"Name: {app.state.name}")
    """

    def __init__(
        self,
        template: str,
        *,
        height: int | str = "auto",
        width: int | None = None,
        initial_state: dict[str, Any] | None = None,
        refresh_interval: float = 0.1,
        enable_input: bool = False,
        quit_key: str | None = "ctrl+q",
    ) -> None:
        self._template = template
        self._height_spec = height
        self._width = width
        self._refresh_interval = refresh_interval
        self._enable_input = enable_input
        self._quit_key = quit_key

        # State with change detection
        self._state = State(initial_state or {})
        self._state.on_change(self._on_state_change)

        # Rendering
        self._renderer = Renderer()
        self._render_width: int = 80
        self._actual_height: int = 1
        self._needs_render = True
        self._running = False
        self._refresh_task: asyncio.Task[None] | None = None

        # Animation support
        self._positioned_elements: list[Element] = []
        self._last_spinner_advance: float = 0.0
        self._spinner_frame_interval: float = 0.2  # 200ms between frames

        # Input support (initialized in __aenter__ if enable_input=True)
        self._input_handler: InputHandler | None = None
        self._focus_manager: FocusManager | None = None
        self._stopped = False  # Flag set by stop() method

    @property
    def state(self) -> State:
        """Access reactive state object.

        Returns
        -------
        State
            The application state. Changes trigger re-renders.
        """
        return self._state

    def _on_state_change(self, key: str, old: Any, new: Any) -> None:
        """Mark for re-render on state change.

        Parameters
        ----------
        key : str
            State key that changed
        old : Any
            Previous value
        new : Any
            New value
        """
        self._needs_render = True

    async def __aenter__(self) -> InlineApp:
        """Enter context: reserve space, initial render, start input.

        Returns
        -------
        InlineApp
            Self for use in async with block
        """
        term_size = shutil.get_terminal_size()
        self._render_width = self._width or term_size.columns

        # Calculate height
        if self._height_spec == "auto":
            self._actual_height = self._calculate_auto_height()
        else:
            self._actual_height = int(self._height_spec)

        # Reserve space by printing empty lines
        if self._actual_height > 1:
            sys.stdout.write("\n" * (self._actual_height - 1))

        # Move cursor back up to start of reserved space
        if self._actual_height > 1:
            sys.stdout.write(move_cursor_up(self._actual_height - 1))

        # Save position and hide cursor
        sys.stdout.write(save_cursor_position())
        sys.stdout.write(hide_cursor())
        sys.stdout.flush()

        # Initialize input handling if enabled
        if self._enable_input:
            from wijjit.core.focus import FocusManager
            from wijjit.terminal.input import InputHandler

            self._input_handler = InputHandler(enable_mouse=False)
            self._focus_manager = FocusManager()

        # Initial render
        self._render()

        # Update focus manager with focusable elements
        if self._focus_manager is not None:
            self._focus_manager.set_elements(self._positioned_elements)

        # Start refresh loop (handles both rendering and input)
        self._running = True
        self._stopped = False
        self._refresh_task = asyncio.create_task(self._refresh_loop())

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context: stop refresh, final render, cleanup.

        Parameters
        ----------
        exc_type : type or None
            Exception type if an exception was raised
        exc_val : BaseException or None
            Exception value if an exception was raised
        exc_tb : TracebackType or None
            Exception traceback if an exception was raised
        """
        self._running = False

        # Cancel refresh task
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        # Final render
        self._render()

        # Cleanup input handler
        if self._input_handler is not None:
            self._input_handler.close()
            self._input_handler = None

        # Clear focus manager
        if self._focus_manager is not None:
            self._focus_manager.clear()
            self._focus_manager = None

        # Move cursor to end of content and cleanup
        sys.stdout.write(restore_cursor_position())
        if self._actual_height > 0:
            sys.stdout.write(f"\x1b[{self._actual_height}B")  # Move down
        sys.stdout.write(show_cursor())
        sys.stdout.write("\n")  # Ensure we're on new line
        sys.stdout.flush()

    async def _refresh_loop(self) -> None:
        """Background loop for periodic rendering, animation, and input."""
        while self._running and not self._stopped:
            # Check if spinners need frame advance
            current_time = time.monotonic()
            if (
                current_time - self._last_spinner_advance
                >= self._spinner_frame_interval
            ):
                if self._advance_spinner_frames():
                    self._needs_render = True
                self._last_spinner_advance = current_time

            if self._needs_render:
                self._render()
                # Update focus manager with new elements after render
                if self._focus_manager is not None:
                    self._focus_manager.set_elements(self._positioned_elements)

            # Handle input if enabled
            if self._input_handler is not None:
                # Read input with short timeout to allow animation
                input_event = await self._input_handler.read_input_async(
                    timeout=self._refresh_interval
                )
                if input_event is not None:
                    await self._handle_input(input_event)
            else:
                # No input handling, just sleep
                await asyncio.sleep(self._refresh_interval)

    def _render(self) -> None:
        """Render current state to terminal."""
        # Build context with state
        context = dict(self._state.data)
        context["state"] = self._state

        # Render to buffer
        _, elements, _ = self._renderer.render_with_layout(
            template_string=self._template,
            context=context,
            width=self._render_width,
            height=self._actual_height,
        )

        # Store elements for animation support
        self._positioned_elements = elements

        # Access the buffer from renderer
        buffer = self._renderer._last_base_buffer
        if buffer is None:
            return

        # Convert to inline ANSI and output
        ansi_output = self._buffer_to_inline_ansi(buffer)

        # Position cursor and output
        sys.stdout.write(restore_cursor_position())
        sys.stdout.write(ansi_output)
        sys.stdout.flush()

        self._needs_render = False

    def _buffer_to_inline_ansi(self, buffer: Any) -> str:
        """Convert buffer to inline ANSI with cursor positioning.

        Parameters
        ----------
        buffer : ScreenBuffer
            Buffer to convert

        Returns
        -------
        str
            ANSI string for in-place update
        """
        lines = []

        for y in range(min(self._actual_height, buffer.height)):
            row = buffer.cells[y]
            line = _render_row_optimized(row, self._render_width)

            # Pad line to full width to clear previous content
            # Then clear to end of line to handle any remaining chars
            lines.append(carriage_return() + line + clear_to_end_of_line())

        return "\n".join(lines)

    def _calculate_auto_height(self) -> int:
        """Calculate content height from template.

        Returns
        -------
        int
            Height needed to fit content
        """
        # Build context with state
        context = dict(self._state.data)
        context["state"] = self._state

        # Render with large height to determine actual height
        _, elements, _ = self._renderer.render_with_layout(
            template_string=self._template,
            context=context,
            width=self._render_width,
            height=1000,
        )

        return _calculate_content_height(elements)

    def refresh(self) -> None:
        """Force immediate re-render.

        Call this if you need to update the display immediately
        without waiting for the refresh interval.
        """
        self._needs_render = True
        self._render()

    def _advance_spinner_frames(self) -> bool:
        """Advance animation frames for all active spinners.

        Returns
        -------
        bool
            True if any spinners were advanced (requires re-render)
        """
        # Import here to avoid circular imports
        from wijjit.elements.display.spinner import Spinner

        advanced_any = False
        for elem in self._positioned_elements:
            if isinstance(elem, Spinner) and elem.active:
                elem.next_frame()
                advanced_any = True

        return advanced_any

    async def _handle_input(self, input_event: Any) -> None:
        """Handle keyboard input event.

        Routes input to quit handling, focus navigation, or focused element.

        Parameters
        ----------
        input_event : Key or MouseEvent
            The input event from InputHandler
        """
        from wijjit.terminal.input import Key

        # Only handle keyboard events (ignore mouse for now)
        if not isinstance(input_event, Key):
            return

        # Check for quit key
        if self._quit_key is not None and input_event.name == self._quit_key:
            self.stop()
            return

        # Handle Tab/Shift+Tab for focus navigation
        if self._focus_manager is not None:
            if input_event.name == "tab":
                self._focus_manager.focus_next()
                self._needs_render = True
                return
            elif input_event.name == "shift+tab":
                self._focus_manager.focus_previous()
                self._needs_render = True
                return

        # Route key to focused element
        if self._focus_manager is not None:
            focused = self._focus_manager.get_focused_element()
            if focused is not None and hasattr(focused, "handle_key"):
                handled = focused.handle_key(input_event)
                if handled:
                    # Sync state from element if it has an id
                    self._sync_element_state(focused)
                    self._needs_render = True

    def _sync_element_state(self, element: Element) -> None:
        """Sync element value to app state.

        Parameters
        ----------
        element : Element
            Element to sync state from
        """
        # Get element id
        elem_id = getattr(element, "id", None)
        if not elem_id:
            return

        # Get element value (TextInput, TextArea, Checkbox, etc.)
        value = None
        if hasattr(element, "value"):
            value = element.value
        elif hasattr(element, "text"):
            value = element.text
        elif hasattr(element, "checked"):
            value = element.checked

        if value is not None:
            # Update state without triggering change callback
            # (since the element already has the value)
            self._state.data[elem_id] = value

    def stop(self) -> None:
        """Stop the application.

        Call this to exit the input loop. The context manager will
        handle cleanup.
        """
        self._stopped = True

    async def wait(self) -> None:
        """Wait until the application is stopped.

        This method blocks until stop() is called (e.g., by the quit key).
        Use this in interactive apps where you want to wait for user input.

        Examples
        --------
        >>> async with InlineApp(template, enable_input=True) as app:
        ...     await app.wait()  # Wait until quit key pressed
        ... print(f"Final state: {dict(app.state)}")
        """
        while self._running and not self._stopped:
            await asyncio.sleep(0.1)
