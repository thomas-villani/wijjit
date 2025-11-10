# ${DIR_PATH}/${FILE_NAME}
from typing import Literal

from wijjit.elements.base import Element, ElementType

SPINNER_FRAMES = {
    # Braille dots spinner
    "dots": [
        "\u280b",
        "\u2819",
        "\u2839",
        "\u2838",
        "\u283c",
        "\u2834",
        "\u2826",
        "\u2827",
        "\u2807",
        "\u280f",
    ],
    "dots_ascii": ["/", "-", "\\", "|"],
    # Rotating line
    "line": ["|", "/", "-", "\\"],
    # Bouncing braille bar
    "bouncing": [
        "\u28fe",
        "\u28fd",
        "\u28fb",
        "\u28bf",
        "\u287f",
        "\u28df",
        "\u28ef",
        "\u28f7",
    ],
    "bouncing_ascii": ["<", "<<", "<<<", ">>", ">"],
    # Clock face
    "clock": [
        "\U0001f550",
        "\U0001f551",
        "\U0001f552",
        "\U0001f553",
        "\U0001f554",
        "\U0001f555",
        "\U0001f556",
        "\U0001f557",
        "\U0001f558",
        "\U0001f559",
        "\U0001f55a",
        "\U0001f55b",
    ],
    "clock_ascii": ["12", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"],
}


class Spinner(Element):
    """Spinner element for displaying indefinite loading animation.

    This element provides an animated spinner indicator with support for:
    - Multiple animation styles (dots, line, bouncing, clock)
    - Unicode detection with ASCII fallback
    - Optional label text
    - Optional coloring
    - Active/inactive state control

    Parameters
    ----------
    id : str, optional
        Element identifier
    active : bool, optional
        Whether spinner is active and animating (default: True)
    style : str, optional
        Animation style: "dots", "line", "bouncing", "clock" (default: "dots")
    label : str, optional
        Label text to display next to spinner (default: "")
    color : str, optional
        Color name for the spinner (default: None)
    frame_index : int, optional
        Current animation frame index (default: 0)

    Attributes
    ----------
    active : bool
        Whether spinner is active
    style : str
        Animation style
    label : str
        Label text
    color : str or None
        Color name
    frame_index : int
        Current frame index
    """

    def __init__(
        self,
        id: str | None = None,
        active: bool = True,
        style: Literal["dots", "line", "bouncing", "clock"] = "dots",
        label: str = "",
        color: str | None = None,
        frame_index: int = 0,
    ):
        super().__init__(id)
        self.element_type = ElementType.DISPLAY
        self.focusable = False  # Spinners are not interactive

        # Spinner properties
        self.active = active
        self.style = style
        self.label = label
        self.color = color
        self.frame_index = frame_index

        # Template metadata
        self.action: str | None = None
        self.bind: bool = True

    def next_frame(self) -> None:
        """Advance to the next animation frame.

        This method increments the frame index and wraps around to 0
        when reaching the end of the animation sequence.
        """
        frames = self._get_style_frames(self.style)
        self.frame_index = (self.frame_index + 1) % len(frames)

    def _get_style_frames(self, style: str) -> list[str]:
        """Get animation frames for a style, with Unicode fallback.

        Parameters
        ----------
        style : str
            Animation style name

        Returns
        -------
        list of str
            List of frame characters
        """
        from wijjit.terminal.ansi import supports_unicode

        # Check if we should use ASCII fallback
        if not supports_unicode():
            # Use ASCII fallback versions
            ascii_style = f"{style}_ascii"
            if ascii_style in SPINNER_FRAMES:
                return SPINNER_FRAMES[ascii_style]
            # If no ASCII version, default to line
            return SPINNER_FRAMES["line"]

        # Use Unicode version
        if style in SPINNER_FRAMES:
            return SPINNER_FRAMES[style]
        else:
            # Default to dots if style not found
            return SPINNER_FRAMES["dots"]

    def _get_current_frame(self) -> str:
        """Get the current animation frame character.

        Returns
        -------
        str
            Current frame character
        """
        frames = self._get_style_frames(self.style)
        # Ensure frame_index is within bounds
        frame_idx = self.frame_index % len(frames)
        return frames[frame_idx]

    def render(self) -> str:
        """Render the spinner.

        Returns
        -------
        str
            Rendered spinner with optional label as single-line string
        """
        from wijjit.terminal.ansi import ANSIColor, colorize

        # If not active, return empty space or just label
        if not self.active:
            if self.label:
                return self.label
            else:
                return ""

        # Get current frame
        frame = self._get_current_frame()

        # Apply color if specified
        if self.color:
            color_code = getattr(ANSIColor, self.color.upper(), None)
            if color_code:
                frame = colorize(frame, color=color_code)

        # Combine frame and label
        if self.label:
            return f"{frame} {self.label}"
        else:
            return frame
