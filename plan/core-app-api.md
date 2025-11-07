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
   template: str
   data: Dict\[str, Any]
   handlers: Dict\[str, Callable]
   on\_enter: Optional\[Callable] = None
   on\_exit: Optional\[Callable] = None



class Wijjit:
   def \_\_init\_\_(self, template\_dir: str = 'templates'):
       self.views: Dict\[str, Callable] = {}
       self.default\_view: Optional\[str] = None
       self.current\_view: Optional\[str] = None
       self.template\_dir = template\_dir
       
       # Core systems
       self.state = State()
       self.renderer = Renderer(self)
       self.input\_handler = InputHandler(self)
       
       # Hooks
       self.\_before\_navigate\_hooks = \[]
       self.\_after\_navigate\_hooks = \[]
       self.\_state\_watchers = {}
       self.\_running = False
   
   def view(self, name: str, default: bool = False):
       """Decorator to register a view"""
       def decorator(func: Callable):
           self.views\[name] = func
           if default:
               self.default\_view = name
           return func
       return decorator
   
   def navigate(self, view\_name: str, \*\*params):
       """Navigate to a different view"""
       if view\_name not in self.views:
           raise ValueError(f"View '{view\_name}' not found")
       
       # Call hooks
       for hook in self.\_before\_navigate\_hooks:
           hook(self.current\_view, view\_name)
       
       # Exit current view
       if self.current\_view:
           current = self.views\[self.current\_view]()
           if isinstance(current, ViewConfig) and current.on\_exit:
               current.on\_exit()
       
       # Enter new view
       self.current\_view = view\_name
       self.view\_params = params
       view\_config = self.views\[view\_name](\*\*params)
       
       if isinstance(view\_config, ViewConfig) and view\_config.on\_enter:
           view\_config.on\_enter()
       
       # Trigger re-render
       self.renderer.render()
       
       # Call after hooks
       for hook in self.\_after\_navigate\_hooks:
           hook(view\_name)
   
   def run(self):
       """Start the app"""
       self.\_running = True
       
       # Navigate to default view
       if self.default\_view:
           self.navigate(self.default\_view)
       
       # Enter alternate screen
       self.renderer.enter\_alternate\_screen()
       
       try:
           # Main event loop
           while self.\_running:
               self.input\_handler.process\_input()
       finally:
           # Cleanup
           self.renderer.exit\_alternate\_screen()
   
   def exit(self):
       """Exit the app"""
       self.\_running = False
   
   # Hook registration
   def before\_navigate(self, func: Callable):
       self.\_before\_navigate\_hooks.append(func)
       return func
   
   def after\_navigate(self, func: Callable):
       self.\_after\_navigate\_hooks.append(func)
       return func
   
   def watch(self, key: str):
       """Watch for state changes"""
       def decorator(func: Callable):
           if key not in self.\_state\_watchers:
               self.\_state\_watchers\[key] = \[]
           self.\_state\_watchers\[key].append(func)
           return func
       return decorator

```



\## State Management



```python

\# wijjit/core/state.py

from typing import Any, Dict

from collections import UserDict



class State(UserDict):
   """Global application state with change detection"""
   
   def \_\_init\_\_(self):
       super().\_\_init\_\_()
       self.data\['view\_context'] = {}
       self.\_watchers = {}
       self.\_app = None  # Set by Wijjit
   
   def \_\_setitem\_\_(self, key: str, value: Any):
       old\_value = self.data.get(key)
       super().\_\_setitem\_\_(key, value)
       
       # Notify watchers
       if key in self.\_watchers:
           for callback in self.\_watchers\[key]:
               callback(old\_value, value)
       
       # Trigger re-render if app is running
       if self.\_app and self.\_app.\_running:
           self.\_app.renderer.render()
   
   def \_\_getattr\_\_(self, key: str):
       """Allow state.key syntax"""
       try:
           return self.data\[key]
       except KeyError:
           raise AttributeError(f"State has no attribute '{key}'")
   
   def \_\_setattr\_\_(self, key: str, value: Any):
       if key in ('data', '\_watchers', '\_app'):
           super().\_\_setattr\_\_(key, value)
       else:
           self\[key] = value
   
   def update\_context(self, \*\*kwargs):
       """Update view-specific context"""
       self.data\['view\_context'].update(kwargs)



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
   DISPLAY = "display"      # Non-interactive (text, table, etc.)
   INPUT = "input"          # Accepts text input
   BUTTON = "button"        # Clickable
   SELECTABLE = "selectable" # Keyboard navigation (list, menu, etc.)



