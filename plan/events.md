Great question! Event handling is crucial to get right. Let's design a flexible system that supports multiple patterns while staying intuitive.

## Event Handler Architecture

### Multiple Registration Patterns

```python
# Pattern 1: Decorator-based (most Flask-like)
@app.view('editor', default=True)
def editor_view():
    return {...}

@app.handler('editor', 'save_file')
def save_file(event):
    """Handler scoped to editor view"""
    state.save(state.current_file, state.editor_buffer)
    app.show_notification("File saved!")

@app.handler('editor', 'close_file')
def close_file(event):
    if state.unsaved_changes:
        app.navigate('confirm_close')
    else:
        app.navigate('browser')

# Pattern 2: Inline in view config (concise for simple handlers)
@app.view('browser')
def browser_view():
    return {
        'template': 'browser.tui',
        'data': {'files': state.files},
        'handlers': {
            'open': lambda e: open_file(e.data['file']),
            'delete': lambda e: app.navigate('confirm_delete', file=e.data['file'])
        }
    }

# Pattern 3: Class-based views (for complex views)
@app.view('editor')
class EditorView:
    def render(self):
        return {
            'template': 'editor.tui',
            'data': {'content': state.editor_buffer}
        }
    
    def on_save(self, event):
        state.save(state.current_file, state.editor_buffer)
    
    def on_close(self, event):
        if state.unsaved_changes:
            app.navigate('confirm_close')

# Pattern 4: Dynamic registration (for plugins/extensions)
def setup_git_integration(app):
    """Plugin can register handlers dynamically"""
    app.register_handler('editor', 'git_commit', handle_commit)
    app.register_handler('editor', 'git_push', handle_push)
```

## Event Object

```python
# wijjit/core/events.py
from dataclasses import dataclass
from typing import Any, Dict, Optional
from enum import Enum

class EventType(Enum):
    KEY = "key"           # Keyboard input
    MOUSE = "mouse"       # Mouse click/drag
    ACTION = "action"     # Button click, menu select
    CHANGE = "change"     # Input value changed
    FOCUS = "focus"       # Element gained focus
    BLUR = "blur"         # Element lost focus
    SUBMIT = "submit"     # Form submission
    NAVIGATE = "navigate" # View navigation
    CUSTOM = "custom"     # User-defined events

@dataclass
class Event:
    """Base event object passed to handlers"""
    type: EventType
    source: str           # Element ID that triggered event
    view: str            # Current view name
    data: Dict[str, Any] # Event-specific data
    handled: bool = False
    
    # Convenience accessors
    @property
    def value(self):
        """For input change events"""
        return self.data.get('value')
    
    @property
    def key(self):
        """For key events"""
        return self.data.get('key')
    
    @property
    def position(self):
        """For mouse events"""
        return self.data.get('x'), self.data.get('y')
    
    def stop_propagation(self):
        """Prevent further handlers from running"""
        self.handled = True

# Specific event types
@dataclass
class KeyEvent(Event):
    key: str
    modifiers: list[str]  # ['ctrl', 'shift', 'alt']
    
    def __init__(self, source: str, view: str, key: str, modifiers=None):
        super().__init__(
            type=EventType.KEY,
            source=source,
            view=view,
            data={'key': key, 'modifiers': modifiers or []}
        )
        self.key = key
        self.modifiers = modifiers or []

@dataclass
class ActionEvent(Event):
    action: str
    element_data: Any = None
    
    def __init__(self, source: str, view: str, action: str, **kwargs):
        super().__init__(
            type=EventType.ACTION,
            source=source,
            view=view,
            data={'action': action, **kwargs}
        )
        self.action = action
        self.element_data = kwargs

@dataclass
class ChangeEvent(Event):
    value: Any
    old_value: Any = None
    
    def __init__(self, source: str, view: str, value: Any, old_value=None):
        super().__init__(
            type=EventType.CHANGE,
            source=source,
            view=view,
            data={'value': value, 'old_value': old_value}
        )
        self.value = value
        self.old_value = old_value
```

