"""Wijjit - Flask for Terminal Applications.

A declarative TUI framework using Jinja2 templates for building
terminal user interfaces with familiar web development patterns.
"""

__version__ = "0.1.0"

# Core components
from wijjit.config import Config, DefaultConfig
from wijjit.core.app import Wijjit
from wijjit.core.events import (
    ActionEvent,
    ChangeEvent,
    Event,
    EventType,
    FocusEvent,
    Handler,
    HandlerRegistry,
    HandlerScope,
    KeyEvent,
)
from wijjit.core.focus import FocusManager
from wijjit.core.renderer import Renderer
from wijjit.core.state import State
from wijjit.core.templating import (
    RenderedView,
    render_template,
    render_template_string,
)
from wijjit.core.view_router import ViewConfig

# Elements - base
from wijjit.elements.base import (
    Container,
    Element,
    ElementType,
    OverlayElement,
    ScrollableElement,
    TextElement,
)

# Elements - display
from wijjit.elements.display import (
    BarChart,
    ColumnChart,
    ContentType,
    ContentView,
    Gauge,
    HeatMap,
    ImageView,
    LineChart,
    Link,
    ListView,
    LogView,
    ModalElement,
    NotificationElement,
    NotificationSeverity,
    Page,
    Pager,
    ProgressBar,
    Sparkline,
    Spinner,
    StatusBar,
    StatusIndicator,
    TabbedPanel,
    Table,
    TabPosition,
    Tree,
    TreeIndicatorStyle,
)

# Elements - input
from wijjit.elements.input import (
    Button,
    Checkbox,
    CheckboxGroup,
    CodeEditor,
    DataGrid,
    InputStyle,
    Radio,
    RadioGroup,
    Select,
    Slider,
    SyntaxHighlighter,
    TextArea,
    TextInput,
    Toggle,
)

# Elements - dialogs (ModalElement subclasses)
from wijjit.elements.modal import AlertDialog, ConfirmDialog, TextInputDialog

# Autocomplete (headline feature - re-exported for `from wijjit import ...`).
# Imported after the element packages: the autocomplete popup depends on the
# elements layer, so importing it earlier would trigger a circular import.
# ``isort: split`` keeps this import from being re-sorted above the elements.
# isort: split
from wijjit.autocomplete import (
    AsyncCompleter,
    CallbackCompleter,
    Completer,
    CompleterConfig,
    StateCompleter,
    WordCompleter,
)

# Helpers
from wijjit.helpers import load_filesystem_tree

# Inline rendering
from wijjit.inline import InlineApp, render_inline

# Layout components
from wijjit.layout.bounds import Bounds, Size, parse_size
from wijjit.layout.frames import BorderStyle, Frame, FrameStyle

# Terminal utilities
from wijjit.terminal.ansi import (
    ANSIColor,
    ANSICursor,
    ANSIScreen,
    ANSIStyle,
    clip_to_width,
    colorize,
    strip_ansi,
    visible_length,
)
from wijjit.terminal.input import InputHandler, Key, Keys, KeyType
from wijjit.terminal.screen import ScreenManager, alternate_screen

# Friendly aliases for the documented element names. The classes are
# internally suffixed ``Element`` (ModalElement / NotificationElement) but the
# docs, template tags, and registry refer to them as ``Modal`` / ``Notification``.
# Both names point at the same class; the ``*Element`` names remain for
# backward compatibility.
Modal = ModalElement
Notification = NotificationElement

__all__ = [
    # Version
    "__version__",
    # Core
    "Wijjit",
    "Config",
    "DefaultConfig",
    "State",
    "Renderer",
    "FocusManager",
    "ViewConfig",
    # Templating (Flask-style view rendering)
    "RenderedView",
    "render_template_string",
    "render_template",
    # Inline rendering
    "render_inline",
    "InlineApp",
    # Autocomplete
    "Completer",
    "WordCompleter",
    "CallbackCompleter",
    "AsyncCompleter",
    "StateCompleter",
    "CompleterConfig",
    # Events
    "Event",
    "EventType",
    "KeyEvent",
    "ActionEvent",
    "ChangeEvent",
    "FocusEvent",
    "Handler",
    "HandlerRegistry",
    "HandlerScope",
    # Elements - base
    "Element",
    "Container",
    "ElementType",
    "OverlayElement",
    "ScrollableElement",
    "TextElement",
    # Elements - input
    "Button",
    "Checkbox",
    "CheckboxGroup",
    "CodeEditor",
    "DataGrid",
    "InputStyle",
    "Radio",
    "RadioGroup",
    "Select",
    "Slider",
    "SyntaxHighlighter",
    "TextArea",
    "TextInput",
    "Toggle",
    # Elements - display
    "BarChart",
    "ColumnChart",
    "ContentType",
    "ContentView",
    "Gauge",
    "HeatMap",
    "ImageView",
    "LineChart",
    "Link",
    "ListView",
    "LogView",
    "ModalElement",
    "Modal",
    "NotificationElement",
    "Notification",
    "NotificationSeverity",
    "ConfirmDialog",
    "AlertDialog",
    "TextInputDialog",
    "Page",
    "Pager",
    "ProgressBar",
    "Sparkline",
    "Spinner",
    "StatusBar",
    "StatusIndicator",
    "Table",
    "TabbedPanel",
    "TabPosition",
    "Tree",
    "TreeIndicatorStyle",
    # Layout
    "Bounds",
    "Size",
    "parse_size",
    "Frame",
    "FrameStyle",
    "BorderStyle",
    # Terminal - ANSI
    "ANSIColor",
    "ANSIStyle",
    "ANSICursor",
    "ANSIScreen",
    "strip_ansi",
    "visible_length",
    "clip_to_width",
    "colorize",
    # Terminal - Screen
    "ScreenManager",
    "alternate_screen",
    # Terminal - Input
    "InputHandler",
    "Key",
    "Keys",
    "KeyType",
    # Helpers
    "load_filesystem_tree",
]
