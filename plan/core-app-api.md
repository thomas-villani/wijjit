\## Core App API



```python

\# wijjit/core/app.py

from typing import Callable, Dict, Any, Optional

from dataclasses import dataclass

from .state import State

from .renderer import Renderer

from ..terminal.input import InputHandler



@dataclass

class ViewConfig:

&nbsp;   template: str

&nbsp;   data: Dict\[str, Any]

&nbsp;   handlers: Dict\[str, Callable]

&nbsp;   on\_enter: Optional\[Callable] = None

&nbsp;   on\_exit: Optional\[Callable] = None



class Wijjit:

&nbsp;   def \_\_init\_\_(self, template\_dir: str = 'templates'):

&nbsp;       self.views: Dict\[str, Callable] = {}

&nbsp;       self.default\_view: Optional\[str] = None

&nbsp;       self.current\_view: Optional\[str] = None

&nbsp;       self.template\_dir = template\_dir

&nbsp;       

&nbsp;       # Core systems

&nbsp;       self.state = State()

&nbsp;       self.renderer = Renderer(self)

&nbsp;       self.input\_handler = InputHandler(self)

&nbsp;       

&nbsp;       # Hooks

&nbsp;       self.\_before\_navigate\_hooks = \[]

&nbsp;       self.\_after\_navigate\_hooks = \[]

&nbsp;       self.\_state\_watchers = {}

&nbsp;       self.\_running = False

&nbsp;   

&nbsp;   def view(self, name: str, default: bool = False):

&nbsp;       """Decorator to register a view"""

&nbsp;       def decorator(func: Callable):

&nbsp;           self.views\[name] = func

&nbsp;           if default:

&nbsp;               self.default\_view = name

&nbsp;           return func

&nbsp;       return decorator

&nbsp;   

&nbsp;   def navigate(self, view\_name: str, \*\*params):

&nbsp;       """Navigate to a different view"""

&nbsp;       if view\_name not in self.views:

&nbsp;           raise ValueError(f"View '{view\_name}' not found")

&nbsp;       

&nbsp;       # Call hooks

&nbsp;       for hook in self.\_before\_navigate\_hooks:

&nbsp;           hook(self.current\_view, view\_name)

&nbsp;       

&nbsp;       # Exit current view

&nbsp;       if self.current\_view:

&nbsp;           current = self.views\[self.current\_view]()

&nbsp;           if isinstance(current, ViewConfig) and current.on\_exit:

&nbsp;               current.on\_exit()

&nbsp;       

&nbsp;       # Enter new view

&nbsp;       self.current\_view = view\_name

&nbsp;       self.view\_params = params

&nbsp;       view\_config = self.views\[view\_name](\*\*params)

&nbsp;       

&nbsp;       if isinstance(view\_config, ViewConfig) and view\_config.on\_enter:

&nbsp;           view\_config.on\_enter()

&nbsp;       

&nbsp;       # Trigger re-render

&nbsp;       self.renderer.render()

&nbsp;       

&nbsp;       # Call after hooks

&nbsp;       for hook in self.\_after\_navigate\_hooks:

&nbsp;           hook(view\_name)

&nbsp;   

&nbsp;   def run(self):

&nbsp;       """Start the app"""

&nbsp;       self.\_running = True

&nbsp;       

&nbsp;       # Navigate to default view

&nbsp;       if self.default\_view:

&nbsp;           self.navigate(self.default\_view)

&nbsp;       

&nbsp;       # Enter alternate screen

&nbsp;       self.renderer.enter\_alternate\_screen()

&nbsp;       

&nbsp;       try:

&nbsp;           # Main event loop

&nbsp;           while self.\_running:

&nbsp;               self.input\_handler.process\_input()

&nbsp;       finally:

&nbsp;           # Cleanup

&nbsp;           self.renderer.exit\_alternate\_screen()

&nbsp;   

&nbsp;   def exit(self):

&nbsp;       """Exit the app"""

&nbsp;       self.\_running = False

&nbsp;   

&nbsp;   # Hook registration

&nbsp;   def before\_navigate(self, func: Callable):

&nbsp;       self.\_before\_navigate\_hooks.append(func)

&nbsp;       return func

&nbsp;   

&nbsp;   def after\_navigate(self, func: Callable):

&nbsp;       self.\_after\_navigate\_hooks.append(func)

&nbsp;       return func

&nbsp;   

&nbsp;   def watch(self, key: str):

&nbsp;       """Watch for state changes"""

&nbsp;       def decorator(func: Callable):

&nbsp;           if key not in self.\_state\_watchers:

&nbsp;               self.\_state\_watchers\[key] = \[]

&nbsp;           self.\_state\_watchers\[key].append(func)

&nbsp;           return func

&nbsp;       return decorator

```



