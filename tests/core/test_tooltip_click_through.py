"""A tooltip must not swallow clicks meant for the UI underneath it.

``MouseEventRouter._route_to_overlay_async`` used to return True ("consumed")
for any overlay under the pointer, handled or not, so a tooltip shown with
``app.show_tooltip`` over a button made the button unclickable. Plain
tooltips now pass unhandled events through; modals, dropdowns and
notifications (interactive, on the tooltip layer) still consume them.
"""

from wijjit import Frame
from wijjit.core.overlay import LayerType
from wijjit.layout.bounds import Bounds
from wijjit.testing import WijjitHarness, app_from_template

TEMPLATE = (
    "{% frame width=40 height=6 %}"
    "{% button id='go' action='go' %}Go Go Go{% endbutton %}"
    "{% endframe %}"
)


def _make_app():
    app = app_from_template(TEMPLATE, state={"clicks": 0})

    @app.on_action("go")
    def _go(event=None):
        app.state["clicks"] += 1

    return app


def _button_cell(app):
    bounds = app.get_element_by_id("go").bounds
    assert bounds is not None
    return bounds.x + 1, bounds.y


def _cover(x, y):
    """A small frame whose bounds cover the cell (x, y)."""
    frame = Frame(width=12, height=3)
    frame.bounds = Bounds(x=max(0, x - 2), y=y, width=12, height=3)
    return frame


class TestTooltipClickThrough:
    def test_click_through_tooltip_reaches_button(self):
        app = _make_app()
        with WijjitHarness(app, size=(60, 12)) as h:
            x, y = _button_cell(app)
            tooltip = _cover(x, y)
            overlay = app.show_tooltip(tooltip, x=tooltip.bounds.x, y=y)
            assert overlay.mouse_passthrough
            assert app.overlay_manager.get_at_position(x, y) is overlay

            h.click(x, y)

            assert h.state["clicks"] == 1
            # Clicking on the tooltip is not a click outside it.
            assert overlay in app.overlay_manager.overlays
            h.assert_no_errors()

    def test_tooltip_does_not_shield_open_dropdown_from_click_outside(self):
        """A click passing through a tooltip still counts as outside the
        overlays beneath it."""
        app = _make_app()
        with WijjitHarness(app, size=(60, 12)) as h:
            x, y = _button_cell(app)
            far = Frame(width=10, height=3)
            far.bounds = Bounds(x=45, y=8, width=10, height=3)
            dropdown = app.overlay_manager.push(
                far, LayerType.DROPDOWN, close_on_click_outside=True
            )
            tooltip = _cover(x, y)
            app.show_tooltip(tooltip, x=tooltip.bounds.x, y=y)

            h.click(x, y)

            assert dropdown not in app.overlay_manager.overlays

    def test_modal_still_consumes_unhandled_click(self):
        app = _make_app()
        with WijjitHarness(app, size=(60, 12)) as h:
            x, y = _button_cell(app)
            cover = _cover(x, y)
            overlay = app.overlay_manager.push(
                cover, LayerType.MODAL, close_on_click_outside=False
            )
            assert not overlay.mouse_passthrough

            h.click(x, y)

            assert h.state["clicks"] == 0

    def test_dropdown_still_consumes_unhandled_click(self):
        app = _make_app()
        with WijjitHarness(app, size=(60, 12)) as h:
            x, y = _button_cell(app)
            cover = _cover(x, y)
            overlay = app.overlay_manager.push(cover, LayerType.DROPDOWN)
            assert not overlay.mouse_passthrough

            h.click(x, y)

            assert h.state["clicks"] == 0

    def test_notification_click_dismisses_and_does_not_reach_button(self):
        app = _make_app()
        with WijjitHarness(app, size=(60, 12)) as h:
            x, y = _button_cell(app)
            app.notify("Saved", duration=None)
            h.tick()
            (notification,) = app.notification_manager.notifications
            assert notification.overlay.layer_type == LayerType.TOOLTIP
            assert not notification.overlay.mouse_passthrough

            # Park the notification over the button to check the routing.
            notification.element.bounds = Bounds(
                x=max(0, x - 2), y=y, width=20, height=3
            )
            h.click(x, y)

            assert h.state["clicks"] == 0
            assert app.notification_manager.notifications == []
