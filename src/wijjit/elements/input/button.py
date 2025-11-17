# ${DIR_PATH}/${FILE_NAME}
from collections.abc import Callable
from enum import Enum, auto

from wijjit.core.events import ActionEvent
from wijjit.elements.base import Element, ElementType
from wijjit.rendering import PaintContext
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseEvent, MouseEventType


class ButtonStyle(Enum):
    """Visual style for button rendering.

    This enum defines different border and decoration styles for buttons.
    Each style provides a distinct visual appearance while maintaining
    single-line height.
    """

    BRACKETS = auto()  # < Button > - Classic angle brackets
    SQUARE = auto()  # [ Button ] - Square brackets
    BOX = auto()  # ┤ Button ├ - Box drawing characters
    BLOCK = auto()  # ▐ Button ▌ - Block characters
    ROUNDED = auto()  # ( Button ) - Rounded brackets
    MINIMAL = auto()  # Button with styling only, no borders


class Button(Element):
    """Button element.

    Parameters
    ----------
    label : str
        Button label text
    id : str, optional
        Element identifier
    on_click : callable, optional
        Callback when button is activated, receives ActionEvent
    style : ButtonStyle, optional
        Visual style for button rendering (default: BRACKETS)

    Attributes
    ----------
    label : str
        Button label
    style : ButtonStyle
        Visual style for rendering
    on_click : callable or None
        Click callback that receives ActionEvent
    on_activate : callable or None
        Action callback that receives ActionEvent
    action : str or None
        Action ID set by template extension

    Examples
    --------
    Create a basic button:

    >>> btn = Button("Click Me")

    Create button with different styles:

    >>> btn = Button("Save", style=ButtonStyle.BOX)
    >>> btn = Button("Cancel", style=ButtonStyle.MINIMAL)
    """

    def __init__(
        self,
        label: str,
        id: str | None = None,
        on_click: Callable[[ActionEvent], None] | None = None,
        style: ButtonStyle = ButtonStyle.BRACKETS,
    ):
        super().__init__(id)
        self.element_type = ElementType.BUTTON
        self.focusable = True
        self.label = label
        self.style = style
        self.on_click = on_click

        # Action callback (called when button is activated)
        self.on_activate: Callable[[ActionEvent], None] | None = None

        # Action ID (set by template extension)
        self.action: str | None = None

    def handle_key(self, key: Key) -> bool:
        """Handle keyboard input.

        Parameters
        ----------
        key : Key
            Key press to handle

        Returns
        -------
        bool
            True if key was handled
        """
        # Activate on Enter or Space
        if key == Keys.ENTER or key == Keys.SPACE:
            self.activate()
            return True

        return False

    def handle_mouse(self, event: MouseEvent) -> bool:
        """Handle mouse input.

        Parameters
        ----------
        event : MouseEvent
            Mouse event to handle

        Returns
        -------
        bool
            True if event was handled
        """
        # Activate on click or double-click
        if event.type in (MouseEventType.CLICK, MouseEventType.DOUBLE_CLICK):
            self.activate()
            return True

        return False

    def activate(self) -> None:
        """Activate the button (trigger click callback and action callback).

        Creates an ActionEvent with the button's action_id and element id,
        and passes it to both on_click and on_activate callbacks.
        """
        # Create ActionEvent with button context
        event = ActionEvent(
            action_id=self.action or "",
            source_element_id=self.id,
            data={"label": self.label},
        )

        if self.on_click:
            self.on_click(event)

        if self.on_activate:
            self.on_activate(event)

    def render_to(self, ctx: PaintContext) -> None:
        """Render button using cell-based rendering (NEW API).

        Parameters
        ----------
        ctx : PaintContext
            Paint context with buffer, style resolver, and bounds

        Notes
        -----
        This is the reference implementation for cell-based rendering.
        It demonstrates how to:
        1. Resolve styles based on element state (focused, hovered)
        2. Apply different visual styles based on configuration
        3. Write styled text to the cell buffer
        4. Handle multi-character borders and decorations

        The button renders as a single line with decorative borders based
        on the style setting.
        """

        # Resolve style based on button state
        if self.focused:
            resolved_style = ctx.style_resolver.resolve_style(self, "button:focus")
        elif self.hovered:
            resolved_style = ctx.style_resolver.resolve_style(self, "button:hover")
        else:
            resolved_style = ctx.style_resolver.resolve_style(self, "button")

        # Render based on visual style
        if self.style == ButtonStyle.BRACKETS:
            # < Button > - Classic angle brackets
            text = f"< {self.label} >"
            ctx.write_text(0, 0, text, resolved_style)

        elif self.style == ButtonStyle.SQUARE:
            # [ Button ] - Square brackets
            text = f"[ {self.label} ]"
            ctx.write_text(0, 0, text, resolved_style)

        elif self.style == ButtonStyle.BOX:
            # ┤ Button ├ - Box drawing characters (left/right borders)
            text = f"\u2524 {self.label} \u251c"  # ┤ and ├
            ctx.write_text(0, 0, text, resolved_style)

        elif self.style == ButtonStyle.BLOCK:
            # ▐ Button ▌ - Block characters (left/right edges)
            text = f"\u2590 {self.label} \u258c"  # ▐ and ▌
            ctx.write_text(0, 0, text, resolved_style)

        elif self.style == ButtonStyle.ROUNDED:
            # ( Button ) - Rounded brackets
            text = f"( {self.label} )"
            ctx.write_text(0, 0, text, resolved_style)

        elif self.style == ButtonStyle.MINIMAL:
            # Button - Just the label with styling, no borders
            # Add padding spaces for better visual separation
            text = f" {self.label} "
            ctx.write_text(0, 0, text, resolved_style)
