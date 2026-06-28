# Wijjit Documentation Plan

This document outlines the structure and content plan for the Wijjit Sphinx documentation.

## Documentation Structure

```
docs/
├── source/
│   ├── index.rst                    # Main entry point
│   │
│   ├── getting_started/             # Getting Started Guide
│   │   ├── index.rst                # Overview
│   │   ├── installation.rst         # Installation instructions
│   │   ├── quickstart.rst          # Quick start guide (Hello World)
│   │   └── tutorial.rst            # Step-by-step tutorial (building a todo app)
│   │
│   ├── user_guide/                  # User Guide (detailed documentation)
│   │   ├── index.rst               # Overview
│   │   ├── core_concepts.rst       # App, Views, Routing
│   │   ├── state_management.rst    # State class, reactivity
│   │   ├── templates.rst           # Jinja2 templates, template tags
│   │   ├── event_handling.rst      # Events, actions, key handlers
│   │   ├── layout_system.rst       # Frames, VStack, HStack, sizing
│   │   ├── components.rst          # All components (input & display)
│   │   ├── modal_dialogs.rst       # Modal system, built-in dialogs
│   │   ├── focus_navigation.rst    # Focus management, Tab navigation
│   │   ├── mouse_support.rst       # Mouse events, click, scroll
│   │   └── styling.rst             # Colors, ANSI, styling
│   │
│   ├── api_reference/               # API Reference (auto-generated + manual)
│   │   ├── index.rst               # Overview
│   │   ├── core.rst                # wijjit.core (App, Wijjit class)
│   │   ├── state.rst               # wijjit.core.state (State class)
│   │   ├── events.rst              # wijjit.core.events (Event types, handlers)
│   │   ├── focus.rst               # wijjit.core.focus (FocusManager)
│   │   ├── overlay.rst             # wijjit.core.overlay (Modal system)
│   │   ├── layout.rst              # wijjit.layout (Layout engine, frames)
│   │   ├── elements.rst            # wijjit.elements (All elements)
│   │   ├── tags.rst                # wijjit.tags (Template tags)
│   │   └── terminal.rst            # wijjit.terminal (ANSI, screen, input)
│   │
│   ├── examples/                    # Examples & Tutorials
│   │   ├── index.rst               # Gallery overview
│   │   ├── basic.rst               # Basic examples (hello world, simple input)
│   │   ├── forms.rst               # Form examples (login, registration)
│   │   ├── data_display.rst        # Tables, trees, lists
│   │   ├── layout.rst              # Layout examples
│   │   ├── advanced.rst            # Advanced examples (modals, navigation)
│   │   └── cookbook.rst            # Common patterns & recipes
│   │
│   ├── developer_guide/             # Developer Guide
│   │   ├── index.rst               # Overview
│   │   ├── architecture.rst        # Architecture overview
│   │   ├── contributing.rst        # How to contribute
│   │   ├── testing.rst             # Testing guide
│   │   └── extending.rst           # Creating custom elements
│   │
│   └── conf.py                      # Sphinx configuration
```

## Content Priorities

### Phase 1: Essential Documentation (Immediate)
1. **index.rst** - Main landing page with overview
2. **getting_started/installation.rst** - How to install
3. **getting_started/quickstart.rst** - Hello World + Login Form
4. **getting_started/tutorial.rst** - Building a complete todo app
5. **user_guide/core_concepts.rst** - App, views, routing, state
6. **user_guide/components.rst** - Component overview and examples

### Phase 2: Comprehensive User Guide (High Priority)
7. **user_guide/state_management.rst** - Detailed state docs
8. **user_guide/templates.rst** - Template system deep dive
9. **user_guide/event_handling.rst** - Event system
10. **user_guide/layout_system.rst** - Layout in detail
11. **user_guide/modal_dialogs.rst** - Modal system
12. **examples/cookbook.rst** - Common patterns

### Phase 3: API Reference (Medium Priority)
13. **api_reference/*.rst** - Auto-generated API docs with sphinx.ext.autodoc
14. Manual API documentation for complex classes

### Phase 4: Advanced Topics (Lower Priority)
15. **developer_guide/architecture.rst** - Detailed architecture
16. **developer_guide/extending.rst** - Custom elements
17. **examples/advanced.rst** - Advanced examples

## Sphinx Extensions to Add

1. **sphinx.ext.autodoc** - Auto-generate API docs from docstrings
2. **sphinx.ext.napoleon** - Support for NumPy-style docstrings
3. **sphinx.ext.viewcode** - Add links to source code
4. **sphinx.ext.intersphinx** - Link to Python/Jinja2 docs
5. **sphinx_copybutton** - Add copy button to code blocks
6. **sphinx-tabs** - Tabbed content for examples
7. **myst-parser** - Support Markdown files (optional)

## Theme

Use **sphinx-rtd-theme** (Read the Docs theme) for:
- Professional appearance
- Mobile-friendly
- Good navigation
- Searchable
- Widely recognized

Alternative: **furo** (modern, clean theme)

## Documentation Writing Guidelines

1. **Code Examples**: Every concept should have a working code example
2. **Cross-references**: Link between related sections
3. **Runnable Examples**: Point to files in examples/ directory
4. **Screenshots**: Consider adding terminal screenshots (using asciinema)
5. **API Docs**: Use NumPy-style docstrings (already done in code)
6. **Consistency**: Use consistent terminology throughout

## Documentation Workflow

1. Write .rst files in docs/source/
2. Build with `make html` or `sphinx-build`
3. View locally at docs/_build/html/index.html
4. Deploy to Read the Docs (free for open source)

## Quick Build Commands

```bash
# Build HTML documentation
cd docs
make html

# Clean build
make clean
make html

# View in browser (Linux/WSL)
python -m http.server -d _build/html 8000
# Then open http://localhost:8000

# Windows
start _build/html/index.html
```

## Content Templates

### Example Template
Every example should include:
- Brief description
- Full working code
- Screenshot or expected output
- Explanation of key concepts
- Link to runnable example in examples/

### API Reference Template
Every API reference should include:
- Class/function signature
- Parameters (with types)
- Return value (with type)
- Usage example
- Related APIs
- Auto-generated from docstrings where possible

### Tutorial Template
Every tutorial should include:
- Learning objectives
- Prerequisites
- Step-by-step instructions
- Complete working code at each step
- Exercises or challenges
- Next steps

## Success Metrics

- Documentation covers all public APIs
- Every component has at least one example
- New users can build their first app in <15 minutes
- Common questions are answered in docs
- Search works well (sphinx search or ReadTheDocs search)
