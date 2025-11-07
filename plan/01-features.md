# Wijjit Feature List

**Version 1.0 - Complete Feature Specification**

---

## Core Framework

### Application Management
- **Wijjit App Class**: Main application container with lifecycle management
- **View Decorator System**: Flask-like `@app.view()` decorator for defining views
- **View Navigation**: `app.navigate(view_name, **params)` for switching between views
- **View Parameters**: Pass data between views during navigation
- **Global State Management**: Reactive state object with change detection
- **View Context**: Ephemeral state scoped to specific views
- **Lifecycle Hooks**: `on_enter`, `on_exit`, `before_navigate`, `after_navigate`
- **State Watchers**: `@app.watch(key)` decorator for reacting to state changes
- **Hot Reload Support**: (Future) Auto-reload templates on change

### Template System
- **Jinja2 Integration**: Full Jinja2 template engine support
- **Custom Tags**: `{% frame %}`, `{% button %}`, `{% textinput %}`, etc.
- **Template Inheritance**: Extend and include templates
- **Custom Filters**: `humanize`, `timeago`, `wordwrap`, etc.
- **Template Loader**: Load from filesystem with caching
- **Inline Templates**: Define templates directly in view functions
- **Pre-rendering Phase**: Calculate layout before Jinja rendering

## Layout System

### Frame System
- **Frame Component**: Bordered containers with flexible sizing
- **Border Styles**: 
  - `single` (┌─┐)
  - `double` (╔═╗)
  - `rounded` (╭─╮)
  - `heavy` (┏━┓)
  - `dashed` (┌╌┐)
  - `none` (no border)
- **Title Support**: Positioned titles (left, center, right)
- **Padding**: Individual padding per side `(top, right, bottom, left)`
- **Margin**: Spacing between frames
- **Overflow Handling**:
  - `clip` - Cut off content
  - `scroll` - Always show scrollbar
  - `auto` - Show scrollbar when needed
  - `wrap` - Wrap text content

### Sizing System
- **Fixed Sizes**: Integer widths/heights
- **Relative Sizes**: Percentages (`"50%"`, `"100%"`)
- **Fill Mode**: `"fill"` to take available space
- **Auto Sizing**: `"auto"` to size based on content
- **Min/Max Constraints**: `min_width`, `max_width`, `min_height`, `max_height`
- **Responsive Layout**: Automatic recalculation on terminal resize

### Layout Primitives
- **HStack**: Horizontal layout with spacing
- **VStack**: Vertical layout with spacing
- **Split Panes**: Divide space with ratios (e.g., `"30:70"`)
- **Grid System**: (Future) CSS-like grid layout
- **Absolute Positioning**: (Future) Position elements at specific coordinates

### Scrolling
- **Vertical Scrolling**: Arrow keys, PageUp/PageDown
- **Horizontal Scrolling**: Left/Right arrows
- **Scrollbar Rendering**: Visual track and thumb indicators
- **Scroll State**: Persistent scroll position per frame
- **Scroll to Element**: (Future) Programmatic scrolling
- **Smooth Scrolling**: (Future) Animated scrolling

## Styling System

### Style Definitions
- **Style Class**: Encapsulates all style properties
- **Color Support**:
  - Named colors (`red`, `blue`, `bright_green`)
  - ANSI codes (`31`, `38;5;208`)
  - Hex colors (`#FF0000`) with 24-bit RGB conversion
- **Text Attributes**: `bold`, `dim`, `italic`, `underline`, `blink`, `reverse`
- **Border Styling**: Color and style per element
- **Layout Properties**: padding, margin, alignment

### Theme System
- **Theme Class**: Collections of named styles
- **Built-in Themes**:
  - `default` - Standard terminal colors
  - `dark` - Modern dark theme
  - `light` - Light background theme (Future)
- **Custom Themes**: User-defined color schemes
- **Theme Switching**: Runtime theme changes
- **Theme Inheritance**: Themes can extend other themes