@dataclass

class Bounds:
   x: int
   y: int
   width: int
   height: int
   
   def contains(self, x: int, y: int) -> bool:
       return (self.x <= x < self.x + self.width and 
               self.y <= y < self.y + self.height)



class Element:
   """Base class for all UI elements"""
   
   def \_\_init\_\_(self, 
                id: str,
                element\_type: ElementType,
                focusable: bool = False):
       self.id = id
       self.element\_type = element\_type
       self.focusable = focusable
       self.focused = False
       self.bounds: Optional\[Bounds] = None
       self.parent = None
   
   def set\_bounds(self, x: int, y: int, width: int, height: int):
       """Set element position and size"""
       self.bounds = Bounds(x, y, width, height)
   
   def handle\_key(self, key: str, state: Any) -> bool:
       """
       Handle keyboard input
       Returns True if event was handled (stop propagation)
       """
       return False
   
   def handle\_mouse(self, x: int, y: int, button: str) -> bool:
       """Handle mouse input"""
       return False
   
   def render(self, state: Any) -> str:
       """Render element to string"""
       raise NotImplementedError
   
   def calculate\_min\_size(self) -> Tuple\[int, int]:
       """Calculate minimum width and height"""
       return (1, 1)



class Container(Element):
   """Base class for elements that contain other elements"""
   
   def \_\_init\_\_(self, id: str):
       super().\_\_init\_\_(id, ElementType.DISPLAY, focusable=False)
       self.children = \[]
   
   def add\_child(self, child: Element):
       child.parent = self
       self.children.append(child)
   
   def get\_focusable\_children(self):
       """Get all focusable descendants in order"""
       focusable = \[]
       for child in self.children:
           if child.focusable:
               focusable.append(child)
           if isinstance(child, Container):
               focusable.extend(child.get\_focusable\_children())
       return focusable

```



\## Input Elements



```python

\# wijjit/elements/input.py

from .base import Element, ElementType



class TextInput(Element):
   def \_\_init\_\_(self, 
                id: str,
                placeholder: str = "",
                value: str = "",
                password: bool = False,
                on\_change: Optional\[Callable] = None,
                on\_enter: Optional\[Callable] = None):
       super().\_\_init\_\_(id, ElementType.INPUT, focusable=True)
       self.placeholder = placeholder
       self.value = value
       self.password = password
       self.on\_change = on\_change
       self.on\_enter = on\_enter
       self.cursor\_pos = len(value)
   
   def handle\_key(self, key: str, state: Any) -> bool:
       if key == 'enter':
           if self.on\_enter:
               self.on\_enter(self.value)
           return True
       elif key == 'backspace':
           if self.cursor\_pos > 0:
               self.value = (self.value\[:self.cursor\_pos-1] + 
                            self.value\[self.cursor\_pos:])
               self.cursor\_pos -= 1
               if self.on\_change:
                   self.on\_change(self.value)
           return True
       elif key == 'left':
           self.cursor\_pos = max(0, self.cursor\_pos - 1)
           return True
       elif key == 'right':
           self.cursor\_pos = min(len(self.value), self.cursor\_pos + 1)
           return True
       elif len(key) == 1:  # Regular character
           self.value = (self.value\[:self.cursor\_pos] + 
                        key + 
                        self.value\[self.cursor\_pos:])
           self.cursor\_pos += 1
           if self.on\_change:
               self.on\_change(self.value)
           return True
       return False
   
   def render(self, state: Any) -> str:
       display = self.value if not self.password else '\*' \* len(self.value)
       if not display and self.placeholder:
           display = f"\\033\[2m{self.placeholder}\\033\[0m"  # Dim
       
       if self.focused:
           # Show cursor
           before = display\[:self.cursor\_pos]
           after = display\[self.cursor\_pos:]
           return f"{before}█{after}"
       return display



class Button(Element):
   def \_\_init\_\_(self,
                id: str,
                label: str,
                action: Optional\[Callable] = None,
                variant: str = "default"):
       super().\_\_init\_\_(id, ElementType.BUTTON, focusable=True)
       self.label = label
       self.action = action
       self.variant = variant
   
   def handle\_key(self, key: str, state: Any) -> bool:
       if key in ('enter', ' '):
           if self.action:
               self.action()
           return True
       return False
   
   def render(self, state: Any) -> str:
       # Simple button rendering
       style = ""
       if self.variant == "primary":
           style = "\\033\[1;44m"  # Bold blue background
       elif self.focused:
           style = "\\033\[7m"  # Inverse
       
       return f"{style}\[ {self.label} ]\\033\[0m"

