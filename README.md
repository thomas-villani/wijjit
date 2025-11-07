# Wijjit Project Plan


**Wijjit is just Jinja in Terminal**


*Flask for the Console: A declarative TUI framework for Python*


---


## Executive Summary


Wijjit is a new Python framework for building Terminal User Interfaces (TUIs) using familiar web development patterns. By combining Jinja2 templating with ANSI rendering, Wijjit enables developers to create rich, interactive console applications using declarative templates and a Flask-like API.


**Key Value Propositions:**

- **Familiar patterns**: Developers who know Flask and Jinja2 can immediately be productive

- **Declarative UI**: Define layouts in templates, not procedural positioning code

- **Component reusability**: Pre-built elements for common patterns (forms, tables, menus)

- **View-based architecture**: Navigate between screens like web routes

- **Fills a gap**: No existing Python TUI framework offers this level of abstraction


**Target Timeline:** 8-10 weeks to MVP

**Target Audience:** CLI tool developers, DevOps engineers, data scientists, systems administrators


---


## Getting Started

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/wijjit.git
cd wijjit

# Install in development mode
pip install -e .
```

### Your First Wijjit App

Here's a simple "Hello World" application:

```python
from wijjit import Wijjit

# Create the app
app = Wijjit()

# Define a view with the @app.view decorator
@app.view("main", default=True)
def main_view():
    return {
        "template": "Hello, World! Press Ctrl+C to exit.",
    }

# Run the app
if __name__ == "__main__":
    app.run()
```

### Interactive Todo List Example

For a more complete example with state management and event handling, see `examples/todo_app.py`:

```python
from wijjit import Wijjit, EventType, HandlerScope

# Initialize app with state
app = Wijjit(initial_state={
    "todos": [
        {"id": 1, "text": "Learn Wijjit", "done": False},
        {"id": 2, "text": "Build a TUI app", "done": False},
    ],
    "next_id": 3,
})

# Define the main view
@app.view("main", default=True)
def main_view():
    def render_data():
        todos = app.state["todos"]
        completed = sum(1 for todo in todos if todo["done"])

        # Build todo list display
        todo_lines = []
        for todo in todos:
            checkbox = "[X]" if todo["done"] else "[ ]"
            todo_lines.append(f"{checkbox} {todo['text']}")

        content = f"""
Todo List ({completed}/{len(todos)} completed)
---
{chr(10).join(todo_lines)}
---
Controls: [a] Add  [d] Delete  [Space] Toggle  [q] Quit
"""
        return {"content": content}

    return {
        "template": "{{ content }}",
        "data": render_data(),
        "on_enter": setup_handlers,
    }

# Set up keyboard handlers
def setup_handlers():
    def on_quit(event):
        if event.key == "q":
            app.quit()

    app.on(EventType.KEY, on_quit, scope=HandlerScope.VIEW, view_name="main")

# Run the app
app.run()
```

### Key Features Demonstrated

- **View Decorators**: Define views using `@app.view()` decorator (Flask-like)
- **State Management**: Reactive state with `app.state` that triggers re-renders
- **Event Handling**: Register keyboard handlers with `app.on()`
- **Template Rendering**: Use Jinja2 templates for UI layout
- **Lifecycle Hooks**: `on_enter` and `on_exit` hooks for view setup/teardown

For more examples, check out the `examples/` directory.


---


## Project Goals


### Primary Goals

1. Create a declarative TUI framework that reduces boilerplate for common CLI patterns

2. Provide a component library for standard UI elements (inputs, tables, menus, etc.)

3. Enable responsive layouts that adapt to terminal size

4. Support keyboard-driven navigation with optional mouse support

5. Achieve feature parity with basic web forms for data collection/display


### Success Metrics

- Build 3+ demo applications showcasing different use cases

- Documentation coverage for all public APIs

- Performance: Render complex UIs (<100 elements) at 60fps

- Developer adoption: 100+ GitHub stars within 3 months of release


---


## Technical Architecture


### High-Level Design


```

┌─────────────────────────────────────────────────┐

│              User Application                    │

│  (View functions, state management, handlers)   │

└────────────────┬────────────────────────────────┘
                │

┌────────────────▼────────────────────────────────┐

│            Wijjit Core API                      │

│  - App class \& view decorator                   │

│  - Navigation system                            │

│  - Global state management                      │

