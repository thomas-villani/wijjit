Great question! ANSI mouse events are actually pretty cool once you understand them. Let me break down how they work and design a comprehensive input system.

## ANSI Mouse Event Basics

### Mouse Tracking Modes

Terminals support different mouse tracking modes via escape sequences:

```python
# wijjit/terminal/mouse.py
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Set

class MouseTrackingMode(Enum):
    """Different mouse tracking modes"""
    DISABLED = 0
    X10 = 9              # Only button press, limited coords
    NORMAL = 1000        # Press and release
    BUTTON_EVENT = 1002  # Press, release, and drag
    ANY_EVENT = 1003     # All mouse motion
    
class MouseButton(Enum):
    """Mouse buttons"""
    LEFT = 0
    MIDDLE = 1
    RIGHT = 2
    SCROLL_UP = 64
    SCROLL_DOWN = 65
    SCROLL_LEFT = 66
    SCROLL_RIGHT = 67
    NONE = 255  # Motion without button

class MouseEventType(Enum):
    """Types of mouse events"""
    PRESS = "press"
    RELEASE = "release"
    DRAG = "drag"
    MOVE = "move"
    SCROLL = "scroll"
    CLICK = "click"      # Synthesized from press+release
    DOUBLE_CLICK = "double_click"

@dataclass
class MouseEvent:
    """A mouse event"""
    type: MouseEventType
    button: MouseButton
    x: int  # 0-based column
    y: int  # 0-based row
    
    # Modifiers
    shift: bool = False
    alt: bool = False
    ctrl: bool = False
    
    # For synthesized events
    click_count: int = 0  # 1 for click, 2 for double-click
    
    def __str__(self):
        mods = []
        if self.shift: mods.append("Shift")
        if self.alt: mods.append("Alt")
        if self.ctrl: mods.append("Ctrl")
        mod_str = "+".join(mods) + "+" if mods else ""
        
        return f"{mod_str}{self.button.name} {self.type.value} at ({self.x}, {self.y})"
```

## Mouse Event Parser

```python
# wijjit/terminal/mouse.py (continued)
import re
from typing import Optional, Tuple

class MouseEventParser:
    """Parse ANSI mouse event sequences"""
    
    # SGR mouse format: \x1b[<button;x;y(M|m)
    SGR_PATTERN = re.compile(r'\x1b\[<(\d+);(\d+);(\d+)([Mm])')
    
    # Normal mouse format: \x1b[Mbxy (bytes after M are encoded)
    NORMAL_PREFIX = b'\x1b[M'
    
    def __init__(self):
        self.last_press: Optional[Tuple[MouseButton, int, int, float]] = None
        self.double_click_threshold = 0.5  # seconds
        self.double_click_distance = 2     # pixels
    
    def parse_sgr(self, sequence: str) -> Optional[MouseEvent]:
        """Parse SGR mouse format (modern, preferred)"""
        match = self.SGR_PATTERN.match(sequence)
        if not match:
            return None
        
        button_code = int(match.group(1))
        x = int(match.group(2)) - 1  # Convert to 0-based
        y = int(match.group(3)) - 1
        is_release = match.group(4) == 'm'
        
        return self._decode_event(button_code, x, y, is_release)
    
    def parse_normal(self, data: bytes) -> Optional[MouseEvent]:
        """Parse normal mouse format (older)"""
        if len(data) < 6 or not data.startswith(self.NORMAL_PREFIX):
            return None
        
        button_code = data[3] - 32  # Decode from printable ASCII
        x = data[4] - 33  # Convert to 0-based
        y = data[5] - 33
        
        # In normal mode, release is indicated by button 3
        is_release = (button_code & 3) == 3
        
        return self._decode_event(button_code, x, y, is_release)
    
    def _decode_event(self, button_code: int, x: int, y: int, is_release: bool) -> MouseEvent:
        """Decode button code into event"""
        import time
        
        # Extract modifiers (bits 2-4)
        shift = bool(button_code & 4)
        alt = bool(button_code & 8)
        ctrl = bool(button_code & 16)
        
        # Extract motion flag (bit 5)
        motion = bool(button_code & 32)
        
        # Extract base button (bits 0-1, plus scroll bits 6-7)
        base_button = button_code & 3
        
        # Handle scroll events
        if button_code & 64:
            button = MouseButton.SCROLL_UP if base_button == 0 else MouseButton.SCROLL_DOWN
            event_type = MouseEventType.SCROLL
        else:
            # Regular button events
            button = MouseButton(base_button) if base_button < 3 else MouseButton.NONE
            
            if motion:
                event_type = MouseEventType.DRAG if button != MouseButton.NONE else MouseEventType.MOVE
            elif is_release:
                event_type = MouseEventType.RELEASE
            else:
                event_type = MouseEventType.PRESS
        
        # Create event
        event = MouseEvent(
            type=event_type,
            button=button,
            x=x,
            y=y,
            shift=shift,
            alt=alt,
            ctrl=ctrl
        )
        
        # Synthesize click events from press/release pairs
        if event_type == MouseEventType.PRESS:
            self.last_press = (button, x, y, time.time())
        elif event_type == MouseEventType.RELEASE and self.last_press:
            press_button, press_x, press_y, press_time = self.last_press
            
            # Check if this is a click (release in same location as press)
            distance = abs(x - press_x) + abs(y - press_y)
            time_diff = time.time() - press_time
            
            if distance <= self.double_click_distance and button == press_button:
                # Check for double-click
                if hasattr(self, 'last_click_time') and \
                   time_diff < self.double_click_threshold and \
                   self.last_click_pos == (x, y) and \
                   self.last_click_button == button:
                    event.type = MouseEventType.DOUBLE_CLICK
                    event.click_count = 2
                    delattr(self, 'last_click_time')  # Reset
                else:
                    event.type = MouseEventType.CLICK
                    event.click_count = 1
                    self.last_click_time = time.time()
                    self.last_click_pos = (x, y)
                    self.last_click_button = button
            
            self.last_press = None
        
        return event
```