## Event Handler System

```python
# wijjit/core/handlers.py
from typing import Callable, Dict, List, Optional
from .events import Event, EventType

class HandlerRegistry:
    """Manages event handlers across views"""
    
    def __init__(self):
        # view_name -> action_name -> [handlers]
        self._view_handlers: Dict[str, Dict[str, List[Callable]]] = {}
        
        # Global handlers (work in any view)
        self._global_handlers: Dict[str, List[Callable]] = {}
        
        # Middleware that runs before handlers
        self._middleware: List[Callable] = []
    
    def register(self, 
                 action: str, 
                 handler: Callable,
                 view: Optional[str] = None,
                 priority: int = 0):
        """Register a handler for an action"""
        if view:
            # View-specific handler
            if view not in self._view_handlers:
                self._view_handlers[view] = {}
            if action not in self._view_handlers[view]:
                self._view_handlers[view][action] = []
            
            self._view_handlers[view][action].append((priority, handler))
            self._view_handlers[view][action].sort(key=lambda x: -x[0])  # Higher priority first
        else:
            # Global handler
            if action not in self._global_handlers:
                self._global_handlers[action] = []
            
            self._global_handlers[action].append((priority, handler))
            self._global_handlers[action].sort(key=lambda x: -x[0])
    
    def unregister(self, action: str, handler: Callable, view: Optional[str] = None):
        """Unregister a handler"""
        if view and view in self._view_handlers:
            if action in self._view_handlers[view]:
                self._view_handlers[view][action] = [
                    (p, h) for p, h in self._view_handlers[view][action] if h != handler
                ]
        elif action in self._global_handlers:
            self._global_handlers[action] = [
                (p, h) for p, h in self._global_handlers[action] if h != handler
            ]
    
    def get_handlers(self, action: str, view: str) -> List[Callable]:
        """Get all handlers for an action in priority order"""
        handlers = []
        
        # Add view-specific handlers
        if view in self._view_handlers and action in self._view_handlers[view]:
            handlers.extend([h for _, h in self._view_handlers[view][action]])
        
        # Add global handlers
        if action in self._global_handlers:
            handlers.extend([h for _, h in self._global_handlers[action]])
        
        return handlers
    
    def add_middleware(self, middleware: Callable):
        """Add middleware that runs before all handlers"""
        self._middleware.append(middleware)
    
    async def dispatch(self, event: Event) -> bool:
        """Dispatch an event to registered handlers"""
        # Run middleware first
        for middleware in self._middleware:
            if await self._call_handler(middleware, event):
                return True  # Middleware handled it
            if event.handled:
                return True
        
        # Get action from event
        action = event.data.get('action', event.source)
        
        # Get handlers
        handlers = self.get_handlers(action, event.view)
        
        # Call handlers in order
        for handler in handlers:
            if await self._call_handler(handler, event):
                return True
            if event.handled:
                return True  # Handler stopped propagation
        
        return False
    
    async def _call_handler(self, handler: Callable, event: Event) -> bool:
        """Call a handler (sync or async)"""
        import inspect
        
        try:
            if inspect.iscoroutinefunction(handler):
                result = await handler(event)
            else:
                result = handler(event)
            
            return result is True  # Handler can return True to stop propagation
        except Exception as e:
            # Log error and continue
            print(f"Error in handler {handler.__name__}: {e}")
            return False

class EventEmitter:
    """Emit events from elements"""
    
    def __init__(self, registry: HandlerRegistry, app):
        self.registry = registry
        self.app = app
    
    async def emit(self, 
                   action: str,
                   source: str,
                   event_type: EventType = EventType.ACTION,
                   **data):
        """Emit an event"""
        event = Event(
            type=event_type,
            source=source,
            view=self.app.current_view,
            data={'action': action, **data}
        )
        
        handled = await self.registry.dispatch(event)
        
        if not handled:
            # No handler found - log warning
            print(f"Warning: No handler for action '{action}' in view '{event.view}'")
        
        return handled
```

## Updated Wijjit App Class

