# ${DIR_PATH}/${FILE_NAME}
from collections.abc import Callable

from wijjit.core.events import ActionEvent
from wijjit.elements.base import Element, ElementType
from wijjit.terminal.ansi import ANSIColor, ANSIStyle
from wijjit.terminal.input import Key, Keys
from wijjit.terminal.mouse import MouseEvent, MouseEventType


class Button(Element):
    """Button element.

    Parameters
    ----------
    id : str, optional
        Element identifier
    label : str
        Button label text
    on_click : callable, optional
        Callback when button is activated, receives ActionEvent

    Attributes
    ----------
    label : str
        Button label
    on_click : callable or None
        Click callback that receives ActionEvent
    on_activate : callable or None
        Action callback that receives ActionEvent
    action : str or None
        Action ID set by template extension
    """

    def __init__(
        self,
        label: str,
        id: str | None = None,
        on_click: Callable[[ActionEvent], None] | None = None,
    ):
        super().__init__(id)
        self.element_type = ElementType.BUTTON
        self.focusable = True
        self.label = label
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

    def render(self) -> str:
        """Render the button.

        Returns
        -------
        str
            Rendered button
        """
        if self.focused:
            # Focused: bold and highlighted with proper ANSI isolation
            # Reset at start to clear any previous styling, and at end to prevent bleeding
            styles = (
                f"{ANSIStyle.RESET}{ANSIStyle.BOLD}{ANSIColor.BG_BLUE}{ANSIColor.WHITE}"
            )
            return f"{styles}< {self.label} >{ANSIStyle.RESET}"
        else:
            # Not focused: plain style with explicit reset to prevent inheriting styles
            return f"{ANSIStyle.RESET}< {self.label} >{ANSIStyle.RESET}"
