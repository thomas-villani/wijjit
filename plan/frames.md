Perfect! Frame rendering is where the magic happens. Let's design this comprehensively.



## Frame Attributes



```python

# wijjit/layout/frames.py

from dataclasses import dataclass

from typing import Optional, Literal

from enum import Enum



class BorderStyle(Enum):
   NONE = "none"
   SINGLE = "single"    # ┌─┐│└─┘
   DOUBLE = "double"    # ╔═╗║╚═╝
   ROUNDED = "rounded"  # ╭─╮│╰─╯
   HEAVY = "heavy"      # ┏━┓┃┗━┛
   DASHED = "dashed"    # ┌╌┐╎└╌┘



class Overflow(Enum):
   CLIP = "clip"        # Cut off content
   SCROLL = "scroll"    # Always show scrollbar
   AUTO = "auto"        # Scrollbar if needed
   WRAP = "wrap"        # Wrap text content



@dataclass

class FrameStyle:
   # Border
   border: BorderStyle = BorderStyle.SINGLE
   border_color: Optional[str] = None  # ANSI color code
   
   # Size
   width: int | str = "auto"  # int, "auto", "fill", "100%", "50%"
   height: int | str = "auto"
   min_width: Optional[int] = None
   max_width: Optional[int] = None
   min_height: Optional[int] = None
   max_height: Optional[int] = None
   
   # Spacing
   padding: int | tuple[int, int, int, int] = 0  # top, right, bottom, left
   margin: int | tuple[int, int, int, int] = 0
   
   # Content
   title: Optional[str] = None
   title_align: Literal["left", "center", "right"] = "left"
   overflow_x: Overflow = Overflow.CLIP
   overflow_y: Overflow = Overflow.AUTO
   
   # Scrolling
   scrollable: bool = True  # Can this frame be scrolled with arrow keys
   scroll_x: int = 0  # Current horizontal scroll offset
   scroll_y: int = 0  # Current vertical scroll offset



# Border character sets

BORDER_CHARS = {
   BorderStyle.SINGLE: {
       'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
       'h': '─', 'v': '│',
       't': '┬', 'b': '┴', 'l': '├', 'r': '┤',
       'cross': '┼'
   },
   BorderStyle.DOUBLE: {
       'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',
       'h': '═', 'v': '║',
       't': '╦', 'b': '╩', 'l': '╠', 'r': '╣',
       'cross': '╬'
   },
   BorderStyle.ROUNDED: {
       'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯',
       'h': '─', 'v': '│',
       't': '┬', 'b': '┴', 'l': '├', 'r': '┤',
       'cross': '┼'
   },
   BorderStyle.HEAVY: {
       'tl': '┏', 'tr': '┓', 'bl': '┗', 'br': '┛',
       'h': '━', 'v': '┃',
       't': '┳', 'b': '┻', 'l': '┣', 'r': '┫',
       'cross': '╋'
   },
   BorderStyle.DASHED: {
       'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
       'h': '╌', 'v': '╎',
       't': '┬', 'b': '┴', 'l': '├', 'r': '┤',
       'cross': '┼'
   }

}

```



## Frame Class