└────────────┬────────────────────────────────────┘
            │
   ┌────────┼────────┐
   │        │        │

┌───▼───┐ ┌──▼──┐ ┌──▼────────┐

│Template│ │Layout│ │ Terminal  │

│ Engine │ │Engine│ │  I/O      │

└───┬───┘ └──┬──┘ └──┬────────┘
   │        │        │

┌───▼────────▼────────▼──────────────────────────┐

│         Rendering Pipeline                      │

│  1. Parse template → AST                        │

│  2. Calculate layout → coordinates              │

│  3. Render elements → ANSI strings              │

│  4. Composite → final output                    │

└─────────────────────────────────────────────────┘

```


### Core Components


#### 1. Application Layer (`wijjit/core/`)

- **`app.py`**: Main Wijjit class, view decorator, navigation

- **`state.py`**: Global state with change detection and reactivity

- **`renderer.py`**: Orchestrates rendering pipeline


#### 2. Template Layer (`wijjit/template/`)

- **`tags.py`**: Custom Jinja extensions (frame, textinput, button, etc.)

- **`filters.py`**: Custom filters (humanize, timeago, etc.)

- **`loader.py`**: Template file loading and caching


#### 3. Layout Layer (`wijjit/layout/`)

- **`engine.py`**: Layout calculation (sizes, positions)

- **`frames.py`**: Frame/border rendering with scroll support

- **`positioning.py`**: Coordinate mapping for elements

- **`scroll.py`**: Scroll state management


#### 4. Elements Layer (`wijjit/elements/`)

- **`base.py`**: Base Element and Container classes

- **`input.py`**: TextInput, Select, Checkbox, RadioGroup

- **`display.py`**: Table, Tree, Progress, LogView

- **`interactive.py`**: Button, Menu, Link, Tabs


#### 5. Terminal Layer (`wijjit/terminal/`)

- **`input.py`**: Keyboard/mouse event handling

- **`screen.py`**: Alternate buffer, cursor control

- **`ansi.py`**: ANSI escape code utilities


### Data Flow


```

User Input → InputHandler → FocusManager → Element.handle\_key()
                                             ↓
                                        State Change
                                             ↓
                                     Trigger Re-render
                                             ↓

Template + State → Pre-render (Layout) → Render → Terminal

```


---


## Feature Breakdown


### Phase 1: Core Foundation (Weeks 1-2)


**Deliverables:**

- [ ] Basic Wijjit app class

- [ ] View decorator and routing system

- [ ] Global state management with change detection

- [ ] Simple template rendering (no custom tags yet)

- [ ] Keyboard input loop (blocking, raw mode)

- [ ] Alternate screen buffer management

- [ ] Basic demo: Hello World with navigation


**Technical Tasks:**

- Implement `Wijjit` class with `run()` method

- Create `@app.view()` decorator

- Build `State` class with `\_\_setitem\_\_` change detection

- Integrate Jinja2 environment

- Implement basic input handler with `tty` module

- ANSI escape codes for screen control


### Phase 2: Layout Engine (Weeks 3-4)


**Deliverables:**

- [ ] Frame macro with border styles

- [ ] Size calculation (fixed, fill, auto, percentages)

- [ ] Padding and margin support

- [ ] Coordinate mapping system

- [ ] Terminal resize handling

- [ ] Demo: Multi-frame layout


**Technical Tasks:**

- Create `LayoutNode` tree structure

- Implement bottom-up size calculation

- Implement top-down position assignment

- Build frame rendering with box-drawing characters

- Support 5 border styles (single, double, rounded, heavy, dashed)

- Handle percentage widths/heights

- Create `LayoutEngine` class


**Frame Attributes:**

```python

border: "none" | "single" | "double" | "rounded" | "heavy" | "dashed"

width: int | "auto" | "fill" | "100%" | "50%"

height: int | "auto" | "fill" | "100%"

padding: int | (top, right, bottom, left)

margin: int | (top, right, bottom, left)

title: str

title\_align: "left" | "center" | "right"

overflow\_x: "clip" | "scroll" | "auto" | "wrap"

overflow\_y: "clip" | "scroll" | "auto" | "wrap"

```


### Phase 3: Input Elements (Weeks 5-6)


**Deliverables:**

- [ ] TextInput with cursor positioning

- [ ] Button with activation

- [ ] Focus management (Tab/Shift+Tab)

- [ ] Basic form validation

- [ ] Select/dropdown component

- [ ] Checkbox and RadioGroup

- [ ] Demo: User registration form


**Input Elements:**

```python