\## State Management



```python

\# wijjit/core/state.py

from typing import Any, Dict

from collections import UserDict



class State(UserDict):

&nbsp;   """Global application state with change detection"""

&nbsp;   

&nbsp;   def \_\_init\_\_(self):

&nbsp;       super().\_\_init\_\_()

&nbsp;       self.data\['view\_context'] = {}

&nbsp;       self.\_watchers = {}

&nbsp;       self.\_app = None  # Set by Wijjit

&nbsp;   

&nbsp;   def \_\_setitem\_\_(self, key: str, value: Any):

&nbsp;       old\_value = self.data.get(key)

&nbsp;       super().\_\_setitem\_\_(key, value)

&nbsp;       

&nbsp;       # Notify watchers

&nbsp;       if key in self.\_watchers:

&nbsp;           for callback in self.\_watchers\[key]:

&nbsp;               callback(old\_value, value)

&nbsp;       

&nbsp;       # Trigger re-render if app is running

&nbsp;       if self.\_app and self.\_app.\_running:

&nbsp;           self.\_app.renderer.render()

&nbsp;   

&nbsp;   def \_\_getattr\_\_(self, key: str):

&nbsp;       """Allow state.key syntax"""

&nbsp;       try:

&nbsp;           return self.data\[key]

&nbsp;       except KeyError:

&nbsp;           raise AttributeError(f"State has no attribute '{key}'")

&nbsp;   

&nbsp;   def \_\_setattr\_\_(self, key: str, value: Any):

&nbsp;       if key in ('data', '\_watchers', '\_app'):

&nbsp;           super().\_\_setattr\_\_(key, value)

&nbsp;       else:

&nbsp;           self\[key] = value

&nbsp;   

&nbsp;   def update\_context(self, \*\*kwargs):

&nbsp;       """Update view-specific context"""

&nbsp;       self.data\['view\_context'].update(kwargs)



\# Global state instance

state = State()

```



\## Element Base Classes