```



\## Template Tags



```python

\# wijjit/template/tags.py

from jinja2 import nodes

from jinja2.ext import Extension



class FrameExtension(Extension):
   tags = {'frame'}
   
   def parse(self, parser):
       lineno = next(parser.stream).lineno
       
       # Parse arguments
       args = \[]
       kwargs = \[]
       
       while parser.stream.current.test\_any('name', 'assign'):
           if parser.stream.current.test('assign'):
               key = parser.stream.current.value
               parser.stream.skip()
               parser.stream.expect('assign')
               value = parser.parse\_expression()
               kwargs.append(nodes.Keyword(key, value, lineno=lineno))
           else:
               args.append(parser.parse\_expression())
       
       # Parse body
       body = parser.parse\_statements(\['name:endframe'], drop\_needle=True)
       
       # Create call node
       call = self.call\_method('\_render\_frame', 
                               args + \[nodes.List(kwargs, lineno=lineno)],
                               lineno=lineno)
       
       return nodes.CallBlock(call, \[], \[], body).set\_lineno(lineno)
   
   def \_render\_frame(self, kwargs, caller):
       # This gets called during template rendering
       # Register frame with layout engine and return placeholder
       frame\_id = kwargs.get('id', f'frame\_{id(caller)}')
       content = caller()
       
       # Store in context for layout engine
       context = self.environment.wijjit\_context
       context.register\_frame(frame\_id, kwargs, content)
       
       return f"{{{{FRAME:{frame\_id}}}}}"



class TextInputExtension(Extension):
   tags = {'textinput'}
   
   def parse(self, parser):
       lineno = next(parser.stream).lineno
       kwargs = self.\_parse\_kwargs(parser)
       
       call = self.call\_method('\_render\_textinput',
                              \[nodes.List(kwargs, lineno=lineno)],
                              lineno=lineno)
       return nodes.Output(\[call], lineno=lineno)
   
   def \_render\_textinput(self, kwargs):
       element\_id = kwargs.get('id', f'input\_{id(kwargs)}')
       
       # Register with context
       context = self.environment.wijjit\_context
       context.register\_element(element\_id, 'textinput', kwargs)
       
       return f"{{{{INPUT:{element\_id}}}}}"
   
   def \_parse\_kwargs(self, parser):
       kwargs = \[]
       while not parser.stream.current.test('block\_end'):
           if parser.stream.current.test('name'):
               key = parser.stream.current.value
               parser.stream.skip()
               parser.stream.expect('assign')
               value = parser.parse\_expression()
               kwargs.append(nodes.Keyword(key, value, lineno=parser.stream.current.lineno))
       return kwargs



\# Similar extensions for button, table, etc.

```



\## Layout Engine



```python

\# wijjit/layout/engine.py

from typing import Dict, List, Tuple

from ..elements.base import Element, Container, Bounds



class LayoutNode:
   def \_\_init\_\_(self, 
                element: Element,
                width: str | int = "auto",
                height: str | int = "auto",
                fill: bool = False):
       self.element = element
       self.width = width
       self.height = height
       self.fill = fill
       self.children: List\[LayoutNode] = \[]
       self.calculated\_width = 0
       self.calculated\_height = 0
       self.x = 0
       self.y = 0
   
   def add\_child(self, node: 'LayoutNode'):
       self.children.append(node)



