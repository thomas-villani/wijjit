#!/usr/bin/env python3
"""CodeEditor demo - Syntax highlighting text editor.

This demo showcases the CodeEditor element with:
- Syntax highlighting for multiple languages
- Multiple color themes
- Line numbers
- Language detection
- All TextArea features (selection, clipboard, etc.)

Controls:
- Tab/Shift+Tab: Navigate between elements
- Arrow keys: Move cursor in editor
- Ctrl+A: Select all
- Ctrl+C/X/V: Copy/Cut/Paste
- Shift+Arrow: Extend selection
- Mouse: Click to position cursor, drag to select
- Scroll wheel: Scroll content
"""

from wijjit import Wijjit, render_template_string

app = Wijjit()

# Sample code in different languages
PYTHON_CODE = '''def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Parameters
    ----------
    n : int
        The position in the sequence

    Returns
    -------
    int
        The nth Fibonacci number
    """
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.result = 0

    def add(self, x: int, y: int) -> int:
        """Add two numbers."""
        self.result = x + y
        return self.result


if __name__ == "__main__":
    print(f"Fib(10) = {fibonacci(10)}")
    calc = Calculator()
    print(f"2 + 3 = {calc.add(2, 3)}")
'''

JAVASCRIPT_CODE = """// Async function example
async function fetchUsers() {
    const response = await fetch('/api/users');
    const data = await response.json();
    return data.map(user => ({
        id: user.id,
        name: user.name,
        email: user.email
    }));
}

// Class with arrow functions
class EventEmitter {
    constructor() {
        this.listeners = new Map();
    }

    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, []);
        }
        this.listeners.get(event).push(callback);
    }

    emit(event, ...args) {
        const callbacks = this.listeners.get(event);
        if (callbacks) {
            callbacks.forEach(cb => cb(...args));
        }
    }
}

// Usage
const emitter = new EventEmitter();
emitter.on('message', (msg) => console.log(msg));
emitter.emit('message', 'Hello, World!');
"""

RUST_CODE = """use std::collections::HashMap;

/// A simple key-value store
pub struct Store<K, V> {
    data: HashMap<K, V>,
}

impl<K: Eq + std::hash::Hash, V> Store<K, V> {
    /// Create a new empty store
    pub fn new() -> Self {
        Store {
            data: HashMap::new(),
        }
    }

    /// Insert a key-value pair
    pub fn insert(&mut self, key: K, value: V) -> Option<V> {
        self.data.insert(key, value)
    }

    /// Get a value by key
    pub fn get(&self, key: &K) -> Option<&V> {
        self.data.get(key)
    }
}

fn main() {
    let mut store: Store<String, i32> = Store::new();
    store.insert("one".to_string(), 1);
    store.insert("two".to_string(), 2);

    if let Some(value) = store.get(&"one".to_string()) {
        println!("Found: {}", value);
    }
}
"""


@app.view("main", default=True)
def main_view():
    """Main view with code editor demo."""
    # Initialize state
    if "language" not in app.state:
        app.state["language"] = "python"
        app.state["theme"] = "monokai"
        app.state["editor"] = PYTHON_CODE

    return render_template_string(
        """
{% frame border="rounded" title="CodeEditor Demo - Syntax Highlighting" width=90 height=35 %}
  {% vstack spacing=1 %}
    {% hstack spacing=2 %}
      Language:
      {% button action="lang_python" %}Python{% endbutton %}
      {% button action="lang_js" %}JavaScript{% endbutton %}
      {% button action="lang_rust" %}Rust{% endbutton %}
      Theme:
      {% button action="theme_monokai" %}Monokai{% endbutton %}
      {% button action="theme_dracula" %}Dracula{% endbutton %}
      {% button action="theme_nord" %}Nord{% endbutton %}
      {% button action="theme_github" %}GitHub{% endbutton %}
    {% endhstack %}

    {% codeeditor id="editor" language=state.language theme=state.theme
                  width=86 height=15 show_line_numbers=True %}
    {% endcodeeditor %}

    {% hstack spacing=2 %}
      Language: {{ state.language }} | Theme: {{ state.theme }}
      | Press Ctrl+Q to quit
    {% endhstack %}
  {% endvstack %}
{% endframe %}
""",
        state=app.state,
    )


@app.on_action("lang_python")
def set_python(event):
    """Switch to Python."""
    app.state["language"] = "python"
    app.state["editor"] = PYTHON_CODE


@app.on_action("lang_js")
def set_javascript(event):
    """Switch to JavaScript."""
    app.state["language"] = "javascript"
    app.state["editor"] = JAVASCRIPT_CODE


@app.on_action("lang_rust")
def set_rust(event):
    """Switch to Rust."""
    app.state["language"] = "rust"
    app.state["editor"] = RUST_CODE


@app.on_action("theme_monokai")
def set_monokai(event):
    """Switch to Monokai theme."""
    app.state["theme"] = "monokai"


@app.on_action("theme_dracula")
def set_dracula(event):
    """Switch to Dracula theme."""
    app.state["theme"] = "dracula"


@app.on_action("theme_nord")
def set_nord(event):
    """Switch to Nord theme."""
    app.state["theme"] = "nord"


@app.on_action("theme_github")
def set_github(event):
    """Switch to GitHub Light theme."""
    app.state["theme"] = "github-light"


if __name__ == "__main__":
    app.run()