### CSS-Like Classes
- **Class Names**: Apply multiple classes to elements
- **Class Composition**: Combine classes for complex styles
- **Inline Style Override**: Inline attributes override classes
- **Pseudo-Classes**: (Future) `:hover`, `:focus`, `:active`
- **Pre-defined Classes**:
  - `primary`, `secondary`, `success`, `danger`, `warning`, `info`, `muted`
  - `button`, `button-primary`, `button-danger`
  - `input`, `input-focus`
  - `table-header`, `table-row-even`, `table-row-odd`, `table-row-selected`
  - `container`, `panel`, `card`

## Input Elements

### Text Input
- **Single-line Text Input**: Basic text field
- **Multi-line Text Area**: Scrollable text area
- **Password Input**: Masked character display
- **Placeholder Text**: Hint when empty
- **Cursor Positioning**: Arrow key navigation
- **Text Selection**: (Future) Shift+Arrow selection
- **Copy/Paste**: (Future) System clipboard integration
- **Input Validation**: Custom validation functions
- **Change Events**: `on_change` callback

### Selection Controls
- **Select/Dropdown**: Single selection from list
- **Multi-Select**: Multiple selection with checkboxes
- **Radio Group**: Mutually exclusive options
- **Checkbox**: Boolean toggle
- **Toggle Switch**: (Future) Visual on/off switch

### Numeric Input
- **Number Input**: Integer/float with validation
- **Range Constraints**: `min` and `max` values
- **Step Size**: Increment/decrement amount
- **Spinner Controls**: (Future) +/- buttons

### Interactive Elements
- **Button**: Clickable action trigger
- **Link**: Navigation to other views
- **Menu**: Keyboard-navigable option list
- **Context Menu**: Right-click menu
- **Tabs**: Tabbed interface navigation
- **Accordion**: (Future) Collapsible sections

## Display Elements

### Data Display
- **Table**: Sortable, filterable data grid
  - Row selection (single/multi)
  - Column sorting
  - Fixed header
  - Pagination support
  - Custom cell renderers
- **Tree View**: Hierarchical data with expand/collapse
  - Lazy loading
  - Custom icons
  - Drag and drop (Future)
- **List View**: Simple scrollable list
- **Data Grid**: (Future) Editable cells

### Progress Indicators
- **Progress Bar**: Percentage-based progress
- **Spinner**: Loading indicator with multiple styles
- **Indeterminate Progress**: (Future) Unknown duration
- **Status Indicators**: Color-coded status badges

### Content Display
- **Text Block**: Formatted text with wrapping
- **Code Block**: Syntax-highlighted code
- **Markdown Renderer**: (Future) Render markdown
- **Log Viewer**: Auto-scrolling log display
- **Notification/Toast**: Temporary message display

### Visualization
- **Charts**: (Future) Bar, line, pie charts
- **Sparklines**: (Future) Inline mini-charts
- **Graphs**: (Future) Network/relationship diagrams

## Event System

### Event Types
- **KeyEvent**: Keyboard input with modifiers
- **MouseEvent**: Click, drag, scroll, hover
- **ActionEvent**: Button clicks, menu selections
- **ChangeEvent**: Input value changes
- **FocusEvent**: Focus gained/lost
- **NavigateEvent**: View navigation
- **CustomEvent**: User-defined events

### Event Handling
- **Handler Decorator**: `@app.handler(view, action)`
- **Global Handlers**: `@app.global_handler(action)`
- **Inline Handlers**: Lambda functions in view config
- **Class Methods**: Auto-registered in class-based views
- **Dynamic Registration**: `app.register_handler()`
- **Priority System**: Control handler execution order
- **Event Propagation**: Stop propagation with `event.stop_propagation()`
- **Event Bubbling**: Events bubble up element tree

### Middleware
- **Middleware System**: Pre-process all events
- **Logging Middleware**: Log all actions
- **Auth Middleware**: Check permissions
- **Validation Middleware**: Validate input
- **Custom Middleware**: User-defined processing

### Async Support
- **Async Handlers**: `async def` handler support
- **Async Actions**: Long-running operations
- **Background Tasks**: Non-blocking operations
- **Progress Reporting**: Update UI during async ops

## Input System

