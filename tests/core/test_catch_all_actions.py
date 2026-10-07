"""``app.on(EventType.ACTION, ...)`` handlers receive actions.

The event-handling guide, the cookbook and the tutorial all register a
catch-all ACTION handler (to route a family of actions like ``toggle_<id>``
through one function, or to log them all), but ``Wijjit._dispatch_action``
only consulted the ``@app.on_action`` map, so such a handler never ran.
"""

import asyncio

from wijjit.core.events import EventType, HandlerScope
from wijjit.testing import WijjitHarness, app_from_template

BUTTONS = (
    "{% vstack %}"
    '{% button action="save" %}Save{% endbutton %}'
    '{% button action="toggle_7" %}Toggle{% endbutton %}'
    "{% endvstack %}"
)


def _click(app, presses):
    """Tab ``presses`` times then press Enter."""
    with WijjitHarness(app, size=(40, 8)) as h:
        for _ in range(presses):
            h.press("tab")
        h.press("enter")
        return h.errors


def test_global_catch_all_sees_every_action():
    seen = []
    app = app_from_template(BUTTONS)
    app.on(EventType.ACTION, lambda e: seen.append(e.action_id))

    _click(app, 2)  # second button, which has no named handler

    assert seen == ["toggle_7"]


def test_named_handler_runs_first_then_catch_alls_by_priority():
    order = []
    app = app_from_template(BUTTONS, actions={"save": lambda e: order.append("named")})
    app.on(EventType.ACTION, lambda e: order.append("low"), priority=0)
    app.on(EventType.ACTION, lambda e: order.append("high"), priority=10)

    _click(app, 1)

    assert order == ["named", "high", "low"]


def test_view_scoped_catch_all_runs_only_in_its_view():
    seen = []
    app = app_from_template(BUTTONS)
    app.on(
        EventType.ACTION,
        lambda e: seen.append(("main", e.action_id)),
        scope=HandlerScope.VIEW,
        view_name="main",
    )
    app.on(
        EventType.ACTION,
        lambda e: seen.append(("other", e.action_id)),
        scope=HandlerScope.VIEW,
        view_name="other",
    )

    _click(app, 1)

    assert seen == [("main", "save")]


def test_cancelling_stops_later_catch_alls():
    seen = []
    app = app_from_template(BUTTONS)

    def first(event):
        seen.append("first")
        event.cancel()

    app.on(EventType.ACTION, first, priority=10)
    app.on(EventType.ACTION, lambda e: seen.append("second"), priority=0)

    _click(app, 1)

    assert seen == ["first"]


def test_a_raising_catch_all_is_reported_and_the_rest_still_run():
    seen = []
    app = app_from_template(BUTTONS)

    def broken(event):
        raise RuntimeError("boom")

    app.on(EventType.ACTION, broken, priority=10)
    app.on(EventType.ACTION, lambda e: seen.append(e.action_id), priority=0)

    errors = _click(app, 1)

    assert seen == ["save"]
    assert any(isinstance(exc, RuntimeError) for _, exc in errors)


def test_async_catch_all_is_run():
    seen = []
    app = app_from_template(BUTTONS)

    async def log(event):
        await asyncio.sleep(0)
        seen.append(event.action_id)

    app.on(EventType.ACTION, log)

    with WijjitHarness(app, size=(40, 8)) as h:
        h.press("tab").press("enter")
        h.tick(frames=3)

    assert seen == ["save"]


def test_key_handlers_are_not_called_for_actions():
    """Only ACTION handlers match an action, not handlers for other events."""
    keys = []
    app = app_from_template(BUTTONS)
    app.on(EventType.CHANGE, lambda e: keys.append(e))

    _click(app, 1)

    assert keys == []