```python

\# wijjit/elements/base.py

from dataclasses import dataclass

from typing import Optional, Callable, Any, Tuple

from enum import Enum



class ElementType(Enum):

&nbsp;   DISPLAY = "display"      # Non-interactive (text, table, etc.)

&nbsp;   INPUT = "input"          # Accepts text input

&nbsp;   BUTTON = "button"        # Clickable

&nbsp;   SELECTABLE = "selectable" # Keyboard navigation (list, menu, etc.)



@dataclass

class Bounds:

&nbsp;   x: int

&nbsp;   y: int

&nbsp;   width: int

&nbsp;   height: int

&nbsp;   

&nbsp;   def contains(self, x: int, y: int) -> bool:

&nbsp;       return (self.x <= x < self.x + self.width and 

&nbsp;               self.y <= y < self.y + self.height)



class Element:

&nbsp;   """Base class for all UI elements"""

&nbsp;   

&nbsp;   def \_\_init\_\_(self, 

&nbsp;                id: str,

&nbsp;                element\_type: ElementType,

&nbsp;                focusable: bool = False):

&nbsp;       self.id = id

&nbsp;       self.element\_type = element\_type

&nbsp;       self.focusable = focusable

&nbsp;       self.focused = False

&nbsp;       self.bounds: Optional\[Bounds] = None

&nbsp;       self.parent = None

&nbsp;   

&nbsp;   def set\_bounds(self, x: int, y: int, width: int, height: int):

&nbsp;       """Set element position and size"""

&nbsp;       self.bounds = Bounds(x, y, width, height)

&nbsp;   

&nbsp;   def handle\_key(self, key: str, state: Any) -> bool:

&nbsp;       """

&nbsp;       Handle keyboard input

&nbsp;       Returns True if event was handled (stop propagation)

&nbsp;       """

&nbsp;       return False

&nbsp;   

&nbsp;   def handle\_mouse(self, x: int, y: int, button: str) -> bool:

&nbsp;       """Handle mouse input"""

&nbsp;       return False

&nbsp;   

&nbsp;   def render(self, state: Any) -> str:

&nbsp;       """Render element to string"""

&nbsp;       raise NotImplementedError

&nbsp;   

&nbsp;   def calculate\_min\_size(self) -> Tuple\[int, int]:

&nbsp;       """Calculate minimum width and height"""

&nbsp;       return (1, 1)



class Container(Element):

&nbsp;   """Base class for elements that contain other elements"""

&nbsp;   

&nbsp;   def \_\_init\_\_(self, id: str):

&nbsp;       super().\_\_init\_\_(id, ElementType.DISPLAY, focusable=False)

&nbsp;       self.children = \[]

&nbsp;   

&nbsp;   def add\_child(self, child: Element):

&nbsp;       child.parent = self

&nbsp;       self.children.append(child)

&nbsp;   

&nbsp;   def get\_focusable\_children(self):

&nbsp;       """Get all focusable descendants in order"""

&nbsp;       focusable = \[]

&nbsp;       for child in self.children:

&nbsp;           if child.focusable:

&nbsp;               focusable.append(child)

&nbsp;           if isinstance(child, Container):

&nbsp;               focusable.extend(child.get\_focusable\_children())

&nbsp;       return focusable

```



\## Input Elements



```python

\# wijjit/elements/input.py

from .base import Element, ElementType



class TextInput(Element):

&nbsp;   def \_\_init\_\_(self, 

&nbsp;                id: str,

&nbsp;                placeholder: str = "",

&nbsp;                value: str = "",

&nbsp;                password: bool = False,

&nbsp;                on\_change: Optional\[Callable] = None,

&nbsp;                on\_enter: Optional\[Callable] = None):

&nbsp;       super().\_\_init\_\_(id, ElementType.INPUT, focusable=True)

&nbsp;       self.placeholder = placeholder

&nbsp;       self.value = value

&nbsp;       self.password = password

&nbsp;       self.on\_change = on\_change

&nbsp;       self.on\_enter = on\_enter

&nbsp;       self.cursor\_pos = len(value)

&nbsp;   

&nbsp;   def handle\_key(self, key: str, state: Any) -> bool:

&nbsp;       if key == 'enter':

&nbsp;           if self.on\_enter:

&nbsp;               self.on\_enter(self.value)

&nbsp;           return True

&nbsp;       elif key == 'backspace':

&nbsp;           if self.cursor\_pos > 0:

&nbsp;               self.value = (self.value\[:self.cursor\_pos-1] + 

&nbsp;                            self.value\[self.cursor\_pos:])

&nbsp;               self.cursor\_pos -= 1

&nbsp;               if self.on\_change:

&nbsp;                   self.on\_change(self.value)

&nbsp;           return True

&nbsp;       elif key == 'left':

&nbsp;           self.cursor\_pos = max(0, self.cursor\_pos - 1)

&nbsp;           return True

&nbsp;       elif key == 'right':

&nbsp;           self.cursor\_pos = min(len(self.value), self.cursor\_pos + 1)

&nbsp;           return True

&nbsp;       elif len(key) == 1:  # Regular character

&nbsp;           self.value = (self.value\[:self.cursor\_pos] + 

&nbsp;                        key + 

&nbsp;                        self.value\[self.cursor\_pos:])

&nbsp;           self.cursor\_pos += 1

&nbsp;           if self.on\_change:

&nbsp;               self.on\_change(self.value)

&nbsp;           return True

&nbsp;       return False

&nbsp;   

&nbsp;   def render(self, state: Any) -> str:

&nbsp;       display = self.value if not self.password else '\*' \* len(self.value)

&nbsp;       if not display and self.placeholder:

&nbsp;           display = f"\\033\[2m{self.placeholder}\\033\[0m"  # Dim

&nbsp;       

&nbsp;       if self.focused:

&nbsp;           # Show cursor

&nbsp;           before = display\[:self.cursor\_pos]

&nbsp;           after = display\[self.cursor\_pos:]

&nbsp;           return f"{before}█{after}"

&nbsp;       return display



class Button(Element):

&nbsp;   def \_\_init\_\_(self,

&nbsp;                id: str,

&nbsp;                label: str,

&nbsp;                action: Optional\[Callable] = None,

&nbsp;                variant: str = "default"):

&nbsp;       super().\_\_init\_\_(id, ElementType.BUTTON, focusable=True)

&nbsp;       self.label = label

&nbsp;       self.action = action

&nbsp;       self.variant = variant

&nbsp;   

&nbsp;   def handle\_key(self, key: str, state: Any) -> bool:

&nbsp;       if key in ('enter', ' '):

&nbsp;           if self.action:

&nbsp;               self.action()

&nbsp;           return True

&nbsp;       return False

&nbsp;   

&nbsp;   def render(self, state: Any) -> str:

&nbsp;       # Simple button rendering

&nbsp;       style = ""

&nbsp;       if self.variant == "primary":

&nbsp;           style = "\\033\[1;44m"  # Bold blue background

&nbsp;       elif self.focused:

&nbsp;           style = "\\033\[7m"  # Inverse

&nbsp;       

&nbsp;       return f"{style}\[ {self.label} ]\\033\[0m"

```