### Keyboard Support
- **Raw Mode**: Character-by-character input
- **Key Parsing**: All keys, combinations, escape sequences
- **Modifiers**: Ctrl, Alt, Shift detection
- **Function Keys**: F1-F12, Home, End, etc.
- **International Input**: UTF-8 character support
- **Key Sequences**: Multi-key combos (e.g., `gg` in Vim)
- **Input Buffer**: Handle rapid keystrokes

### Mouse Support
- **Mouse Tracking Modes**:
  - `NORMAL` - Click and release
  - `BUTTON_EVENT` - Click, release, drag
  - `ANY_EVENT` - All motion
- **Mouse Events**:
  - Click (left, middle, right)
  - Double-click
  - Drag
  - Scroll (up, down, left, right)
  - Hover
- **Coordinate Mapping**: Map mouse position to elements
- **Mouse Modifiers**: Shift, Alt, Ctrl with mouse

### Focus Management
- **Tab Navigation**: Cycle through focusable elements
- **Shift+Tab**: Reverse tab order
- **Mouse Focus**: Click to focus
- **Programmatic Focus**: `element.focus()`
- **Focus Indicators**: Visual focus state
- **Focus Trapping**: (Future) Keep focus within modal

## Key Binding System

### Binding Definition
- **Simple Keys**: Single key bindings (`ctrl+s`)
- **Key Sequences**: Multi-key combos (`['g', 'g']`)
- **Binding Scopes**:
  - `GLOBAL` - Active everywhere
  - `VIEW` - Active in specific view
  - `ELEMENT` - Active when element focused
  - `MODAL` - Active in modal dialogs
- **Priority System**: Resolve conflicts
- **Categories**: Organize bindings for help
- **Descriptions**: Human-readable documentation

### Binding Management
- **Decorator Binding**: `@app.bind(keys, action)`
- **Programmatic Binding**: `app.keybindings.bind()`
- **Unbinding**: Remove bindings
- **Enable/Disable**: Toggle bindings on/off
- **Conflict Detection**: Warn about overlapping bindings
- **Key Hints**: Display shortcuts in UI

### User Customization
- **Config Files**: JSON/YAML key binding configs
- **Load/Save**: Persist user customizations
- **Binding Editor**: (Future) Visual binding configuration
- **Import/Export**: Share binding configs

### Help System
- **Command Palette**: Searchable action list (Ctrl+P style)
- **Help View**: Auto-generated keyboard reference
- **Contextual Help**: Show bindings for current view
- **Tooltips**: (Future) Hover to see shortcuts

## Component System

### Component Definition
- **Component Decorator**: `@app.component(name)`
- **Props System**: Pass data to components
- **Default Props**: Default values for props
- **Prop Validation**: Type checking and validation
- **Component Registry**: Named component lookup

### Composition
- **Nested Components**: Components within components
- **Slots**: Pass content sections to components
- **Higher-Order Components**: Wrap components with behavior
- **Component Libraries**: Reusable component collections

### Built-in Components
- **Layout Components**:
  - `navbar` - Navigation bar
  - `sidebar` - Side navigation
  - `three_column_layout` - Three-pane layout
  - `split_view` - Adjustable split panes
- **UI Components**:
  - `user_card` - User profile card
  - `status_badge` - Status indicator
  - `metric_card` - Dashboard metric display
  - `form_field` - Form input with label/error
- **Utility Components**:
  - `modal` - Modal dialog
  - `with_loading` - Loading state wrapper
  - `error_boundary` - Error handling wrapper

## Rendering System

### Virtual Screen Buffer
- **Cell-based Buffer**: 2D array of styled cells
- **ANSI Parsing**: Parse and preserve ANSI codes
- **Dirty Tracking**: Mark changed regions
- **Bounds Tracking**: Element position and size

### Rendering Pipeline
1. **Parse Template**: Jinja2 to string
2. **Pre-render Layout**: Calculate positions
3. **Render Elements**: Generate styled content
4. **Composite Buffer**: Combine into screen buffer
5. **Diff Rendering**: Compare with previous frame
6. **Terminal Output**: Write minimal ANSI commands

