"""Headless test harness for Wijjit applications.

The harness lets tests (and agents) drive a real :class:`~wijjit.core.app.Wijjit`
application without a TTY: scripted key and mouse events are fed through the
*same* event-loop dispatch path used in production, and the rendered screen can
be read back as plain text or ANSI.

It works by:

1. Swapping ``app.input_handler`` for a :class:`ScriptedInputHandler` that
   returns queued events from ``read_input_async()`` instead of reading a
   terminal.
2. Forcing a headless configuration (no alternate screen, no cursor hiding, no
   suspend handlers, no FPS sleeps, no render throttle).
3. Pinning the terminal size by patching :func:`shutil.get_terminal_size`.
4. Driving ``EventLoop._process_frame_async()`` on a private asyncio loop, so
   input routing, focus navigation, modal blocking and overlay compositing all
   run exactly as they do for a real user.

The visible screen is read from the renderer's last displayed buffer, so
overlays composited during a frame are included.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import os
import shutil
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING

from wijjit.inline.render import _buffer_to_inline_ansi
from wijjit.terminal.input import Key, Keys, KeyType
from wijjit.terminal.mouse import MouseButton, MouseEvent, MouseEventType

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit
    from wijjit.core.vdom import VNode
    from wijjit.elements.base import Element

# Friendly key-name -> Key mapping for WijjitHarness.press().
_NAMED_KEYS: dict[str, Key] = {
    "enter": Keys.ENTER,
    "return": Keys.ENTER,
    "tab": Keys.TAB,
    "shift+tab": Keys.BACKTAB,
    "backtab": Keys.BACKTAB,
    "escape": Keys.ESCAPE,
    "esc": Keys.ESCAPE,
    "backspace": Keys.BACKSPACE,
    "delete": Keys.DELETE,
    "del": Keys.DELETE,
    "space": Keys.SPACE,
    "up": Keys.UP,
    "down": Keys.DOWN,
    "left": Keys.LEFT,
    "right": Keys.RIGHT,
    "home": Keys.HOME,
    "end": Keys.END,
    "pageup": Keys.PAGE_UP,
    "pagedown": Keys.PAGE_DOWN,
}

_MOUSE_BUTTONS = {
    "left": MouseButton.LEFT,
    "middle": MouseButton.MIDDLE,
    "right": MouseButton.RIGHT,
}


class ScriptedInputHandler:
    """Drop-in replacement for :class:`~wijjit.terminal.input.InputHandler`.

    Returns queued :class:`~wijjit.terminal.input.Key` /
    :class:`~wijjit.terminal.mouse.MouseEvent` objects instead of reading from a
    real terminal. All terminal-mutating methods are no-ops.

    Parameters
    ----------
    enable_mouse : bool, optional
        Recorded for parity with the real handler (default: False).
    mouse_tracking_mode : optional
        Ignored; present for signature parity.
    """

    def __init__(self, enable_mouse: bool = False, mouse_tracking_mode=None) -> None:
        self._queue: deque = deque()
        self._wants_mouse = enable_mouse
        self.mouse_enabled = False
        self.mouse_parser = None

    def enqueue(self, event: Key | MouseEvent) -> None:
        """Queue an event to be returned by the next read.

        Parameters
        ----------
        event : Key or MouseEvent
            The event to queue.
        """
        self._queue.append(event)

    def empty(self) -> bool:
        """Return True if no events are queued.

        Returns
        -------
        bool
            Whether the input queue is empty.
        """
        return not self._queue

    async def read_input_async(self, timeout: float | None = None):
        """Return the next queued event, or None if the queue is empty.

        Parameters
        ----------
        timeout : float, optional
            Ignored; the queue is drained immediately.

        Returns
        -------
        Key or MouseEvent or None
            The next event, or None when empty (simulating a read timeout).
        """
        if self._queue:
            return self._queue.popleft()
        return None

    def read_input(self, timeout: float | None = None):
        """Synchronous variant of :meth:`read_input_async`.

        Parameters
        ----------
        timeout : float, optional
            Ignored.

        Returns
        -------
        Key or MouseEvent or None
            The next event, or None when empty.
        """
        return self._queue.popleft() if self._queue else None

    def read_key(self) -> Key | None:
        """Return the next queued key, skipping non-key events.

        Returns
        -------
        Key or None
            The next key event, or None.
        """
        event = self.read_input()
        return event if isinstance(event, Key) else None

    def enable_mouse_tracking(self, mode=None) -> None:
        """No-op mouse-tracking enable (records state only)."""
        self.mouse_enabled = True

    def disable_mouse_tracking(self) -> None:
        """No-op mouse-tracking disable (records state only)."""
        self.mouse_enabled = False

    def close(self) -> None:
        """No-op close."""

    def cleanup(self) -> None:
        """No-op cleanup."""


class _RecordingBackend:
    """Tee around the app's terminal backend that records emitted frames.

    Delegates every attribute to the wrapped backend and appends each
    ``write_frame`` payload - the exact ANSI byte string the app would send
    to the terminal - to a shared list. This is the only place the raw
    emitted stream (diff output, SGR sequences, cursor escapes) is
    observable: the harness's ``screen()``/``screen_ansi()`` re-serialize
    the cell buffer and never see it.

    Parameters
    ----------
    inner : object
        The real backend to delegate to.
    frames : list of str
        Shared sink that recorded frames are appended to.
    """

    def __init__(self, inner: object, frames: list[str]) -> None:
        self._inner = inner
        self._frames = frames

    def write_frame(self, data: str) -> None:
        """Record the frame payload, then forward it to the real backend."""
        self._frames.append(data)
        self._inner.write_frame(data)  # type: ignore[attr-defined]

    def __getattr__(self, name: str):
        return getattr(self._inner, name)


class WijjitHarness:
    """Drive a Wijjit app headlessly and inspect the rendered screen.

    Parameters
    ----------
    app : Wijjit
        The application to drive. Views should already be registered.
    size : tuple of (int, int), optional
        Terminal ``(columns, rows)`` to render at (default: ``(80, 24)``).
    enable_mouse : bool, optional
        Whether to report mouse support as enabled (default: True).
    max_frames : int, optional
        Safety cap on frames processed per input pump (default: 500).

    Notes
    -----
    Use as a context manager, or call :meth:`start` and :meth:`close` manually.
    The public input methods (:meth:`press`, :meth:`type`, :meth:`click`,
    :meth:`scroll`, :meth:`tick`) are synchronous; they pump the async event
    loop internally on a private loop.
    """

    def __init__(
        self,
        app: Wijjit,
        size: tuple[int, int] = (80, 24),
        enable_mouse: bool = True,
        max_frames: int = 500,
    ) -> None:
        self.app = app
        self._size = size
        self._enable_mouse = enable_mouse
        self._max_frames = max_frames

        self._input = ScriptedInputHandler(enable_mouse=enable_mouse)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._orig_input = None
        self._orig_get_size = None
        self._started = False

        # Errors routed through app._handle_error while the harness drives the
        # app (render/action/background-task failures). Captured so tests can
        # assert the app rendered cleanly via assert_no_errors().
        self._errors: list[tuple[str, BaseException]] = []
        self._orig_handle_error = None

        # Raw frame payloads recorded from app._backend.write_frame while the
        # harness is driving (see emitted_frames / last_frame / emitted_ansi).
        self._emitted_frames: list[str] = []
        self._orig_backend: object | None = None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> WijjitHarness:
        """Initialize the app headlessly and render the initial view.

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.
        """
        if self._started:
            return self

        self._patch_terminal_size()
        self._orig_input = self.app.input_handler
        self.app.input_handler = self._input  # type: ignore[assignment]
        self._apply_headless_config()
        self._capture_errors()

        # Tee the backend so the raw emitted ANSI stream is recorded.
        self._emitted_frames.clear()
        self._orig_backend = self.app._backend
        self.app._backend = _RecordingBackend(  # type: ignore[assignment]
            self._orig_backend, self._emitted_frames
        )

        self._loop = asyncio.new_event_loop()
        self._run(self._startup_async())
        self._started = True
        return self

    def close(self) -> None:
        """Restore the app and tear down the private event loop."""
        try:
            if self._loop is not None and not self._loop.is_closed():
                # Let any callback-scheduled tasks settle, then cancel them.
                with contextlib.suppress(Exception):
                    self._run(asyncio.sleep(0))
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    with contextlib.suppress(Exception):
                        self._loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                self._loop.close()
        finally:
            self._restore_terminal_size()
            self._restore_error_handler()
            if self._orig_input is not None:
                self.app.input_handler = self._orig_input
            if self._orig_backend is not None:
                self.app._backend = self._orig_backend  # type: ignore[assignment]
                self._orig_backend = None
            self._started = False

    def __enter__(self) -> WijjitHarness:
        return self.start()

    def __exit__(self, *exc) -> None:
        self.close()

    # -- input -------------------------------------------------------------

    def press(self, key: str | Key) -> WijjitHarness:
        """Press a single key and pump the resulting frames.

        Parameters
        ----------
        key : str or Key
            A friendly key name (``"enter"``, ``"tab"``, ``"up"``, ``"ctrl+s"``,
            a single character), or a pre-built :class:`Key`.

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.
        """
        self._input.enqueue(self._to_key(key))
        self._pump()
        return self

    def type(self, text: str) -> WijjitHarness:
        """Type a string, one character key at a time.

        Parameters
        ----------
        text : str
            The text to type into the focused element.

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.
        """
        for char in text:
            self._input.enqueue(Key(char, KeyType.CHARACTER, char))
        self._pump()
        return self

    def key(self, key_obj: Key) -> WijjitHarness:
        """Enqueue a raw :class:`Key` and pump frames.

        Parameters
        ----------
        key_obj : Key
            The key object to dispatch.

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.
        """
        self._input.enqueue(key_obj)
        self._pump()
        return self

    def click(
        self, x: int, y: int, button: str = "left", count: int = 1
    ) -> WijjitHarness:
        """Click at a screen cell and pump frames.

        Parameters
        ----------
        x : int
            Column (0-based).
        y : int
            Row (0-based).
        button : str, optional
            ``"left"``, ``"middle"`` or ``"right"`` (default: ``"left"``).
        count : int, optional
            Click count; 2 produces a double-click (default: 1).

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.
        """
        event_type = MouseEventType.DOUBLE_CLICK if count >= 2 else MouseEventType.CLICK
        self._input.enqueue(
            MouseEvent(event_type, _MOUSE_BUTTONS[button], x, y, click_count=count)
        )
        self._pump()
        return self

    def scroll(
        self, x: int, y: int, direction: str = "down", amount: int = 1
    ) -> WijjitHarness:
        """Scroll the wheel at a screen cell and pump frames.

        Parameters
        ----------
        x : int
            Column (0-based).
        y : int
            Row (0-based).
        direction : str, optional
            ``"up"`` or ``"down"`` (default: ``"down"``).
        amount : int, optional
            Number of wheel steps (default: 1).

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.
        """
        button = MouseButton.SCROLL_UP if direction == "up" else MouseButton.SCROLL_DOWN
        for _ in range(amount):
            self._input.enqueue(MouseEvent(MouseEventType.SCROLL, button, x, y))
        self._pump()
        return self

    def tick(self, frames: int = 1) -> WijjitHarness:
        """Advance animations (e.g. spinners) and re-render.

        Parameters
        ----------
        frames : int, optional
            Number of animation frames to advance (default: 1).

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.
        """
        for _ in range(max(1, frames)):
            self.app.event_loop._advance_spinner_frames()
        self.app.needs_render = True
        self._pump()
        return self

    def resize(self, width: int, height: int) -> WijjitHarness:
        """Resize the virtual terminal and drive the resulting re-layout.

        Changes the size reported by the app's backend and pumps a frame, so
        the event loop's resize-detection path runs exactly as it does on a live
        terminal resize: overlays re-centre, notification positions update,
        scroll offsets re-clamp to the new viewport, and the view re-lays-out
        and repaints at the new dimensions. ``screen()`` / ``screen_ansi()``
        reflect the new size afterward.

        Parameters
        ----------
        width : int
            New terminal width in columns.
        height : int
            New terminal height in rows.

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.
        """
        if not self._started:
            raise RuntimeError("resize() requires a started harness (call start())")
        self._size = (width, height)
        self.app.needs_render = True
        self._pump()
        return self

    # -- waiting -----------------------------------------------------------

    def wait_for(
        self,
        predicate: Callable[[], bool],
        *,
        frames: int = 100,
        tick: bool = False,
    ) -> WijjitHarness:
        """Pump frames until ``predicate()`` is true, or raise on timeout.

        Use this to drive an app whose UI settles asynchronously -- an async
        view resolving, a background task updating ``state``, a notification
        expiring, or a spinner-driven animation reaching a target frame. Each
        iteration processes one event-loop frame (rendering and yielding to any
        pending asyncio tasks), then re-checks ``predicate``.

        The harness has no wall clock (rendering is deterministic and
        frame-driven), so the timeout is expressed as a *frame budget* rather
        than seconds. This keeps waits reproducible across machines and CI.

        Parameters
        ----------
        predicate : callable
            A zero-argument callable returning ``True`` once the awaited
            condition holds. Evaluated once before pumping and again after each
            frame.
        frames : int, optional
            Maximum number of frames to pump before giving up (default: 100).
        tick : bool, optional
            Advance one animation frame per iteration as well, so conditions
            that depend on spinner/animation progress can be awaited (default:
            False).

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.

        Raises
        ------
        TimeoutError
            If ``predicate`` is still false after ``frames`` frames. The final
            screen is included for context.

        Examples
        --------
        >>> h.press("enter")
        >>> h.wait_for(lambda: h.state["status"] == "done")
        >>> h.wait_for(lambda: h.find_text("Loaded"), frames=50)
        """
        self._run(self._wait_for_async(predicate, frames, tick))
        return self

    def wait_for_text(self, text: str, *, frames: int = 100) -> WijjitHarness:
        """Pump frames until ``text`` appears on screen, or raise on timeout.

        Convenience wrapper over :meth:`wait_for` for the common case of
        waiting for rendered output. See :meth:`wait_for` for the frame-budget
        rationale.

        Parameters
        ----------
        text : str
            Substring to wait for anywhere on the rendered screen.
        frames : int, optional
            Maximum number of frames to pump before giving up (default: 100).

        Returns
        -------
        WijjitHarness
            ``self``, for chaining.

        Raises
        ------
        TimeoutError
            If ``text`` never appears within ``frames`` frames. The final
            screen is included for context.
        """
        try:
            return self.wait_for(lambda: text in self.screen(), frames=frames)
        except TimeoutError:
            raise TimeoutError(
                f"Timed out after {frames} frames waiting for {text!r} on screen. "
                f"Last screen:\n{self.screen()}"
            ) from None

    async def _wait_for_async(
        self, predicate: Callable[[], bool], frames: int, tick: bool
    ) -> None:
        event_loop = self.app.event_loop
        if predicate():
            return
        for _ in range(max(1, frames)):
            if tick:
                event_loop._advance_spinner_frames()
            self.app.needs_render = True
            await event_loop._process_frame_async()
            # Let callback-scheduled tasks (async views, background work) run.
            await asyncio.sleep(0)
            if predicate():
                return
            if not event_loop.running:
                break
        raise TimeoutError(
            f"Timed out after {frames} frames waiting for condition. "
            f"Last screen:\n{self.screen()}"
        )

    # -- inspection --------------------------------------------------------

    def screen(self) -> str:
        """Return the current screen as plain text (no ANSI).

        Returns
        -------
        str
            Newline-joined visible characters of the last rendered frame.
        """
        return self.app.renderer.get_buffer_as_text()

    def screen_ansi(self) -> str:
        """Return the current screen as an ANSI string (with styling).

        Returns
        -------
        str
            ANSI representation of the last displayed buffer, rows separated by
            newlines. Empty string if nothing has been rendered yet.
        """
        buffer = self.app.renderer._last_displayed_buffer
        if buffer is None:
            return ""
        width, height = self._size
        return _buffer_to_inline_ansi(buffer, width, height)

    def lines(self) -> list[str]:
        """Return the screen as a list of plain-text rows.

        Returns
        -------
        list of str
            One string per terminal row.
        """
        return self.screen().split("\n")

    def find_text(self, text: str) -> bool:
        """Return whether ``text`` appears anywhere on screen.

        Parameters
        ----------
        text : str
            Substring to look for.

        Returns
        -------
        bool
            True if found.
        """
        return text in self.screen()

    def assert_text(self, text: str) -> None:
        """Assert that ``text`` appears on screen, else raise with the screen.

        Parameters
        ----------
        text : str
            Substring expected to be visible.

        Raises
        ------
        AssertionError
            If ``text`` is not present, including the full screen for context.
        """
        screen = self.screen()
        assert text in screen, f"Expected {text!r} on screen but got:\n{screen}"

    def tree(self) -> VNode | None:
        """Return the last rendered VNode tree (the "DOM"), if any.

        Returns
        -------
        VNode or None
            Root of the last reconciled VNode tree, or ``None`` for a
            plain-text (non-layout) template that produced no element tree.
        """
        return self.app.renderer._last_vnode_tree

    @property
    def errors(self) -> list[tuple[str, BaseException]]:
        """Errors the app reported while the harness drove it.

        Returns
        -------
        list of (str, BaseException)
            ``(message, exception)`` pairs captured from ``app._handle_error``
            (render, action and background-task failures). Empty if the app
            rendered and dispatched cleanly.
        """
        return list(self._errors)

    def assert_no_errors(self) -> None:
        """Assert the app reported no errors, else raise listing them.

        Raises
        ------
        AssertionError
            If any error was routed through ``app._handle_error``.
        """
        if self._errors:
            detail = "\n".join(f"  {message}: {exc!r}" for message, exc in self._errors)
            raise AssertionError(
                f"App reported {len(self._errors)} error(s):\n{detail}"
            )

    def assert_tree_contains(
        self,
        *,
        type: str | None = None,
        key: str | None = None,
        props: dict[str, object] | None = None,
    ) -> None:
        """Assert a VNode matching the given criteria exists in the tree.

        Parameters
        ----------
        type : str, optional
            Required VNode type (e.g. ``"Button"``).
        key : str, optional
            Required reconciliation key (typically the element id).
        props : dict, optional
            Props that must all be present with the given values.

        Raises
        ------
        AssertionError
            If no matching node is found (the tree is included for context).
        """
        from wijjit.devtools.tree import render_tree_text, walk_vnodes

        root = self.tree()
        for node in walk_vnodes(root):
            if type is not None and node.type != type:
                continue
            if key is not None and node.key != key:
                continue
            if props is not None and not all(
                node.get_prop(name) == value for name, value in props.items()
            ):
                continue
            return
        tree_text = render_tree_text(root) if root is not None else "<no layout tree>"
        raise AssertionError(
            f"No VNode matching type={type!r} key={key!r} props={props!r}.\n"
            f"Tree:\n{tree_text}"
        )

    def assert_screen(self, snapshot: object) -> None:
        """Assert the plain-text screen equals a syrupy ``snapshot``.

        Parameters
        ----------
        snapshot : object
            The syrupy ``snapshot`` fixture to compare against.

        Raises
        ------
        AssertionError
            If the screen does not match the stored snapshot.
        """
        assert self.screen() == snapshot

    @property
    def emitted_frames(self) -> list[str]:
        """Raw ANSI frame payloads the app wrote to its backend, in order.

        Each entry is exactly what one ``_render`` pass sent to
        ``backend.write_frame``: the diffed cell updates with real SGR and
        cursor-position escapes. Unlike :meth:`screen_ansi` (which
        re-serializes the cell buffer), this is the true emitted byte
        stream, so it can assert diff size, escape-sequence hygiene, and
        cursor parking.

        Returns
        -------
        list of str
            A copy of the recorded frame payloads.
        """
        return list(self._emitted_frames)

    @property
    def last_frame(self) -> str:
        """The most recent raw frame payload written to the backend.

        Returns
        -------
        str
            The last ``write_frame`` payload, or ``""`` if none yet.
        """
        return self._emitted_frames[-1] if self._emitted_frames else ""

    def emitted_ansi(self) -> str:
        """The concatenated raw ANSI stream emitted so far.

        Returns
        -------
        str
            All recorded frame payloads joined in emission order.
        """
        return "".join(self._emitted_frames)

    @property
    def state(self):
        """The application's reactive state.

        Returns
        -------
        State
            ``app.state``.
        """
        return self.app.state

    @property
    def running(self) -> bool:
        """Whether the event loop is still running (False after quit).

        Returns
        -------
        bool
            ``app.event_loop.running``.
        """
        return self.app.event_loop.running

    @property
    def focused(self) -> Element | None:
        """The currently focused element, if any.

        Returns
        -------
        Element or None
            The focused element.
        """
        return self.app.focus_manager.get_focused_element()

    # -- internals ---------------------------------------------------------

    def _to_key(self, key: str | Key) -> Key:
        if isinstance(key, Key):
            return key
        name = key.lower()
        if name in _NAMED_KEYS:
            return _NAMED_KEYS[name]
        if name.startswith("ctrl+") and len(name) == len("ctrl+x"):
            letter = name[-1]
            char = chr(ord(letter) - 96) if "a" <= letter <= "z" else None
            return Key(name, KeyType.CONTROL, char)
        if len(key) == 1:
            return Key(key, KeyType.CHARACTER, key)
        raise ValueError(f"Unrecognized key: {key!r}")

    def _apply_headless_config(self) -> None:
        cfg = self.app.config
        cfg["USE_ALTERNATE_SCREEN"] = False
        cfg["HIDE_CURSOR"] = False
        cfg["ENABLE_SUSPEND"] = False
        cfg["SHOW_FPS"] = False
        cfg["SHOW_BOUNDS"] = False
        cfg["MAX_FPS"] = None
        cfg["RENDER_THROTTLE_MS"] = 0
        cfg["ENABLE_MOUSE"] = self._enable_mouse
        # Pin Unicode rendering so snapshots are deterministic across platforms
        # (box-drawing characters would otherwise depend on terminal detection).
        cfg["UNICODE_SUPPORT"] = True

    def _capture_errors(self) -> None:
        """Wrap ``app._handle_error`` so harness-driven errors are recorded.

        The original handler is still invoked (preserving its logging/stderr
        and fatal re-raise behavior); we only tee ``(message, exception)`` into
        ``self._errors`` for later inspection.
        """
        self._errors.clear()
        orig = self.app._handle_error
        self._orig_handle_error = orig  # type: ignore[assignment]
        sink = self._errors

        def _capture(message, exception, fatal=False):  # type: ignore[no-untyped-def]
            sink.append((message, exception))
            return orig(message, exception, fatal=fatal)

        self.app._handle_error = _capture  # type: ignore[assignment]

    def _restore_error_handler(self) -> None:
        if self._orig_handle_error is not None:
            self.app._handle_error = self._orig_handle_error  # type: ignore[assignment]
            self._orig_handle_error = None

    def _patch_terminal_size(self) -> None:
        self._orig_get_size = shutil.get_terminal_size
        # Read self._size at call time (not captured) so resize() takes effect
        # by updating the field, with no need to re-patch.
        shutil.get_terminal_size = (  # type: ignore[assignment]
            lambda *a, **k: os.terminal_size(self._size)
        )

    def _restore_terminal_size(self) -> None:
        if self._orig_get_size is not None:
            shutil.get_terminal_size = self._orig_get_size  # type: ignore[assignment]
            self._orig_get_size = None

    def _run(self, coro):
        """Run a coroutine on the private loop, suppressing stdout writes."""
        assert self._loop is not None
        with contextlib.redirect_stdout(io.StringIO()):
            return self._loop.run_until_complete(coro)

    async def _startup_async(self) -> None:
        """Replicate EventLoop.run_async startup without entering the loop."""
        app = self.app
        event_loop = app.event_loop

        # Select the default (or first) view.
        if app.current_view is None:
            for name, view in app.views.items():
                if view.is_default:
                    app.current_view = name
                    break
        if app.current_view is None and app.views:
            app.current_view = next(iter(app.views.keys()))
        if app.current_view is None:
            raise RuntimeError("No views registered. Use @app.view() to register one.")

        initial_view = app.views[app.current_view]
        await app.view_router._initialize_view_async(initial_view)
        app.handler_registry.current_view = app.current_view

        if initial_view.on_enter:
            if asyncio.iscoroutinefunction(initial_view.on_enter):
                await initial_view.on_enter()
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, initial_view.on_enter)

        event_loop.running = True
        if app.config["ENABLE_MOUSE"] and not app.input_handler.mouse_enabled:
            app.input_handler.enable_mouse_tracking()

        app._render()
        app._last_refresh_time = 0.0

    def _pump(self) -> None:
        self._run(self._pump_async())

    async def _pump_async(self) -> None:
        event_loop = self.app.event_loop
        frames = 0
        while frames < self._max_frames:
            await event_loop._process_frame_async()
            frames += 1
            if not event_loop.running:
                break
            if self._input.empty() and not self.app.needs_render:
                break
        # Allow callback-scheduled tasks to start.
        await asyncio.sleep(0)