\## Template Tags



```python

\# wijjit/template/tags.py

from jinja2 import nodes

from jinja2.ext import Extension



class FrameExtension(Extension):

&nbsp;   tags = {'frame'}

&nbsp;   

&nbsp;   def parse(self, parser):

&nbsp;       lineno = next(parser.stream).lineno

&nbsp;       

&nbsp;       # Parse arguments

&nbsp;       args = \[]

&nbsp;       kwargs = \[]

&nbsp;       

&nbsp;       while parser.stream.current.test\_any('name', 'assign'):

&nbsp;           if parser.stream.current.test('assign'):

&nbsp;               key = parser.stream.current.value

&nbsp;               parser.stream.skip()

&nbsp;               parser.stream.expect('assign')

&nbsp;               value = parser.parse\_expression()

&nbsp;               kwargs.append(nodes.Keyword(key, value, lineno=lineno))

&nbsp;           else:

&nbsp;               args.append(parser.parse\_expression())

&nbsp;       

&nbsp;       # Parse body

&nbsp;       body = parser.parse\_statements(\['name:endframe'], drop\_needle=True)

&nbsp;       

&nbsp;       # Create call node

&nbsp;       call = self.call\_method('\_render\_frame', 

&nbsp;                               args + \[nodes.List(kwargs, lineno=lineno)],

&nbsp;                               lineno=lineno)

&nbsp;       

&nbsp;       return nodes.CallBlock(call, \[], \[], body).set\_lineno(lineno)

&nbsp;   

&nbsp;   def \_render\_frame(self, kwargs, caller):

&nbsp;       # This gets called during template rendering

&nbsp;       # Register frame with layout engine and return placeholder

&nbsp;       frame\_id = kwargs.get('id', f'frame\_{id(caller)}')

&nbsp;       content = caller()

&nbsp;       

&nbsp;       # Store in context for layout engine

&nbsp;       context = self.environment.wijjit\_context

&nbsp;       context.register\_frame(frame\_id, kwargs, content)

&nbsp;       

&nbsp;       return f"{{{{FRAME:{frame\_id}}}}}"



class TextInputExtension(Extension):

&nbsp;   tags = {'textinput'}

&nbsp;   

&nbsp;   def parse(self, parser):

&nbsp;       lineno = next(parser.stream).lineno

&nbsp;       kwargs = self.\_parse\_kwargs(parser)

&nbsp;       

&nbsp;       call = self.call\_method('\_render\_textinput',

&nbsp;                              \[nodes.List(kwargs, lineno=lineno)],

&nbsp;                              lineno=lineno)

&nbsp;       return nodes.Output(\[call], lineno=lineno)

&nbsp;   

&nbsp;   def \_render\_textinput(self, kwargs):

&nbsp;       element\_id = kwargs.get('id', f'input\_{id(kwargs)}')

&nbsp;       

&nbsp;       # Register with context

&nbsp;       context = self.environment.wijjit\_context

&nbsp;       context.register\_element(element\_id, 'textinput', kwargs)

&nbsp;       

&nbsp;       return f"{{{{INPUT:{element\_id}}}}}"

&nbsp;   

&nbsp;   def \_parse\_kwargs(self, parser):

&nbsp;       kwargs = \[]

&nbsp;       while not parser.stream.current.test('block\_end'):

&nbsp;           if parser.stream.current.test('name'):

&nbsp;               key = parser.stream.current.value

&nbsp;               parser.stream.skip()

&nbsp;               parser.stream.expect('assign')

&nbsp;               value = parser.parse\_expression()

&nbsp;               kwargs.append(nodes.Keyword(key, value, lineno=parser.stream.current.lineno))

&nbsp;       return kwargs



\# Similar extensions for button, table, etc.

```