{% textinput id="username" placeholder="Enter username" %}

{% textinput id="password" type="password" %}

{% numberinput id="port" min=1024 max=65535 %}

{% select id="theme" options=\["dark", "light"] %}

{% checkbox id="remember" label="Remember me" %}

{% radiogroup id="mode" options=\["auto", "manual"] %}

{% button action="submit" variant="primary" %}Submit{% endbutton %}

```


**Technical Tasks:**

- Implement `Element` base class with focus support

- Create `FocusManager` for Tab navigation

- Build text input with editing (insert, delete, arrow keys)

- Implement button activation on Enter/Space

- Create select with arrow key navigation

- Add input validation framework


### Phase 4: Display Elements (Weeks 6-7)


**Deliverables:**

- [ ] Table component (leveraging Rich)

- [ ] Tree view with expand/collapse

- [ ] Progress bar

- [ ] Log viewer with auto-scroll

- [ ] Tabs component

- [ ] Demo: File browser


**Display Elements:**

```python

{% table data=items columns=\["Name", "Size"] selectable=true %}

{% tree data=file\_tree on\_select="open\_node" %}

{% progress value=50 max=100 %}

{% logview lines=logs follow=true %}

{% tabs active="overview" %}
 {% tab key="overview" %}...{% endtab %}

{% endtabs %}

```


**Technical Tasks:**

- Integrate Rich Table component

- Build tree data structure with state

- Create progress bar with percentage/bar format

- Implement log viewer with scroll-to-bottom

- Create tabs with keyboard switching


### Phase 5: Advanced Features (Weeks 7-8)


**Deliverables:**

- [ ] Overflow and scrolling

- [ ] Scrollbar rendering

- [ ] Layout macros (hstack, vstack, split)

- [ ] ANSI-aware text clipping

- [ ] Event hooks (before\_navigate, on\_state\_change)

- [ ] Demo: Dashboard with multiple panes


**Layout Macros:**

```jinja

{% hstack spacing=2 %}
 {{ button("OK") }}
 {{ button("Cancel") }}

{% endhstack %}


{% vstack fill=true %}
 {% for item in items %}...{% endfor %}

{% endvstack %}


{% split direction="horizontal" ratio="30:70" %}
 {% left %}Sidebar{% endleft %}
 {% right %}Content{% endright %}

{% endsplit %}

```


**Technical Tasks:**

- Implement scroll offset tracking per frame

- Render scrollbars with thumb/track

- Create stack layout algorithms

- Build split pane with ratio calculation

- Add text wrapping with ANSI preservation

- Create hook system for lifecycle events


### Phase 6: Polish \& Documentation (Weeks 8-10)


**Deliverables:**

- [ ] Mouse support (optional)

- [ ] Performance optimization (render caching)

- [ ] Comprehensive documentation

- [ ] 5+ example applications

- [ ] Unit tests for core components

- [ ] GitHub repository with CI/CD


**Documentation Sections:**

- Quick start guide

- API reference

- Template syntax guide

- Element catalog with examples

- Cookbook (common patterns)

- Migration guide (from other TUI libs)


**Example Applications:**

- Todo list manager

- File browser

- System monitor

- API testing tool

- Database query interface


---


## Technical Considerations


### Performance


**Optimization Strategies:**

1. **Render caching**: Cache rendered frames when content unchanged

2. **Dirty tracking**: Only re-render changed regions

3. **Virtual scrolling**: Render only visible rows for large tables

4. **Debounced input**: Batch rapid keystrokes

5. **Lazy template compilation**: Compile templates once


**Performance Targets:**

- Initial render: <100ms for complex layouts

- Input response: <16ms (60fps)

- Memory: <50MB for typical applications


### Overflow and Scrolling


**Clip Mode** (`overflow="clip"`):

- Content beyond bounds is cut off

- No scrollbar shown

- Simplest, fastest rendering


**Scroll Mode** (`overflow="scroll"`):

- Always show scrollbar

- Arrow keys scroll content

- PageUp/PageDown for large jumps

- Home/End for top/bottom


**Auto Mode** (`overflow="auto"`):

- Show scrollbar only when needed

- Dynamically calculate content height

- Automatically hide when all content visible


**Wrap Mode** (`overflow="wrap"`):

- Text wraps to next line

- Respects word boundaries

- Increases content height dynamically


### Text Handling with ANSI


**Challenge**: ANSI escape codes (colors, formatting) don't count toward visible length


**Solutions:**

1. **Strip-and-measure**: Regex to remove ANSI, measure length

2. **Clip-with-preservation**: Clip visible chars but keep ANSI codes

3. **Slice-with-codes**: When scrolling, maintain ANSI state across slices


```python