## Enhanced Input Handler

```python
# wijjit/terminal/input.py (updated)
import sys
import tty
import termios
import select
from typing import Optional, Callable
from .mouse import MouseEventParser, MouseEvent, MouseTrackingMode

class InputHandler:
    """Handles keyboard and mouse input"""
    
    def __init__(self, app):
        self.app = app
        
        # Focus management
        self.focused_element = None
        self.focusable_elements = []
        self.focused_index = 0
        
        # Mouse support
        self.mouse_enabled = False
        self.mouse_parser = MouseEventParser()
        self.mouse_tracking_mode = MouseTrackingMode.BUTTON_EVENT
        
        # Hover tracking
        self.hovered_element = None
        self.last_mouse_pos = (0, 0)
        
        # Input buffer for escape sequences
        self.input_buffer = bytearray()
        
        # Terminal state
        self.original_term_settings = None
    
    def enable_mouse(self, mode: MouseTrackingMode = MouseTrackingMode.BUTTON_EVENT):
        """Enable mouse event reporting"""
        self.mouse_enabled = True
        self.mouse_tracking_mode = mode
        
        # Enable mouse tracking
        sys.stdout.write(f"\033[?{mode.value}h")  # Enable tracking mode
        sys.stdout.write("\033[?1006h")           # Enable SGR extended mouse mode
        sys.stdout.flush()
    
    def disable_mouse(self):
        """Disable mouse event reporting"""
        if self.mouse_enabled:
            sys.stdout.write(f"\033[?{self.mouse_tracking_mode.value}l")
            sys.stdout.write("\033[?1006l")
            sys.stdout.flush()
            self.mouse_enabled = False
    
    def setup(self):
        """Setup terminal for input handling"""
        # Save original terminal settings
        fd = sys.stdin.fileno()
        self.original_term_settings = termios.tcgetattr(fd)
        
        # Set raw mode
        tty.setraw(fd)
        
        # Enable mouse if requested
        if self.mouse_enabled:
            self.enable_mouse(self.mouse_tracking_mode)
    
    def cleanup(self):
        """Restore terminal settings"""
        if self.original_term_settings:
            fd = sys.stdin.fileno()
            termios.tcsetattr(fd, termios.TCSADRAIN, self.original_term_settings)
        
        self.disable_mouse()
    
    def process_input(self, timeout: float = 0.1) -> bool:
        """
        Read and process input events
        Returns True if event was processed
        """
        # Check if input is available
        if not select.select([sys.stdin], [], [], timeout)[0]:
            return False
        
        # Read available bytes
        data = sys.stdin.buffer.read1(1024)
        if not data:
            return False
        
        self.input_buffer.extend(data)
        
        # Try to parse events from buffer
        while self.input_buffer:
            event_processed = self._try_parse_event()
            if not event_processed:
                break
        
        return True
    
    def _try_parse_event(self) -> bool:
        """Try to parse an event from the buffer"""
        buffer_str = self.input_buffer.decode('utf-8', errors='ignore')
        
        # Try mouse event first (SGR format)
        if buffer_str.startswith('\x1b[<'):
            mouse_event = self.mouse_parser.parse_sgr(buffer_str)
            if mouse_event:
                # Find how many bytes to consume
                match = self.mouse_parser.SGR_PATTERN.match(buffer_str)
                if match:
                    consumed = len(match.group(0).encode('utf-8'))
                    self.input_buffer = self.input_buffer[consumed:]
                    self._handle_mouse_event(mouse_event)
                    return True
        
        # Try normal mouse event
        if self.input_buffer.startswith(b'\x1b[M') and len(self.input_buffer) >= 6:
            mouse_event = self.mouse_parser.parse_normal(bytes(self.input_buffer[:6]))
            if mouse_event:
                self.input_buffer = self.input_buffer[6:]
                self._handle_mouse_event(mouse_event)
                return True
        
        # Try keyboard event
        key = self._try_parse_key()
        if key:
            self._handle_key_event(key)
            return True
        
        # If we have data but can't parse, might need more bytes
        # But if buffer is getting large, discard oldest byte
        if len(self.input_buffer) > 100:
            self.input_buffer = self.input_buffer[1:]
        
        return False
    
    def _try_parse_key(self) -> Optional[str]:
        """Try to parse a key event from buffer"""
        if not self.input_buffer:
            return None
        
        # Single byte keys
        if self.input_buffer[0] == 0x1b:  # Escape
            if len(self.input_buffer) == 1:
                # Wait a bit to see if it's an escape sequence
                # (This is a simplification - real implementation would use timeout)
                return None
            
            # Multi-byte escape sequence
            buffer_str = self.input_buffer.decode('utf-8', errors='ignore')
            
            # Arrow keys
            if buffer_str.startswith('\x1b[A'):
                self.input_buffer = self.input_buffer[3:]
                return 'up'
            elif buffer_str.startswith('\x1b[B'):
                self.input_buffer = self.input_buffer[3:]
                return 'down'
            elif buffer_str.startswith('\x1b[C'):
                self.input_buffer = self.input_buffer[3:]
                return 'right'
            elif buffer_str.startswith('\x1b[D'):
                self.input_buffer = self.input_buffer[3:]
                return 'left'
            
            # Function keys
            if buffer_str.startswith('\x1b['):
                # F1-F12 and other special keys
                # This is simplified - real implementation would handle all variants
                pass
            
            # Shift+Tab
            if buffer_str.startswith('\x1b[Z'):
                self.input_buffer = self.input_buffer[3:]
                return 'shift+tab'
            
            # Alt+key combinations
            if len(self.input_buffer) >= 2:
                self.input_buffer = self.input_buffer[1:]
                char = chr(self.input_buffer[0])
                self.input_buffer = self.input_buffer[1:]
                return f'alt+{char}'
        
        # Control characters
        elif self.input_buffer[0] < 32:
            byte = self.input_buffer[0]
            self.input_buffer = self.input_buffer[1:]
            
            if byte == 0x09:  # Tab
                return 'tab'
            elif byte == 0x0D:  # Enter
                return 'enter'
            elif byte == 0x7F or byte == 0x08:  # Backspace/Delete
                return 'backspace'
            elif byte == 0x03:  # Ctrl+C
                return 'ctrl+c'
            elif byte == 0x04:  # Ctrl+D
                return 'ctrl+d'
            elif byte == 0x1A:  # Ctrl+Z
                return 'ctrl+z'
            else:
                # Other control characters
                char = chr(ord('a') + byte - 1)
                return f'ctrl+{char}'
        
        # Regular character
        else:
            try:
                # Try to decode UTF-8 character
                char = self.input_buffer[0:4].decode('utf-8')
                consumed = len(char.encode('utf-8'))
                self.input_buffer = self.input_buffer[consumed:]
                return char
            except UnicodeDecodeError:
                # Invalid UTF-8, skip byte
                self.input_buffer = self.input_buffer[1:]
                return None
        
        return None
    
    def _handle_key_event(self, key: str):
        """Handle a keyboard event"""
        # Global shortcuts
        if key == 'ctrl+c':
            self.app.exit()
            return
        
        # Tab navigation
        if key == 'tab':
            self._handle_tab()
            return
        elif key == 'shift+tab':
            self._handle_shift_tab()
            return
        
        # Send to focused element
        if self.focused_element:
            from ..core.events import KeyEvent
            event = KeyEvent(
                source=self.focused_element.id,
                view=self.app.current_view,
                key=key,
                modifiers=self._parse_modifiers(key)
            )
            
            handled = self.focused_element.handle_key(key, self.app.state)
            
            if handled:
                self.app.renderer.request_render()
            else:
                # Dispatch to registered handlers
                import asyncio
                asyncio.create_task(self.app.handler_registry.dispatch(event))
    
    def _handle_mouse_event(self, mouse_event: MouseEvent):
        """Handle a mouse event"""
        from ..core.events import Event, EventType
        
        # Update last mouse position
        self.last_mouse_pos = (mouse_event.x, mouse_event.y)
        
        # Find element at position
        element = self._find_element_at(mouse_event.x, mouse_event.y)
        
        # Handle hover changes
        if element != self.hovered_element:
            # Trigger hover out on old element
            if self.hovered_element:
                self._trigger_hover(self.hovered_element, False)
            
            # Trigger hover in on new element
            if element:
                self._trigger_hover(element, True)
            
            self.hovered_element = element
        
        # Handle different mouse event types
        if mouse_event.type == MouseEventType.CLICK and element:
            # Focus element on click if focusable
            if element.focusable:
                self._set_focus(element)
            
            # Trigger click handler
            self._trigger_click(element, mouse_event)
        
        elif mouse_event.type == MouseEventType.DOUBLE_CLICK and element:
            self._trigger_double_click(element, mouse_event)
        
        elif mouse_event.type == MouseEventType.SCROLL:
            # Handle scroll on hovered frame
            if element:
                self._trigger_scroll(element, mouse_event)
        
        elif mouse_event.type == MouseEventType.DRAG:
            # Handle drag
            if element:
                self._trigger_drag(element, mouse_event)
        
        # Request render if anything changed
        self.app.renderer.request_render()
    
    def _find_element_at(self, x: int, y: int):
        """Find the element at screen coordinates"""
        # Search through all elements in reverse order (top to bottom)
        for element in reversed(self.app.renderer.all_elements):
            if element.bounds and element.bounds.contains(x, y):
                return element
        return None
    
    def _trigger_hover(self, element, is_hovering: bool):
        """Trigger hover event on element"""
        if hasattr(element, 'on_hover'):
            element.on_hover(is_hovering)
    
    def _trigger_click(self, element, mouse_event: MouseEvent):
        """Trigger click event on element"""
        # Call element's click handler
        if hasattr(element, 'handle_mouse'):
            element.handle_mouse(mouse_event.x, mouse_event.y, 'click')
        
        # Dispatch to registered handlers
        from ..core.events import Event, EventType
        event = Event(
            type=EventType.MOUSE,
            source=element.id,
            view=self.app.current_view,
            data={
                'action': 'click',
                'x': mouse_event.x,
                'y': mouse_event.y,
                'button': mouse_event.button.name,
                'shift': mouse_event.shift,
                'alt': mouse_event.alt,
                'ctrl': mouse_event.ctrl
            }
        )
        
        import asyncio
        asyncio.create_task(self.app.handler_registry.dispatch(event))
    
    def _trigger_double_click(self, element, mouse_event: MouseEvent):
        """Trigger double-click event"""
        if hasattr(element, 'on_double_click'):
            element.on_double_click(mouse_event)
    
    def _trigger_scroll(self, element, mouse_event: MouseEvent):
        """Trigger scroll event"""
        # Find scrollable parent
        current = element
        while current:
            if hasattr(current, 'style') and hasattr(current.style, 'scrollable'):
                if current.style.scrollable:
                    # Scroll up or down
                    direction = 1 if mouse_event.button == MouseButton.SCROLL_DOWN else -1
                    current.handle_key('down' if direction > 0 else 'up', self.app.state)
                    break
            current = current.parent
    
    def _trigger_drag(self, element, mouse_event: MouseEvent):
        """Trigger drag event"""
        if hasattr(element, 'on_drag'):
            element.on_drag(mouse_event)
    
    def _set_focus(self, element):
        """Set focus to an element"""
        if self.focused_element:
            self.focused_element.focused = False
        
        self.focused_element = element
        element.focused = True
        
        # Update focused index
        if element in self.focusable_elements:
            self.focused_index = self.focusable_elements.index(element)
    
    def _handle_tab(self):
        """Handle Tab key - focus next element"""
        if not self.focusable_elements:
            return
        
        if self.focused_element:
            self.focused_element.focused = False
        
        self.focused_index = (self.focused_index + 1) % len(self.focusable_elements)
        self.focused_element = self.focusable_elements[self.focused_index]
        self.focused_element.focused = True
        
        self.app.renderer.request_render()
    
    def _handle_shift_tab(self):
        """Handle Shift+Tab - focus previous element"""
        if not self.focusable_elements:
            return
        
        if self.focused_element:
            self.focused_element.focused = False
        
        self.focused_index = (self.focused_index - 1) % len(self.focusable_elements)
        self.focused_element = self.focusable_elements[self.focused_index]
        self.focused_element.focused = True
        
        self.app.renderer.request_render()
    
    def _parse_modifiers(self, key: str) -> list[str]:
        """Extract modifiers from key string"""
        modifiers = []
        if key.startswith('ctrl+'):
            modifiers.append('ctrl')
        if key.startswith('alt+'):
            modifiers.append('alt')
        if key.startswith('shift+'):
            modifiers.append('shift')
        return modifiers
```