```python
# wijjit/core/app.py (updated)
class Wijjit:
    def __init__(self, template_dir: str = 'templates'):
        # ... existing init ...
        
        # Event handling
        self.handler_registry = HandlerRegistry()
        self.events = EventEmitter(self.handler_registry, self)
    
    def handler(self, view: str, action: str, priority: int = 0):
        """Decorator to register a view-specific handler"""
        def decorator(func: Callable):
            self.handler_registry.register(action, func, view=view, priority=priority)
            return func
        return decorator
    
    def global_handler(self, action: str, priority: int = 0):
        """Decorator to register a global handler"""
        def decorator(func: Callable):
            self.handler_registry.register(action, func, view=None, priority=priority)
            return func
        return decorator
    
    def register_handler(self, action: str, handler: Callable, view: Optional[str] = None):
        """Manually register a handler"""
        self.handler_registry.register(action, handler, view=view)
    
    def unregister_handler(self, action: str, handler: Callable, view: Optional[str] = None):
        """Manually unregister a handler"""
        self.handler_registry.unregister(action, handler, view=view)
    
    def middleware(self, func: Callable):
        """Decorator to register middleware"""
        self.handler_registry.add_middleware(func)
        return func
    
    # Helper for common patterns
    def show_notification(self, message: str, duration: float = 2.0):
        """Show a temporary notification"""
        state.notification = message
        # Schedule removal after duration
        # (would need async timer support)
```

## Template Usage

```jinja
{# Connect template actions to handlers #}

{# Simple action #}
{% button action="save_file" %}Save{% endbutton %}

{# Action with data #}
{% button action="delete_file" data={"file_id": file.id} %}Delete{% endbutton %}

{# Multiple events on same element #}
{% textinput id="search" 
             on_change="filter_results"
             on_enter="execute_search"
             on_escape="clear_search" %}

{# Conditional actions #}
{% if can_edit %}
  {% button action="edit" %}Edit{% endbutton %}
{% endif %}

{# Dynamic actions #}
{% for item in items %}
  {% button action="select_item" data={"item_id": item.id} %}
    {{ item.name }}
  {% endbutton %}
{% endfor %}
```

## Full Example