def clip\_to\_width(text: str, width: int) -> str:
   """Clip text preserving ANSI codes"""
   ansi\_pattern = re.compile(r'\\x1b\\\[\[0-9;]*m')
   parts = ansi\_pattern.split(text)
   
   result = \[]
   visible\_count = 0
   
   for i, part in enumerate(parts):
       if i % 2 == 1:  # ANSI code
           result.append(part)
       else:  # Regular text
           remaining = width - visible\_count
           if len(part) <= remaining:
               result.append(part)
               visible\_count += len(part)
           else:
               result.append(part\[:remaining])
               break
   
   return ''.join(result)

```


### State Management


**Philosophy**: Single source of truth


```python

# Global state

state.current\_file = Path("config.py")

state.editor\_buffer = "def main():\\n    pass"

state.unsaved\_changes = True


# View-specific ephemeral state

state.view\_context\['editor'] = {
   'cursor\_pos': (10, 5),
   'scroll\_offset': 0

}

```


**Change Detection**:

- Intercept `\_\_setitem\_\_` to detect changes

- Notify registered watchers

- Automatically trigger re-render


**Best Practices**:

- Keep state flat when possible

- Use view\_context for temporary state

- Avoid nested mutations (use immutable updates)


### Cross-Platform Compatibility


**Challenges:**

- Windows terminal limitations (ConPTY vs legacy)

- macOS vs Linux terminal escape sequences

- UTF-8 support for box-drawing characters


**Solutions:**

1. Use `prompt\_toolkit` for cross-platform input handling

2. Detect terminal capabilities with `blessed`

3. Fallback to ASCII box-drawing on limited terminals

4. Test on Windows Terminal, iTerm2, GNOME Terminal


### Error Handling


**Graceful Degradation:**

- Terminal too small: Show minimum size warning

- Resize during input: Reflow layout

- Invalid template: Show error view with traceback

- Unhandled exception: Exit alternate screen before crash


**Debugging:**

- Log mode: Write render output to file

- Step mode: Pause on each render

- State inspector: View current state tree


---


## Dependencies


### Core Dependencies

```python

jinja2>=3.1.0        # Template engine

prompt\_toolkit>=3.0  # Terminal input/output

rich>=13.0           # ANSI rendering, tables

```


### Optional Dependencies

```python

blessed>=1.20        # Terminal capabilities (cross-platform)

pyperclip>=1.8      # Clipboard integration

pygments>=2.0       # Syntax highlighting

```


### Development Dependencies

```python

pytest>=7.0         # Testing

pytest-cov>=4.0     # Coverage

black>=23.0         # Formatting

mypy>=1.0           # Type checking

sphinx>=5.0         # Documentation

```


---


## Development Workflow


### Repository Structure

```

wijjit/

├── wijjit/

│   ├── \_\_init\_\_.py

│   ├── core/

│   ├── elements/

│   ├── layout/

│   ├── template/

│   └── terminal/

├── examples/

│   ├── todo.py

│   ├── file\_browser.py

│   └── form\_demo.py

├── tests/

│   ├── test\_core.py

│   ├── test\_layout.py

│   └── test\_elements.py

├── docs/

│   ├── quickstart.md

│   ├── api.md

│   └── examples/

├── pyproject.toml

└── README.md

```


### Testing Strategy


**Unit Tests:**

- Layout calculation algorithms

- State change detection

- Text clipping with ANSI

- Focus navigation


**Integration Tests:**

- Full render pipeline

- View navigation

- Input handling

- Resize behavior


**Manual Tests:**

- Visual regression (screenshot comparison)

- Terminal compatibility (multiple emulators)

- Performance benchmarks


### CI/CD Pipeline


```yaml

# .github/workflows/test.yml

- Run pytest with coverage

- Type check with mypy

- Format check with black

- Build documentation

- Publish to PyPI on release tags