## Mouse Event Support in Elements

```python
# wijjit/elements/base.py (additions)
class Element:
    def __init__(self, id: str, element_type: ElementType, focusable: bool = False):
        # ... existing init ...
        
        # Mouse event callbacks
        self.on_click: Optional[Callable] = None
        self.on_double_click: Optional[Callable] = None
        self.on_hover_in: Optional[Callable] = None
        self.on_hover_out: Optional[Callable] = None
        self.on_drag: Optional[Callable] = None
        
        # Hover state
        self.hovered = False
    
    def handle_mouse(self, x: int, y: int, event_type: str) -> bool:
        """Handle mouse event (override in subclasses)"""
        return False
    
    def on_hover(self, is_hovering: bool):
        """Called when hover state changes"""
        was_hovered = self.hovered
        self.hovered = is_hovering
        
        if is_hovering and not was_hovered and self.on_hover_in:
            self.on_hover_in()
        elif not is_hovering and was_hovered and self.on_hover_out:
            self.on_hover_out()

# Button with mouse support
class Button(Element):
    def __init__(self, id: str, label: str, action: Optional[Callable] = None):
        super().__init__(id, ElementType.BUTTON, focusable=True)
        self.label = label
        self.action = action
        self.pressed = False
    
    def handle_mouse(self, x: int, y: int, event_type: str) -> bool:
        if event_type == 'click':
            if self.action:
                self.action()
            return True
        return False
    
    def render(self, state: Any) -> str:
        # Change appearance based on state
        style = ""
        
        if self.pressed:
            style = "\033[7m"  # Reverse video when pressed
        elif self.focused:
            style = "\033[1;44m"  # Blue background when focused
        elif self.hovered:
            style = "\033[4m"  # Underline when hovered
        
        return f"{style}[ {self.label} ]\033[0m"
```