```python

class Frame(Container):
   """A bordered container with overflow/scroll handling"""
   
   def __init__(self, id: str, style: FrameStyle):
       super().__init__(id)
       self.style = style
       self.content_lines: List[str] = []
       self.content_height = 0  # Actual content height
       self.content_width = 0   # Actual content width
       self.focused_child: Optional[Element] = None
   
   def set_content(self, content: str):
       """Set the raw content for this frame"""
       self.content_lines = content.split('\\n')
       self.content_height = len(self.content_lines)
       self.content_width = max(self._strip_ansi_len(line) 
                               for line in self.content_lines) if self.content_lines else 0
   
   def render(self, state: Any) -> str:
       """Render frame with borders, padding, and scroll handling"""
       if not self.bounds:
           return ""
       
       lines = []
       chars = BORDER_CHARS.get(self.style.border, BORDER_CHARS[BorderStyle.SINGLE])
       
       # Apply padding
       padding = self._normalize_padding(self.style.padding)
       pad_top, pad_right, pad_bottom, pad_left = padding
       
       # Calculate content area (inside border and padding)
       border_width = 0 if self.style.border == BorderStyle.NONE else 2
       content_width = self.bounds.width - border_width - pad_left - pad_right
       content_height = self.bounds.height - border_width - pad_top - pad_bottom
       
       # Check if scrolling is needed
       needs_scroll_y = self.content_height > content_height
       needs_scroll_x = self.content_width > content_width
       
       # Adjust for scrollbar space
       if needs_scroll_y and self.style.overflow_y != Overflow.CLIP:
           content_width -= 1  # Reserve space for scrollbar
       
       # Render top border
       if self.style.border != BorderStyle.NONE:
           top_line = self._render_top_border(chars, content_width)
           lines.append(top_line)
       
       # Render content lines with padding and scrolling
       visible_start_y = self.style.scroll_y
       visible_end_y = visible_start_y + content_height
       
       for i in range(content_height):
           line = self._render_content_line(
               i, 
               visible_start_y, 
               visible_end_y,
               content_width,
               pad_left,
               chars,
               needs_scroll_y
           )
           lines.append(line)
       
       # Render bottom border
       if self.style.border != BorderStyle.NONE:
           bottom_line = self._render_bottom_border(chars, content_width)
           lines.append(bottom_line)
       
       return '\\n'.join(lines)
   
   def _render_top_border(self, chars: dict, content_width: int) -> str:
       """Render top border with title"""
       color = self.style.border_color or ""
       reset = "\\033[0m" if color else ""
       
       # Start with top-left corner
       line = f"{color}{chars['tl']}"
       
       # Add title if present
       if self.style.title:
           title = f" {self.style.title} "
           title_len = len(title)
           
           if self.style.title_align == "left":
               line += title
               line += chars['h'] \* (content_width + 2 - title_len)
           elif self.style.title_align == "center":
               left_pad = (content_width + 2 - title_len) // 2
               right_pad = content_width + 2 - title_len - left_pad
               line += chars['h'] \* left_pad + title + chars['h'] \* right_pad
           else:  # right
               line += chars['h'] \* (content_width + 2 - title_len)
               line += title
       else:
           line += chars['h'] \* (content_width + 2)
       
       # Top-right corner
       line += f"{chars['tr']}{reset}"
       return line
   
   def _render_content_line(self, 
                           local_line_idx: int,
                           visible_start: int,
                           visible_end: int,
                           content_width: int,
                           pad_left: int,
                           chars: dict,
                           show_scrollbar: bool) -> str:
       """Render a single content line with clipping/scrolling"""
       color = self.style.border_color or ""
       reset = "\\033[0m" if color else ""
       
       # Start with left border
       if self.style.border != BorderStyle.NONE:
           line = f"{color}{chars['v']}{reset}"
       else:
           line = ""
       
       # Add left padding
       line += " " \* pad_left
       
       # Get content line (accounting for scroll)
       content_line_idx = visible_start + local_line_idx
       
       if 0 <= content_line_idx < len(self.content_lines):
           content = self.content_lines[content_line_idx]
           
           # Apply horizontal scroll
           if self.style.scroll_x > 0:
               content = self._slice_with_ansi(content, self.style.scroll_x)
           
           # Clip to width
           content = self._clip_to_width(content, content_width)
           
           # Pad to full width
           visible_len = self._strip_ansi_len(content)
           content += " " \* (content_width - visible_len)
       else:
           # Empty line
           content = " " \* content_width
       
       line += content
       
       # Add scrollbar indicator
       if show_scrollbar:
           scrollbar_char = self._get_scrollbar_char(
               local_line_idx,
               content_width,
               visible_start,
               self.content_height
           )
           line += f"{color}{scrollbar_char}{reset}"
       else:
           line += " "  # Right padding
       
       # Right border
       if self.style.border != BorderStyle.NONE:
           line += f"{color}{chars['v']}{reset}"
       
       return line
   
   def _render_bottom_border(self, chars: dict, content_width: int) -> str:
       """Render bottom border"""
       color = self.style.border_color or ""
       reset = "\\033[0m" if color else ""
       
       line = f"{color}{chars['bl']}"
       line += chars['h'] \* (content_width + 2)
       line += f"{chars['br']}{reset}"
       return line
   
   def _get_scrollbar_char(self, 
                          line_idx: int,
                          content_height: int,
                          scroll_offset: int,
                          total_height: int) -> str:
       """Calculate scrollbar character for this line"""
       if total_height <= content_height:
           return '│'
       
       # Calculate scrollbar position and size
       scrollbar_height = max(1, int(content_height \* content_height / total_height))
       scrollbar_start = int(scroll_offset \* content_height / total_height)
       scrollbar_end = scrollbar_start + scrollbar_height
       
       if scrollbar_start <= line_idx < scrollbar_end:
           return '█'  # Scrollbar thumb
       else:
           return '│'  # Scrollbar track
   
   def handle_key(self, key: str, state: Any) -> bool:
       """Handle scrolling keys"""
       if not self.style.scrollable:
           return False
       
       content_height = self.bounds.height - 2  # Minus borders
       max_scroll_y = max(0, self.content_height - content_height)
       max_scroll_x = max(0, self.content_width - (self.bounds.width - 2))
       
       if key == 'up':
           self.style.scroll_y = max(0, self.style.scroll_y - 1)
           return True
       elif key == 'down':
           self.style.scroll_y = min(max_scroll_y, self.style.scroll_y + 1)
           return True
       elif key == 'pageup':
           self.style.scroll_y = max(0, self.style.scroll_y - content_height)
           return True
       elif key == 'pagedown':
           self.style.scroll_y = min(max_scroll_y, self.style.scroll_y + content_height)
           return True
       elif key == 'home':
           self.style.scroll_y = 0
           return True
       elif key == 'end':
           self.style.scroll_y = max_scroll_y
           return True
       
       return False
   
   # Utility methods
   
   def _normalize_padding(self, padding) -> tuple[int, int, int, int]:
       """Convert padding to (top, right, bottom, left)"""
       if isinstance(padding, int):
           return (padding, padding, padding, padding)
       return padding
   
   def _strip_ansi_len(self, text: str) -> int:
       """Get visible length of text (excluding ANSI codes)"""
       import re
       ansi_escape = re.compile(r'\\x1b\\[[0-9;]\*m')
       return len(ansi_escape.sub('', text))
   
   def _clip_to_width(self, text: str, max_width: int) -> str:
       """Clip text to max_width, preserving ANSI codes"""
       import re
       
       ansi_escape = re.compile(r'(\\x1b\\[[0-9;]\*m)')
       parts = ansi_escape.split(text)
       
       result = []
       visible_count = 0
       
       for part in parts:
           if ansi_escape.match(part):
               # ANSI code - always include
               result.append(part)
           else:
               # Regular text - count and clip
               remaining = max_width - visible_count
               if remaining <= 0:
                   break
               
               if len(part) <= remaining:
                   result.append(part)
                   visible_count += len(part)
               else:
                   result.append(part[:remaining])
                   visible_count += remaining
                   break
       
       return ''.join(result)
   
   def _slice_with_ansi(self, text: str, start: int) -> str:
       """Slice text starting at position, preserving ANSI codes"""
       import re
       
       ansi_escape = re.compile(r'(\\x1b\\[[0-9;]\*m)')
       parts = ansi_escape.split(text)
       
       result = []
       visible_count = 0
       started = False
       
       for part in parts:
           if ansi_escape.match(part):
               # Keep ANSI codes once we've started
               if started or visible_count >= start:
                   result.append(part)
                   started = True
           else:
               # Regular text
               if visible_count + len(part) <= start:
                   # Skip this part entirely
                   visible_count += len(part)
               elif visible_count < start:
                   # Partial skip
                   skip_amount = start - visible_count
                   result.append(part[skip_amount:])
                   visible_count = start
                   started = True
               else:
                   # Include this part
                   result.append(part)
                   visible_count += len(part)
                   started = True
       
       return ''.join(result)

```