class LayoutEngine:
   def \_\_init\_\_(self, terminal\_width: int, terminal\_height: int):
       self.terminal\_width = terminal\_width
       self.terminal\_height = terminal\_height
       self.root: Optional\[LayoutNode] = None
       self.element\_registry: Dict\[str, Element] = {}
   
   def calculate\_layout(self, root: LayoutNode):
       """Calculate positions and sizes for all elements"""
       self.root = root
       
       # Phase 1: Calculate sizes bottom-up
       self.\_calculate\_sizes(root, self.terminal\_width, self.terminal\_height)
       
       # Phase 2: Assign positions top-down
       self.\_assign\_positions(root, 0, 0)
       
       # Phase 3: Set bounds on actual elements
       self.\_apply\_bounds(root)
   
   def \_calculate\_sizes(self, 
                       node: LayoutNode, 
                       available\_width: int, 
                       available\_height: int):
       """Calculate node sizes based on constraints"""
       
       # Handle explicit sizes
       if isinstance(node.width, int):
           node.calculated\_width = node.width
       elif node.width == "100%" or node.width == "fill":
           node.calculated\_width = available\_width
       else:  # "auto"
           # Calculate based on content
           if node.children:
               # For now, simple sum of children
               node.calculated\_width = sum(
                   self.\_calculate\_sizes(child, available\_width, available\_height)\[0]
                   for child in node.children
               )
           else:
               min\_w, \_ = node.element.calculate\_min\_size()
               node.calculated\_width = min\_w
       
       # Similar for height
       if isinstance(node.height, int):
           node.calculated\_height = node.height
       elif node.height == "100%" or node.height == "fill":
           node.calculated\_height = available\_height
       else:
           if node.children:
               node.calculated\_height = sum(
                   self.\_calculate\_sizes(child, available\_width, available\_height)\[1]
                   for child in node.children
               )
           else:
               \_, min\_h = node.element.calculate\_min\_size()
               node.calculated\_height = min\_h
       
       return (node.calculated\_width, node.calculated\_height)
   
   def \_assign\_positions(self, node: LayoutNode, x: int, y: int):
       """Assign absolute positions to nodes"""
       node.x = x
       node.y = y
       
       # Layout children (for now, simple vertical stack)
       current\_y = y
       for child in node.children:
           self.\_assign\_positions(child, x, current\_y)
           current\_y += child.calculated\_height
   
   def \_apply\_bounds(self, node: LayoutNode):
       """Apply calculated bounds to elements"""
       node.element.set\_bounds(
           node.x, 
           node.y, 
           node.calculated\_width, 
           node.calculated\_height
       )
       
       for child in node.children:
           self.\_apply\_bounds(child)
   
   def register\_element(self, element: Element):
       """Register an element for focus management"""
       self.element\_registry\[element.id] = element
   
   def get\_focusable\_elements(self) -> List\[Element]:
       """Get all focusable elements in render order"""
       if not self.root:
           return \[]
       return self.\_collect\_focusable(self.root)
   
   def \_collect\_focusable(self, node: LayoutNode) -> List\[Element]:
       focusable = \[]
       if node.element.focusable:
           focusable.append(node.element)
       for child in node.children:
           focusable.extend(self.\_collect\_focusable(child))
       return focusable

```



\## Renderer



```python

\# wijjit/core/renderer.py

import os

from jinja2 import Environment, FileSystemLoader

from ..template.tags import FrameExtension, TextInputExtension

from ..layout.engine import LayoutEngine



class Renderer:
   def \_\_init\_\_(self, app):
       self.app = app
       
       # Setup Jinja environment
       self.jinja\_env = Environment(
           loader=FileSystemLoader(app.template\_dir),
           extensions=\[FrameExtension, TextInputExtension]
       )
       
       # Add custom filters
       self.jinja\_env.filters\['humanize'] = self.\_humanize
       self.jinja\_env.filters\['timeago'] = self.\_timeago
       
       # Terminal state
       self.in\_alternate\_screen = False
       self.last\_render = ""
   
   def render(self):
       """Render the current view"""
       if not self.app.current\_view:
           return
       
       # Get view config
       view\_func = self.app.views\[self.app.current\_view]
       view\_config = view\_func(\*\*self.app.view\_params)
       
       # Get terminal size
       width, height = os.get\_terminal\_size()
       
       # Setup layout engine
       layout = LayoutEngine(width, height)
       
       # Attach to jinja context
       self.jinja\_env.wijjit\_context = layout
       
       # Render template
       if view\_config.template.endswith('.tui'):
           template = self.jinja\_env.get\_template(view\_config.template)
       else:
           template = self.jinja\_env.from\_string(view\_config.template)
       
       output = template.render(\*\*view\_config.data, state=self.app.state)
       
       # Clear screen and render
       self.\_clear\_screen()
       print(output, end='', flush=True)
       
       self.last\_render = output
   
   def enter\_alternate\_screen(self):
       """Switch to alternate screen buffer"""
       print("\\033\[?1049h", end='', flush=True)  # Enter alternate screen
       print("\\033\[?25l", end='', flush=True)    # Hide cursor
       self.in\_alternate\_screen = True
   
   def exit\_alternate\_screen(self):
       """Return to main screen buffer"""
       print("\\033\[?25h", end='', flush=True)    # Show cursor
       print("\\033\[?1049l", end='', flush=True)  # Exit alternate screen
       self.in\_alternate\_screen = False
   
   def \_clear\_screen(self):
       print("\\033\[2J\\033\[H", end='', flush=True)
   
   def \_humanize(self, size: int) -> str:
       """Convert bytes to human readable"""
       for unit in \['B', 'KB', 'MB', 'GB']:
           if size < 1024:
               return f"{size:.1f}{unit}"
           size /= 1024
       return f"{size:.1f}TB"
   
   def \_timeago(self, dt) -> str:
       """Convert datetime to relative time"""
       # Simplified implementation
       return "2m ago"