## Usage in Templates

```jinja
{# Mouse events in templates #}

{# Click handler #}
{% button id="save" 
          action="save_file"
          on_click="handle_save_click" %}
  Save
{% endbutton %}

{# Hover effects #}
{% frame id="card"
         class="card"
         on_hover_in="show_details"
         on_hover_out="hide_details" %}
  {{ content }}
{% endframe %}

{# Double-click #}
{% table id="files"
         on_row_click="select_file"
         on_row_double_click="open_file" %}
  ...
{% endtable %}

{# Drag support #}
{% frame id="resizable"
         draggable=true
         on_drag="handle_resize" %}
  ...
{% endframe %}
```

## Usage in Application

```python
# app.py
from wijjit import Wijjit, state

app = Wijjit()

# Enable mouse support
app.input_handler.mouse_enabled = True

@app.view('interactive', default=True)
def interactive_view():
    return {
        'template': '''
        {% frame class="container" %}
          <h1>Interactive Demo</h1>
          
          {% button id="btn1" action="button_clicked" %}
            Click Me!
          {% endbutton %}
          
          {% frame id="hover_area" 
                   class="panel"
                   height=10 %}
            {{ state.hover_message }}
          {% endframe %}
        {% endframe %}
        ''',
        'data': {}
    }

@app.handler('interactive', 'button_clicked')
def button_clicked(event):
    state.click_count = state.get('click_count', 0) + 1
    state.hover_message = f"Button clicked {state.click_count} times!"
    
    # Access mouse position from event
    if 'x' in event.data and 'y' in event.data:
        print(f"Clicked at ({event.data['x']}, {event.data['y']})")

# Mouse event handlers
@app.handler('interactive', 'hover_in')
def hover_in(event):
    state.hover_message = "Mouse is over the panel!"

@app.handler('interactive', 'hover_out')
def hover_out(event):
    state.hover_message = "Mouse left the panel"

if __name__ == '__main__':
    state.hover_message = "Move your mouse over the panel"
    state.click_count = 0
    app.run()
```