## Scroll State Management



```python

# wijjit/layout/scroll.py

from typing import Dict



class ScrollManager:
   """Manages scroll state across frames"""
   
   def __init__(self):
       self.scroll_states: Dict[str, tuple[int, int]] = {}  # frame_id -> (x, y)
       self.focused_frame: Optional[str] = None
   
   def get_scroll(self, frame_id: str) -> tuple[int, int]:
       """Get scroll offset for a frame"""
       return self.scroll_states.get(frame_id, (0, 0))
   
   def set_scroll(self, frame_id: str, x: int, y: int):
       """Set scroll offset for a frame"""
       self.scroll_states[frame_id] = (x, y)
   
   def scroll_up(self, frame_id: str, amount: int = 1):
       """Scroll frame up"""
       x, y = self.get_scroll(frame_id)
       self.set_scroll(frame_id, x, max(0, y - amount))
   
   def scroll_down(self, frame_id: str, amount: int, max_scroll: int):
       """Scroll frame down"""
       x, y = self.get_scroll(frame_id)
       self.set_scroll(frame_id, x, min(max_scroll, y + amount))
   
   def reset_scroll(self, frame_id: str):
       """Reset scroll to top"""
       self.scroll_states.pop(frame_id, None)

```



## Template Usage



```jinja

{# Various frame configurations #}



{# Simple frame with auto-sizing #}

{% frame id="header" border="single" %}
 Welcome to Wijjit!

{% endframe %}



{# Fixed size with scrolling #}

{% frame id="logs" 
        border="double" 
        height=20 
        overflow_y="scroll"
        title="Application Logs" %}
 {% for log in logs %}
   {{ log.timestamp }} - {{ log.message }}
 {% endfor %}

{% endframe %}



{# Fill available space #}

{% frame id="content" 
        border="rounded"
        width="fill"
        height="fill"
        padding=2
        overflow_y="auto" %}
 {{ main_content }}

{% endframe %}



{# No border, just padding and overflow #}

{% frame id="text" 
        border="none"
        padding=(1, 2, 1, 2)
        overflow_y="wrap" %}
 {{ long_text | wordwrap(60) }}

{% endframe %}



{# Colored border #}

{% frame id="error" 
        border="heavy"
        border_color="\\033[31m"  {# Red #}
        title="Error" %}
 Something went wrong!

{% endframe %}



{# Min/max constraints #}

{% frame id="sidebar"
        width="25%"
        min_width=20
        max_width=40
        fill=true %}
 Navigation menu

{% endframe %}

```