### Optimization
- **Render Caching**: Cache unchanged frames
- **Dirty Region Merging**: Combine overlapping regions
- **Rate Limiting**: Cap at 60 FPS
- **Debouncing**: Batch rapid state changes
- **Virtual Scrolling**: Render only visible rows
- **Double Buffering**: Eliminate flicker

### Performance
- **First Render**: <100ms for complex layouts
- **Incremental Update**: <16ms (60 FPS)
- **Input Response**: Sub-frame latency
- **Memory Usage**: <50MB typical

## Terminal Integration

### Screen Control
- **Alternate Screen**: Switch to separate buffer
- **Cursor Management**: Hide/show, position
- **Clear Operations**: Full screen, regions, lines
- **Terminal Size**: Detect and track changes
- **Resize Handling**: Automatic layout reflow

### ANSI Support
- **Text Attributes**: Bold, dim, italic, underline
- **Color Modes**:
  - 8 colors (basic)
  - 16 colors (bright variants)
  - 256 colors (xterm palette)
  - 24-bit RGB (true color)
- **Cursor Positioning**: Move to any position
- **Scroll Regions**: Define scrolling areas
- **Box Drawing**: UTF-8 line characters

### Cross-Platform
- **Linux/macOS**: Full support via `termios`
- **Windows**: ConPTY and Windows Terminal support
- **Terminal Detection**: Capability detection
- **Fallback Modes**: ASCII when UTF-8 unavailable

## Developer Experience

### API Design
- **Flask-like API**: Familiar decorator patterns
- **Type Hints**: Full typing for IDE support
- **Docstrings**: Comprehensive documentation
- **Examples**: Rich example library
- **Error Messages**: Clear, actionable errors

### Debugging
- **Debug Mode**: Verbose logging
- **Profiler**: Performance timing
- **State Inspector**: View current state
- **Layout Inspector**: Visualize element bounds
- **Event Logging**: Track all events

### Testing
- **Unit Tests**: Test components in isolation
- **Integration Tests**: Test full applications
- **Visual Tests**: Screenshot comparison
- **Mock Input**: Simulate keyboard/mouse
- **Test Fixtures**: Reusable test data

### Documentation
- **API Reference**: Complete API docs
- **Quick Start**: Get started in 5 minutes
- **Tutorials**: Step-by-step guides
- **Cookbook**: Common patterns
- **Migration Guide**: From other TUI frameworks

## Distribution

### Packaging
- **PyPI Package**: `pip install wijjit`
- **Minimal Dependencies**: `jinja2`, `prompt_toolkit`, `rich`
- **Optional Dependencies**: Syntax highlighting, clipboard
- **Version Management**: Semantic versioning

### Platform Support
- **Python Versions**: 3.9+
- **Operating Systems**: Linux, macOS, Windows
- **Terminal Emulators**: iTerm2, GNOME Terminal, Windows Terminal, etc.

### Examples
- **Todo List**: Simple CRUD app
- **Text Editor**: Basic text editing
- **File Manager**: Browse files and directories
- **System Monitor**: Real-time system stats
- **Database Client**: Query database
- **API Tester**: Make HTTP requests
- **Git TUI**: Git operations
- **Log Viewer**: View and search logs

## Future Features (v2.0+)

### Advanced UI
- **Animations**: Smooth transitions
- **Themes**: More built-in themes
- **Custom Widgets**: User-defined elements
- **Drag and Drop**: Full DnD support
- **Split Panels**: User-resizable splits

### Data Binding
- **Two-way Binding**: Auto-sync state and UI
- **Computed Properties**: Derived state
- **Watchers**: Complex state reactions
- **Form Validation**: Declarative validation

### Networking
- **WebSocket Support**: Real-time updates
- **Server-Sent Events**: Stream data
- **HTTP Client**: Built-in requests
- **GraphQL**: GraphQL queries

### Extensibility
- **Plugin System**: Third-party extensions
- **Custom Themes**: Theme marketplace
- **Component Library**: Shared components
- **Middleware Plugins**: Auth, logging, etc.

### IDE Integration
- **VS Code Extension**: Template syntax highlighting
- **Language Server**: Autocomplete
- **Snippets**: Common patterns
- **Debugger**: Visual debugging