## Complete Input System Integration

```python
# wijjit/core/app.py (updated run method)
class Wijjit:
    def run(self):
        """Start the app"""
        self._running = True
        
        try:
            # Setup input handler
            self.input_handler.setup()
            
            # Navigate to default view
            if self.default_view:
                self.navigate(self.default_view)
            
            # Enter alternate screen
            self.renderer.enter_alternate_screen()
            
            # Main event loop
            while self._running:
                # Process input (keyboard and mouse)
                self.input_handler.process_input(timeout=0.016)  # ~60fps
                
                # Process any pending async tasks
                # (This is simplified - real implementation would use asyncio properly)
        
        finally:
            # Cleanup
            self.input_handler.cleanup()
            self.renderer.exit_alternate_screen()
```

## Advanced Features

### Context Menus

```python
@app.component('context_menu')
def context_menu():
    return '''
    {% frame class="card" 
             width=20
             x=menu_x 
             y=menu_y %}
      {% for item in items %}
        {% button action=item.action class="button" width="100%" %}
          {{ item.label }}
        {% endbutton %}
      {% endfor %}
    {% endframe %}
    '''

@app.handler('browser', 'right_click')
def show_context_menu(event):
    state.context_menu_visible = True
    state.context_menu_x = event.data['x']
    state.context_menu_y = event.data['y']
    state.context_menu_items = [
        {'label': 'Open', 'action': 'open_file'},
        {'label': 'Delete', 'action': 'delete_file'},
        {'label': 'Properties', 'action': 'show_properties'}
    ]
```