## Focus Integration



```python

# Update InputHandler to manage frame focus

class InputHandler:
   def __init__(self, app):
       self.app = app
       self.focused_element = None
       self.focused_frame = None  # Track which frame can scroll
   
   def process_input(self):
       key = self._read_key()
       
       # Try focused element first
       if self.focused_element:
           handled = self.focused_element.handle_key(key, self.app.state)
           if handled:
               self.app.renderer.render()
               return
       
       # Then try focused frame for scrolling
       if self.focused_frame and self.focused_frame.style.scrollable:
           handled = self.focused_frame.handle_key(key, self.app.state)
           if handled:
               self.app.renderer.render()
               return
       
       # Global shortcuts
       if key == 'ctrl+c':
           self.app.exit()

```



## Performance Optimization



```python

class Frame(Container):
   """Add virtual rendering for large content"""
   
   def __init__(self, id: str, style: FrameStyle):
       super().__init__(id)
       self.style = style
       self.content_lines: List[str] = []
       self._render_cache: Optional[str] = None
       self._cache_key: Optional[tuple] = None
   
   def render(self, state: Any) -> str:
       # Cache key includes scroll position and bounds
       cache_key = (
           self.bounds,
           self.style.scroll_x,
           self.style.scroll_y,
           len(self.content_lines)
       )
       
       if self._cache_key == cache_key and self._render_cache:
           return self._render_cache
       
       result = self._do_render(state)
       self._render_cache = result
       self._cache_key = cache_key
       
       return result

```



This gives us:

\- ✅ Multiple border styles

\- ✅ Flexible sizing (fixed, fill, percentages, auto)

\- ✅ Padding and margins

\- ✅ Overflow handling (clip, scroll, auto, wrap)

\- ✅ Scrollbar rendering

\- ✅ Title placement

\- ✅ ANSI-aware text clipping

\- ✅ Scroll state management

\- ✅ Performance caching



The key insight is treating frames as \*\*viewports\*\* into potentially larger content. When `overflow_y="scroll"`, the frame tracks its scroll offset and only renders the visible slice.



Want to tackle the layout calculation for splits and stacks next? That's where we'd handle the `hstack`, `vstack`, and `split` macros.