\## Layout Engine



```python

\# wijjit/layout/engine.py

from typing import Dict, List, Tuple

from ..elements.base import Element, Container, Bounds



class LayoutNode:

&nbsp;   def \_\_init\_\_(self, 

&nbsp;                element: Element,

&nbsp;                width: str | int = "auto",

&nbsp;                height: str | int = "auto",

&nbsp;                fill: bool = False):

&nbsp;       self.element = element

&nbsp;       self.width = width

&nbsp;       self.height = height

&nbsp;       self.fill = fill

&nbsp;       self.children: List\[LayoutNode] = \[]

&nbsp;       self.calculated\_width = 0

&nbsp;       self.calculated\_height = 0

&nbsp;       self.x = 0

&nbsp;       self.y = 0

&nbsp;   

&nbsp;   def add\_child(self, node: 'LayoutNode'):

&nbsp;       self.children.append(node)



class LayoutEngine:

&nbsp;   def \_\_init\_\_(self, terminal\_width: int, terminal\_height: int):

&nbsp;       self.terminal\_width = terminal\_width

&nbsp;       self.terminal\_height = terminal\_height

&nbsp;       self.root: Optional\[LayoutNode] = None

&nbsp;       self.element\_registry: Dict\[str, Element] = {}

&nbsp;   

&nbsp;   def calculate\_layout(self, root: LayoutNode):

&nbsp;       """Calculate positions and sizes for all elements"""

&nbsp;       self.root = root

&nbsp;       

&nbsp;       # Phase 1: Calculate sizes bottom-up

&nbsp;       self.\_calculate\_sizes(root, self.terminal\_width, self.terminal\_height)

&nbsp;       

&nbsp;       # Phase 2: Assign positions top-down

&nbsp;       self.\_assign\_positions(root, 0, 0)

&nbsp;       

&nbsp;       # Phase 3: Set bounds on actual elements

&nbsp;       self.\_apply\_bounds(root)

&nbsp;   

&nbsp;   def \_calculate\_sizes(self, 

&nbsp;                       node: LayoutNode, 

&nbsp;                       available\_width: int, 

&nbsp;                       available\_height: int):

&nbsp;       """Calculate node sizes based on constraints"""

&nbsp;       

&nbsp;       # Handle explicit sizes

&nbsp;       if isinstance(node.width, int):

&nbsp;           node.calculated\_width = node.width

&nbsp;       elif node.width == "100%" or node.width == "fill":

&nbsp;           node.calculated\_width = available\_width

&nbsp;       else:  # "auto"

&nbsp;           # Calculate based on content

&nbsp;           if node.children:

&nbsp;               # For now, simple sum of children

&nbsp;               node.calculated\_width = sum(

&nbsp;                   self.\_calculate\_sizes(child, available\_width, available\_height)\[0]

&nbsp;                   for child in node.children

&nbsp;               )

&nbsp;           else:

&nbsp;               min\_w, \_ = node.element.calculate\_min\_size()

&nbsp;               node.calculated\_width = min\_w

&nbsp;       

&nbsp;       # Similar for height

&nbsp;       if isinstance(node.height, int):

&nbsp;           node.calculated\_height = node.height

&nbsp;       elif node.height == "100%" or node.height == "fill":

&nbsp;           node.calculated\_height = available\_height

&nbsp;       else:

&nbsp;           if node.children:

&nbsp;               node.calculated\_height = sum(

&nbsp;                   self.\_calculate\_sizes(child, available\_width, available\_height)\[1]

&nbsp;                   for child in node.children

&nbsp;               )

&nbsp;           else:

&nbsp;               \_, min\_h = node.element.calculate\_min\_size()

&nbsp;               node.calculated\_height = min\_h

&nbsp;       

&nbsp;       return (node.calculated\_width, node.calculated\_height)

&nbsp;   

&nbsp;   def \_assign\_positions(self, node: LayoutNode, x: int, y: int):

&nbsp;       """Assign absolute positions to nodes"""

&nbsp;       node.x = x

&nbsp;       node.y = y

&nbsp;       

&nbsp;       # Layout children (for now, simple vertical stack)

&nbsp;       current\_y = y

&nbsp;       for child in node.children:

&nbsp;           self.\_assign\_positions(child, x, current\_y)

&nbsp;           current\_y += child.calculated\_height

&nbsp;   

&nbsp;   def \_apply\_bounds(self, node: LayoutNode):

&nbsp;       """Apply calculated bounds to elements"""

&nbsp;       node.element.set\_bounds(

&nbsp;           node.x, 

&nbsp;           node.y, 

&nbsp;           node.calculated\_width, 

&nbsp;           node.calculated\_height

&nbsp;       )

&nbsp;       

&nbsp;       for child in node.children:

&nbsp;           self.\_apply\_bounds(child)

&nbsp;   

&nbsp;   def register\_element(self, element: Element):

&nbsp;       """Register an element for focus management"""

&nbsp;       self.element\_registry\[element.id] = element

&nbsp;   

&nbsp;   def get\_focusable\_elements(self) -> List\[Element]:

&nbsp;       """Get all focusable elements in render order"""

&nbsp;       if not self.root:

&nbsp;           return \[]

&nbsp;       return self.\_collect\_focusable(self.root)

&nbsp;   

&nbsp;   def \_collect\_focusable(self, node: LayoutNode) -> List\[Element]:

&nbsp;       focusable = \[]

&nbsp;       if node.element.focusable:

&nbsp;           focusable.append(node.element)

&nbsp;       for child in node.children:

&nbsp;           focusable.extend(self.\_collect\_focusable(child))

&nbsp;       return focusable

```