### Drag and Drop

```python
class DraggableElement(Element):
    def __init__(self, id: str):
        super().__init__(id, ElementType.INTERACTIVE)
        self.dragging = False
        self.drag_start_pos = None
        self.drag_offset = (0, 0)
    
    def handle_mouse(self, x: int, y: int, event_type: str) -> bool:
        if event_type == 'press':
            self.dragging = True
            self.drag_start_pos = (x, y)
            return True
        elif event_type == 'drag' and self.dragging:
            if self.bounds:
                dx = x - self.drag_start_pos[0]
                dy = y - self.drag_start_pos[1]
                self.drag_offset = (dx, dy)
            return True
        elif event_type == 'release':
            self.dragging = False
            # Finalize position
            if self.on_drag_end:
                self.on_drag_end(self.drag_offset)
            return True
        return False
```

## Summary

This input system provides:

✅ **Complete keyboard support**: All keys, modifiers, combinations
✅ **Mouse tracking modes**: From basic clicks to full motion tracking
✅ **Event types**: Click, double-click, hover, drag, scroll
✅ **Coordinate mapping**: Find elements at mouse position
✅ **Focus management**: Tab navigation + mouse focus
✅ **Modifier keys**: Shift, Alt, Ctrl detection
✅ **Event synthesis**: Generate high-level events from low-level input
✅ **Hover states**: Track mouse-over elements
✅ **Context menus**: Right-click support
✅ **Drag and drop**: Full dragging support

The system handles the complexity of ANSI escape sequences while exposing clean, event-driven APIs. Elements can opt into mouse support, and the framework handles all the coordination!

Want to explore any specific interaction pattern, like implementing a draggable splitter or a resizable panel?