```



\## Input Handler



```python

\# wijjit/terminal/input.py

import sys

import tty

import termios

from typing import Optional



class InputHandler:
   def \_\_init\_\_(self, app):
       self.app = app
       self.focused\_index = 0
       self.focusable\_elements = \[]
   
   def process\_input(self):
       """Read and process one input event"""
       key = self.\_read\_key()
       
       if key == 'tab':
           self.\_handle\_tab()
       elif key == 'shift+tab':
           self.\_handle\_shift\_tab()
       elif key == 'ctrl+c':
           self.app.exit()
       else:
           # Send to focused element
           if self.focusable\_elements:
               focused = self.focusable\_elements\[self.focused\_index]
               handled = focused.handle\_key(key, self.app.state)
               
               if handled:
                   self.app.renderer.render()
   
   def \_handle\_tab(self):
       """Move focus to next element"""
       if not self.focusable\_elements:
           return
       
       self.focusable\_elements\[self.focused\_index].focused = False
       self.focused\_index = (self.focused\_index + 1) % len(self.focusable\_elements)
       self.focusable\_elements\[self.focused\_index].focused = True
       self.app.renderer.render()
   
   def \_handle\_shift\_tab(self):
       """Move focus to previous element"""
       if not self.focusable\_elements:
           return
       
       self.focusable\_elements\[self.focused\_index].focused = False
       self.focused\_index = (self.focused\_index - 1) % len(self.focusable\_elements)
       self.focusable\_elements\[self.focused\_index].focused = True
       self.app.renderer.render()
   
   def \_read\_key(self) -> str:
       """Read a single keypress (blocking)"""
       # Save terminal settings
       fd = sys.stdin.fileno()
       old\_settings = termios.tcgetattr(fd)
       
       try:
           tty.setraw(fd)
           ch = sys.stdin.read(1)
           
           # Handle escape sequences
           if ch == '\\x1b':
               ch2 = sys.stdin.read(1)
               if ch2 == '\[':
                   ch3 = sys.stdin.read(1)
                   if ch3 == 'A': return 'up'
                   elif ch3 == 'B': return 'down'
                   elif ch3 == 'C': return 'right'
                   elif ch3 == 'D': return 'left'
                   elif ch3 == 'Z': return 'shift+tab'
           elif ch == '\\t': return 'tab'
           elif ch == '\\r': return 'enter'
           elif ch == '\\x7f': return 'backspace'
           elif ch == '\\x03': return 'ctrl+c'
           
           return ch
       finally:
           termios.tcsetattr(fd, termios.TCSADRAIN, old\_settings)

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
   return {
       'template': '''

{% frame title="Todo List" border="double" width="100%" height="100%" %}
 
 {% frame id="list" fill=true %}
   {% for item in items %}
     {{ item }}
   {% endfor %}
 {% endframe %}
 
 {% frame id="input" height=3 %}
   New: {% textinput id="new" value=state.new\_item on\_enter="add\_item" %}
 {% endframe %}
 
 {% frame id="actions" height=3 %}
   {% button id="quit" action="quit" %}Quit{% endbutton %}
 {% endframe %}
 

{% endframe %}
       ''',
       'data': {
           'items': state.items
       },
       'handlers': {
           'add\_item': add\_item,
           'quit': app.exit
       }
   }



def add\_item(text):
   if text.strip():
       state.items.append(text)
       state.new\_item = ""



if \_\_name\_\_ == '\_\_main\_\_':
   app.run()

```



This gives us:

\- ✅ Clean decorator-based API

\- ✅ Global state management

\- ✅ Template-based layouts

\- ✅ Custom Jinja tags

\- ✅ Focus management

\- ✅ Event handling

\- ✅ View navigation