\## Renderer



```python

\# wijjit/core/renderer.py

import os

from jinja2 import Environment, FileSystemLoader

from ..template.tags import FrameExtension, TextInputExtension

from ..layout.engine import LayoutEngine



class Renderer:

&nbsp;   def \_\_init\_\_(self, app):

&nbsp;       self.app = app

&nbsp;       

&nbsp;       # Setup Jinja environment

&nbsp;       self.jinja\_env = Environment(

&nbsp;           loader=FileSystemLoader(app.template\_dir),

&nbsp;           extensions=\[FrameExtension, TextInputExtension]

&nbsp;       )

&nbsp;       

&nbsp;       # Add custom filters

&nbsp;       self.jinja\_env.filters\['humanize'] = self.\_humanize

&nbsp;       self.jinja\_env.filters\['timeago'] = self.\_timeago

&nbsp;       

&nbsp;       # Terminal state

&nbsp;       self.in\_alternate\_screen = False

&nbsp;       self.last\_render = ""

&nbsp;   

&nbsp;   def render(self):

&nbsp;       """Render the current view"""

&nbsp;       if not self.app.current\_view:

&nbsp;           return

&nbsp;       

&nbsp;       # Get view config

&nbsp;       view\_func = self.app.views\[self.app.current\_view]

&nbsp;       view\_config = view\_func(\*\*self.app.view\_params)

&nbsp;       

&nbsp;       # Get terminal size

&nbsp;       width, height = os.get\_terminal\_size()

&nbsp;       

&nbsp;       # Setup layout engine

&nbsp;       layout = LayoutEngine(width, height)

&nbsp;       

&nbsp;       # Attach to jinja context

&nbsp;       self.jinja\_env.wijjit\_context = layout

&nbsp;       

&nbsp;       # Render template

&nbsp;       if view\_config.template.endswith('.tui'):

&nbsp;           template = self.jinja\_env.get\_template(view\_config.template)

&nbsp;       else:

&nbsp;           template = self.jinja\_env.from\_string(view\_config.template)

&nbsp;       

&nbsp;       output = template.render(\*\*view\_config.data, state=self.app.state)

&nbsp;       

&nbsp;       # Clear screen and render

&nbsp;       self.\_clear\_screen()

&nbsp;       print(output, end='', flush=True)

&nbsp;       

&nbsp;       self.last\_render = output

&nbsp;   

&nbsp;   def enter\_alternate\_screen(self):

&nbsp;       """Switch to alternate screen buffer"""

&nbsp;       print("\\033\[?1049h", end='', flush=True)  # Enter alternate screen

&nbsp;       print("\\033\[?25l", end='', flush=True)    # Hide cursor

&nbsp;       self.in\_alternate\_screen = True

&nbsp;   

&nbsp;   def exit\_alternate\_screen(self):

&nbsp;       """Return to main screen buffer"""

&nbsp;       print("\\033\[?25h", end='', flush=True)    # Show cursor

&nbsp;       print("\\033\[?1049l", end='', flush=True)  # Exit alternate screen

&nbsp;       self.in\_alternate\_screen = False

&nbsp;   

&nbsp;   def \_clear\_screen(self):

&nbsp;       print("\\033\[2J\\033\[H", end='', flush=True)

&nbsp;   

&nbsp;   def \_humanize(self, size: int) -> str:

&nbsp;       """Convert bytes to human readable"""

&nbsp;       for unit in \['B', 'KB', 'MB', 'GB']:

&nbsp;           if size < 1024:

&nbsp;               return f"{size:.1f}{unit}"

&nbsp;           size /= 1024

&nbsp;       return f"{size:.1f}TB"

&nbsp;   

&nbsp;   def \_timeago(self, dt) -> str:

&nbsp;       """Convert datetime to relative time"""

&nbsp;       # Simplified implementation

&nbsp;       return "2m ago"

```