```


---


## Risk Assessment


| Risk | Impact | Likelihood | Mitigation |

|------|--------|------------|------------|

| Terminal compatibility issues | High | Medium | Use prompt\_toolkit, test on multiple platforms |

| Performance with large datasets | Medium | Medium | Implement virtual scrolling, render caching |

| Complex layout edge cases | Medium | High | Comprehensive test suite, clear error messages |

| Adoption/competition | High | Medium | Focus on unique value prop, excellent docs |

| Scope creep | Medium | High | Strict MVP definition, save features for v2 |


---


## Success Criteria


### MVP Completion (Week 8)

- \[ ] All Phase 1-4 features implemented

- \[ ] 3 working demo applications

- \[ ] Basic documentation published

- \[ ] Core API stable


### v1.0 Release (Week 10)

- \[ ] All Phase 5-6 features implemented

- \[ ] 5 example applications

- \[ ] Comprehensive documentation

- \[ ] PyPI package published

- \[ ] GitHub repository public


### Post-Launch (3 months)

- \[ ] 100+ GitHub stars

- \[ ] 10+ community contributions

- \[ ] Featured in Python newsletter/podcast

- \[ ] 3+ real-world applications built


---


## Future Roadmap (Post-MVP)


### v1.1 - Enhanced Interactions

- Drag and drop support

- Context menus

- Tooltips/hover text

- Animations and transitions

- Sound effects (terminal bell)


### v1.2 - Advanced Components

- Data grid with sorting/filtering

- Charts and graphs

- Markdown renderer

- Code editor with syntax highlighting

- File picker dialog


### v1.3 - Developer Experience

- Hot reload for templates

- Interactive debugger

- Visual layout inspector

- Template linting

- IDE extensions (VS Code)


### v2.0 - Async and Streaming

- Async/await support
- WebSocket integration
- Streaming data updates
- Background tasks
- Real-time collaboration


### Community Extensions

- Plugin system for custom elements

- Theme marketplace

- Component library (wijjit-ui)

- Integrations (Django, FastAPI)


---


## Team Roles \& Responsibilities


### Core Development

- **Lead Developer**: Architecture, core API, code review

- **UI/Layout Developer**: Frame rendering, layout engine, scrolling

- **Component Developer**: Input/display elements, Rich integration

- **Terminal Expert**: Cross-platform compatibility, ANSI handling


### Supporting Roles

- **Technical Writer**: Documentation, tutorials, API reference

- **QA Engineer**: Test suite, compatibility testing, performance

- **DevOps**: CI/CD, PyPI publishing, release management

- **Community Manager**: GitHub issues, discussions, examples


---


## Communication Plan


### Internal

- **Daily standups** (async in Slack)

- **Weekly demos** (Friday showcase)

- **Bi-weekly planning** (Sprint planning)

- **Shared document** for design decisions


### External

- **GitHub Discussions** for community questions

- **Discord server** for real-time help

- **Monthly blog posts** on progress

- **Twitter** for announcements


---


## Budget \& Resources


### Development Time

- **8 weeks × 4 developers** = 32 person-weeks

- Average 30 hours/week = 960 hours total


### Infrastructure

- GitHub (free for open source)

- PyPI hosting (free)

- Documentation hosting (ReadTheDocs, free)

- CI/CD (GitHub Actions, free tier)


### Estimated Cost

- Developer time: $960 hours × $75/hr = $72,000

- Infrastructure: $0 (using free tiers)

- **Total**: $72,000


---


## Conclusion


Wijjit addresses a clear gap in the Python ecosystem: there's no Flask-equivalent for building TUIs. By combining familiar web patterns (Jinja templates, view decorators) with modern terminal capabilities, we can dramatically reduce the friction of building rich console applications.


The 8-10 week timeline to MVP is aggressive but achievable given the modular architecture and clear phase boundaries. The framework's value proposition—"Flask for the console"—should resonate immediately with Python web developers looking to build CLI tools.


**Next Steps:**

1. Review and approve project plan

2. Set up repository and development environment

3. Begin Phase 1: Core foundation

4. Schedule weekly check-ins


**Questions for Discussion:**

- Resource allocation: Do we have 4 developers available?

- Timeline: Is 8-10 weeks realistic for our team?

- Scope: Any Phase 1-4 features that should be deprioritized?

- Naming: Final approval on "wijjit" branding?


---


*Document Version: 1.0*  

*Date: 2025-10-30*  

*Author: Architecture Team*