```python
# file_manager.py
from wijjit import Wijjit, state
from pathlib import Path

app = Wijjit()

# Initialize state
state.current_dir = Path.cwd()
state.files = list(state.current_dir.iterdir())
state.selected = []
state.clipboard = []

# === Browser View ===

@app.view('browser', default=True)
def browser_view():
    return {
        'template': 'browser.tui',
        'data': {
            'path': state.current_dir,
            'files': state.files,
            'selected': state.selected,
        }
    }

# Handler approach 1: Decorator
@app.handler('browser', 'open_file')
def open_file(event):
    file = event.element_data['file']
    if file.is_dir():
        state.current_dir = file
        state.files = list(file.iterdir())
        state.selected = []
    else:
        # Open in viewer
        app.navigate('viewer', file=file)

@app.handler('browser', 'delete_files')
def delete_files(event):
    if state.selected:
        app.navigate('confirm_delete', files=state.selected)

@app.handler('browser', 'copy_files')
def copy_files(event):
    state.clipboard = state.selected.copy()
    app.show_notification(f"Copied {len(state.clipboard)} files")

@app.handler('browser', 'paste_files')
def paste_files(event):
    for file in state.clipboard:
        # Copy files to current directory
        shutil.copy(file, state.current_dir)
    state.files = list(state.current_dir.iterdir())
    app.show_notification(f"Pasted {len(state.clipboard)} files")

# === Viewer View ===

@app.view('viewer')
class ViewerView:
    """Class-based view for complex logic"""
    
    def render(self):
        file = app.view_params['file']
        content = file.read_text() if file.suffix in ['.txt', '.py', '.md'] else "[Binary file]"
        
        return {
            'template': 'viewer.tui',
            'data': {
                'filename': file.name,
                'content': content,
                'can_edit': file.suffix in ['.txt', '.py', '.md']
            }
        }
    
    def on_edit(self, event):
        """Handler method auto-registered"""
        file = app.view_params['file']
        app.navigate('editor', file=file)
    
    def on_close(self, event):
        app.navigate('browser')

# === Confirm Dialog ===

@app.view('confirm_delete')
def confirm_delete_view():
    files = app.view_params['files']
    return {
        'template': 'confirm.tui',
        'data': {
            'message': f"Delete {len(files)} files?",
            'files': [f.name for f in files]
        },
        'handlers': {
            # Inline handlers for simple logic
            'yes': lambda e: delete_confirmed(files),
            'no': lambda e: app.navigate('browser')
        }
    }

def delete_confirmed(files):
    for file in files:
        file.unlink()
    state.files = list(state.current_dir.iterdir())
    state.selected = []
    app.navigate('browser')
    app.show_notification(f"Deleted {len(files)} files")

# === Global Handlers ===

@app.global_handler('quit', priority=100)
def quit_app(event):
    """Global quit handler works in any view"""
    if state.unsaved_changes:
        app.navigate('confirm_quit')
    else:
        app.exit()
    return True  # Stop propagation

@app.global_handler('help')
def show_help(event):
    """Global help accessible from anywhere"""
    app.navigate('help')

# === Middleware ===

@app.middleware
def log_actions(event):
    """Log all actions for debugging"""
    print(f"[{event.view}] {event.type.value}: {event.data.get('action')}")
    # Return False to continue to handlers
    return False

@app.middleware
def check_permissions(event):
    """Check if user can perform action"""
    if event.data.get('action') in ['delete_files', 'edit']:
        if not state.user_permissions.get('can_edit'):
            app.show_notification("Permission denied")
            return True  # Stop event
    return False

# === Dynamic Registration (Plugin System) ===

def register_git_plugin(app):
    """Plugins can register handlers dynamically"""
    
    def git_status(event):
        # Run git status
        result = subprocess.run(['git', 'status'], capture_output=True)
        app.navigate('git_status', output=result.stdout.decode())
    
    def git_commit(event):
        app.navigate('git_commit')
    
    # Register handlers
    app.register_handler('git_status', git_status, view='browser')
    app.register_handler('git_commit', git_commit, view='browser')

# Load plugins
register_git_plugin(app)

if __name__ == '__main__':
    app.run()
```

## Advanced Patterns

### Event Chaining

```python
@app.handler('editor', 'save')
async def save_file(event):
    # Save file
    state.editor_buffer_save()
    
    # Emit another event
    await app.events.emit('file_saved', 
                         source='editor',
                         file=state.current_file)

@app.handler('editor', 'file_saved')
def on_file_saved(event):
    # Update UI after save
    app.show_notification("File saved")
    state.unsaved_changes = False
```

### Async Handlers

```python
@app.handler('browser', 'search_files')
async def search_files(event):
    query = event.value
    
    # Show loading indicator
    state.searching = True
    app.renderer.render()
    
    # Async file search
    results = await async_file_search(query)
    
    # Update results
    state.search_results = results
    state.searching = False
```

### Event Bubbling

```python
# Child element doesn't handle event, bubbles to parent
class TextInput(Element):
    def handle_key(self, key: str, state: Any) -> bool:
        if key == 'escape':
            # Don't handle - let parent handle it
            return False
        # Handle other keys
        return True

# Parent frame can handle bubbled events
@app.handler('form', 'escape')
def cancel_form(event):
    app.navigate('main')
```

## Summary

This event system provides:

✅ **Multiple patterns**: Decorators, inline handlers, class methods, dynamic registration
✅ **Scoping**: View-specific vs global handlers
✅ **Priority**: Control handler execution order
✅ **Middleware**: Cross-cutting concerns (logging, auth, etc.)
✅ **Event objects**: Rich context about what happened
✅ **Async support**: Long-running operations
✅ **Propagation control**: Stop event bubbling
✅ **Plugin-friendly**: Dynamic registration for extensions

Which pattern feels most natural for your use case? We can refine based on your preferences!