\## Input Handler



```python

\# wijjit/terminal/input.py

import sys

import tty

import termios

from typing import Optional



class InputHandler:

&nbsp;   def \_\_init\_\_(self, app):

&nbsp;       self.app = app

&nbsp;       self.focused\_index = 0

&nbsp;       self.focusable\_elements = \[]

&nbsp;   

&nbsp;   def process\_input(self):

&nbsp;       """Read and process one input event"""

&nbsp;       key = self.\_read\_key()

&nbsp;       

&nbsp;       if key == 'tab':

&nbsp;           self.\_handle\_tab()

&nbsp;       elif key == 'shift+tab':

&nbsp;           self.\_handle\_shift\_tab()

&nbsp;       elif key == 'ctrl+c':

&nbsp;           self.app.exit()

&nbsp;       else:

&nbsp;           # Send to focused element

&nbsp;           if self.focusable\_elements:

&nbsp;               focused = self.focusable\_elements\[self.focused\_index]

&nbsp;               handled = focused.handle\_key(key, self.app.state)

&nbsp;               

&nbsp;               if handled:

&nbsp;                   self.app.renderer.render()

&nbsp;   

&nbsp;   def \_handle\_tab(self):

&nbsp;       """Move focus to next element"""

&nbsp;       if not self.focusable\_elements:

&nbsp;           return

&nbsp;       

&nbsp;       self.focusable\_elements\[self.focused\_index].focused = False

&nbsp;       self.focused\_index = (self.focused\_index + 1) % len(self.focusable\_elements)

&nbsp;       self.focusable\_elements\[self.focused\_index].focused = True

&nbsp;       self.app.renderer.render()

&nbsp;   

&nbsp;   def \_handle\_shift\_tab(self):

&nbsp;       """Move focus to previous element"""

&nbsp;       if not self.focusable\_elements:

&nbsp;           return

&nbsp;       

&nbsp;       self.focusable\_elements\[self.focused\_index].focused = False

&nbsp;       self.focused\_index = (self.focused\_index - 1) % len(self.focusable\_elements)

&nbsp;       self.focusable\_elements\[self.focused\_index].focused = True

&nbsp;       self.app.renderer.render()

&nbsp;   

&nbsp;   def \_read\_key(self) -> str:

&nbsp;       """Read a single keypress (blocking)"""

&nbsp;       # Save terminal settings

&nbsp;       fd = sys.stdin.fileno()

&nbsp;       old\_settings = termios.tcgetattr(fd)

&nbsp;       

&nbsp;       try:

&nbsp;           tty.setraw(fd)

&nbsp;           ch = sys.stdin.read(1)

&nbsp;           

&nbsp;           # Handle escape sequences

&nbsp;           if ch == '\\x1b':

&nbsp;               ch2 = sys.stdin.read(1)

&nbsp;               if ch2 == '\[':

&nbsp;                   ch3 = sys.stdin.read(1)

&nbsp;                   if ch3 == 'A': return 'up'

&nbsp;                   elif ch3 == 'B': return 'down'

&nbsp;                   elif ch3 == 'C': return 'right'

&nbsp;                   elif ch3 == 'D': return 'left'

&nbsp;                   elif ch3 == 'Z': return 'shift+tab'

&nbsp;           elif ch == '\\t': return 'tab'

&nbsp;           elif ch == '\\r': return 'enter'

&nbsp;           elif ch == '\\x7f': return 'backspace'

&nbsp;           elif ch == '\\x03': return 'ctrl+c'

&nbsp;           

&nbsp;           return ch

&nbsp;       finally:

&nbsp;           termios.tcsetattr(fd, termios.TCSADRAIN, old\_settings)

```



\## Example Usage



```python

\# example.py

from wijjit import Wijjit, state



app = Wijjit()



\# Initialize state

state.items = \["Buy milk", "Walk dog", "Write code"]

state.new\_item = ""



@app.view('main', default=True)

def main\_view():

&nbsp;   return {

&nbsp;       'template': '''

{% frame title="Todo List" border="double" width="100%" height="100%" %}

&nbsp; 

&nbsp; {% frame id="list" fill=true %}

&nbsp;   {% for item in items %}

&nbsp;     {{ item }}

&nbsp;   {% endfor %}

&nbsp; {% endframe %}

&nbsp; 

&nbsp; {% frame id="input" height=3 %}

&nbsp;   New: {% textinput id="new" value=state.new\_item on\_enter="add\_item" %}

&nbsp; {% endframe %}

&nbsp; 

&nbsp; {% frame id="actions" height=3 %}

&nbsp;   {% button id="quit" action="quit" %}Quit{% endbutton %}

&nbsp; {% endframe %}

&nbsp; 

{% endframe %}

&nbsp;       ''',

&nbsp;       'data': {

&nbsp;           'items': state.items

&nbsp;       },

&nbsp;       'handlers': {

&nbsp;           'add\_item': add\_item,

&nbsp;           'quit': app.exit

&nbsp;       }

&nbsp;   }



def add\_item(text):

&nbsp;   if text.strip():

&nbsp;       state.items.append(text)

&nbsp;       state.new\_item = ""



if \_\_name\_\_ == '\_\_main\_\_':

&nbsp;   app.run()

```



This gives us:

\- ✅ Clean decorator-based API

\- ✅ Global state management

\- ✅ Template-based layouts

\- ✅ Custom Jinja tags

\- ✅ Focus management

\- ✅ Event handling

\- ✅ View navigation



