Perfect! Frame rendering is where the magic happens. Let's design this comprehensively.



\## Frame Attributes



```python

\# wijjit/layout/frames.py

from dataclasses import dataclass

from typing import Optional, Literal

from enum import Enum



class BorderStyle(Enum):

&nbsp;   NONE = "none"

&nbsp;   SINGLE = "single"    # ┌─┐│└─┘

&nbsp;   DOUBLE = "double"    # ╔═╗║╚═╝

&nbsp;   ROUNDED = "rounded"  # ╭─╮│╰─╯

&nbsp;   HEAVY = "heavy"      # ┏━┓┃┗━┛

&nbsp;   DASHED = "dashed"    # ┌╌┐╎└╌┘



class Overflow(Enum):

&nbsp;   CLIP = "clip"        # Cut off content

&nbsp;   SCROLL = "scroll"    # Always show scrollbar

&nbsp;   AUTO = "auto"        # Scrollbar if needed

&nbsp;   WRAP = "wrap"        # Wrap text content



@dataclass

class FrameStyle:

&nbsp;   # Border

&nbsp;   border: BorderStyle = BorderStyle.SINGLE

&nbsp;   border\_color: Optional\[str] = None  # ANSI color code

&nbsp;   

&nbsp;   # Size

&nbsp;   width: int | str = "auto"  # int, "auto", "fill", "100%", "50%"

&nbsp;   height: int | str = "auto"

&nbsp;   min\_width: Optional\[int] = None

&nbsp;   max\_width: Optional\[int] = None

&nbsp;   min\_height: Optional\[int] = None

&nbsp;   max\_height: Optional\[int] = None

&nbsp;   

&nbsp;   # Spacing

&nbsp;   padding: int | tuple\[int, int, int, int] = 0  # top, right, bottom, left

&nbsp;   margin: int | tuple\[int, int, int, int] = 0

&nbsp;   

&nbsp;   # Content

&nbsp;   title: Optional\[str] = None

&nbsp;   title\_align: Literal\["left", "center", "right"] = "left"

&nbsp;   overflow\_x: Overflow = Overflow.CLIP

&nbsp;   overflow\_y: Overflow = Overflow.AUTO

&nbsp;   

&nbsp;   # Scrolling

&nbsp;   scrollable: bool = True  # Can this frame be scrolled with arrow keys

&nbsp;   scroll\_x: int = 0  # Current horizontal scroll offset

&nbsp;   scroll\_y: int = 0  # Current vertical scroll offset



\# Border character sets

BORDER\_CHARS = {

&nbsp;   BorderStyle.SINGLE: {

&nbsp;       'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',

&nbsp;       'h': '─', 'v': '│',

&nbsp;       't': '┬', 'b': '┴', 'l': '├', 'r': '┤',

&nbsp;       'cross': '┼'

&nbsp;   },

&nbsp;   BorderStyle.DOUBLE: {

&nbsp;       'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝',

&nbsp;       'h': '═', 'v': '║',

&nbsp;       't': '╦', 'b': '╩', 'l': '╠', 'r': '╣',

&nbsp;       'cross': '╬'

&nbsp;   },

&nbsp;   BorderStyle.ROUNDED: {

&nbsp;       'tl': '╭', 'tr': '╮', 'bl': '╰', 'br': '╯',

&nbsp;       'h': '─', 'v': '│',

&nbsp;       't': '┬', 'b': '┴', 'l': '├', 'r': '┤',

&nbsp;       'cross': '┼'

&nbsp;   },

&nbsp;   BorderStyle.HEAVY: {

&nbsp;       'tl': '┏', 'tr': '┓', 'bl': '┗', 'br': '┛',

&nbsp;       'h': '━', 'v': '┃',

&nbsp;       't': '┳', 'b': '┻', 'l': '┣', 'r': '┫',

&nbsp;       'cross': '╋'

&nbsp;   },

&nbsp;   BorderStyle.DASHED: {

&nbsp;       'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',

&nbsp;       'h': '╌', 'v': '╎',

&nbsp;       't': '┬', 'b': '┴', 'l': '├', 'r': '┤',

&nbsp;       'cross': '┼'

&nbsp;   }

}

```



\## Frame Class



```python

class Frame(Container):

&nbsp;   """A bordered container with overflow/scroll handling"""

&nbsp;   

&nbsp;   def \_\_init\_\_(self, id: str, style: FrameStyle):

&nbsp;       super().\_\_init\_\_(id)

&nbsp;       self.style = style

&nbsp;       self.content\_lines: List\[str] = \[]

&nbsp;       self.content\_height = 0  # Actual content height

&nbsp;       self.content\_width = 0   # Actual content width

&nbsp;       self.focused\_child: Optional\[Element] = None

&nbsp;   

&nbsp;   def set\_content(self, content: str):

&nbsp;       """Set the raw content for this frame"""

&nbsp;       self.content\_lines = content.split('\\n')

&nbsp;       self.content\_height = len(self.content\_lines)

&nbsp;       self.content\_width = max(self.\_strip\_ansi\_len(line) 

&nbsp;                               for line in self.content\_lines) if self.content\_lines else 0

&nbsp;   

&nbsp;   def render(self, state: Any) -> str:

&nbsp;       """Render frame with borders, padding, and scroll handling"""

&nbsp;       if not self.bounds:

&nbsp;           return ""

&nbsp;       

&nbsp;       lines = \[]

&nbsp;       chars = BORDER\_CHARS.get(self.style.border, BORDER\_CHARS\[BorderStyle.SINGLE])

&nbsp;       

&nbsp;       # Apply padding

&nbsp;       padding = self.\_normalize\_padding(self.style.padding)

&nbsp;       pad\_top, pad\_right, pad\_bottom, pad\_left = padding

&nbsp;       

&nbsp;       # Calculate content area (inside border and padding)

&nbsp;       border\_width = 0 if self.style.border == BorderStyle.NONE else 2

&nbsp;       content\_width = self.bounds.width - border\_width - pad\_left - pad\_right

&nbsp;       content\_height = self.bounds.height - border\_width - pad\_top - pad\_bottom

&nbsp;       

&nbsp;       # Check if scrolling is needed

&nbsp;       needs\_scroll\_y = self.content\_height > content\_height

&nbsp;       needs\_scroll\_x = self.content\_width > content\_width

&nbsp;       

&nbsp;       # Adjust for scrollbar space

&nbsp;       if needs\_scroll\_y and self.style.overflow\_y != Overflow.CLIP:

&nbsp;           content\_width -= 1  # Reserve space for scrollbar

&nbsp;       

&nbsp;       # Render top border

&nbsp;       if self.style.border != BorderStyle.NONE:

&nbsp;           top\_line = self.\_render\_top\_border(chars, content\_width)

&nbsp;           lines.append(top\_line)

&nbsp;       

&nbsp;       # Render content lines with padding and scrolling

&nbsp;       visible\_start\_y = self.style.scroll\_y

&nbsp;       visible\_end\_y = visible\_start\_y + content\_height

&nbsp;       

&nbsp;       for i in range(content\_height):

&nbsp;           line = self.\_render\_content\_line(

&nbsp;               i, 

&nbsp;               visible\_start\_y, 

&nbsp;               visible\_end\_y,

&nbsp;               content\_width,

&nbsp;               pad\_left,

&nbsp;               chars,

&nbsp;               needs\_scroll\_y

&nbsp;           )

&nbsp;           lines.append(line)

&nbsp;       

&nbsp;       # Render bottom border

&nbsp;       if self.style.border != BorderStyle.NONE:

&nbsp;           bottom\_line = self.\_render\_bottom\_border(chars, content\_width)

&nbsp;           lines.append(bottom\_line)

&nbsp;       

&nbsp;       return '\\n'.join(lines)

&nbsp;   

&nbsp;   def \_render\_top\_border(self, chars: dict, content\_width: int) -> str:

&nbsp;       """Render top border with title"""

&nbsp;       color = self.style.border\_color or ""

&nbsp;       reset = "\\033\[0m" if color else ""

&nbsp;       

&nbsp;       # Start with top-left corner

&nbsp;       line = f"{color}{chars\['tl']}"

&nbsp;       

&nbsp;       # Add title if present

&nbsp;       if self.style.title:

&nbsp;           title = f" {self.style.title} "

&nbsp;           title\_len = len(title)

&nbsp;           

&nbsp;           if self.style.title\_align == "left":

&nbsp;               line += title

&nbsp;               line += chars\['h'] \* (content\_width + 2 - title\_len)

&nbsp;           elif self.style.title\_align == "center":

&nbsp;               left\_pad = (content\_width + 2 - title\_len) // 2

&nbsp;               right\_pad = content\_width + 2 - title\_len - left\_pad

&nbsp;               line += chars\['h'] \* left\_pad + title + chars\['h'] \* right\_pad

&nbsp;           else:  # right

&nbsp;               line += chars\['h'] \* (content\_width + 2 - title\_len)

&nbsp;               line += title

&nbsp;       else:

&nbsp;           line += chars\['h'] \* (content\_width + 2)

&nbsp;       

&nbsp;       # Top-right corner

&nbsp;       line += f"{chars\['tr']}{reset}"

&nbsp;       return line

&nbsp;   

&nbsp;   def \_render\_content\_line(self, 

&nbsp;                           local\_line\_idx: int,

&nbsp;                           visible\_start: int,

&nbsp;                           visible\_end: int,

&nbsp;                           content\_width: int,

&nbsp;                           pad\_left: int,

&nbsp;                           chars: dict,

&nbsp;                           show\_scrollbar: bool) -> str:

&nbsp;       """Render a single content line with clipping/scrolling"""

&nbsp;       color = self.style.border\_color or ""

&nbsp;       reset = "\\033\[0m" if color else ""

&nbsp;       

&nbsp;       # Start with left border

&nbsp;       if self.style.border != BorderStyle.NONE:

&nbsp;           line = f"{color}{chars\['v']}{reset}"

&nbsp;       else:

&nbsp;           line = ""

&nbsp;       

&nbsp;       # Add left padding

&nbsp;       line += " " \* pad\_left

&nbsp;       

&nbsp;       # Get content line (accounting for scroll)

&nbsp;       content\_line\_idx = visible\_start + local\_line\_idx

&nbsp;       

&nbsp;       if 0 <= content\_line\_idx < len(self.content\_lines):

&nbsp;           content = self.content\_lines\[content\_line\_idx]

&nbsp;           

&nbsp;           # Apply horizontal scroll

&nbsp;           if self.style.scroll\_x > 0:

&nbsp;               content = self.\_slice\_with\_ansi(content, self.style.scroll\_x)

&nbsp;           

&nbsp;           # Clip to width

&nbsp;           content = self.\_clip\_to\_width(content, content\_width)

&nbsp;           

&nbsp;           # Pad to full width

&nbsp;           visible\_len = self.\_strip\_ansi\_len(content)

&nbsp;           content += " " \* (content\_width - visible\_len)

&nbsp;       else:

&nbsp;           # Empty line

&nbsp;           content = " " \* content\_width

&nbsp;       

&nbsp;       line += content

&nbsp;       

&nbsp;       # Add scrollbar indicator

&nbsp;       if show\_scrollbar:

&nbsp;           scrollbar\_char = self.\_get\_scrollbar\_char(

&nbsp;               local\_line\_idx,

&nbsp;               content\_width,

&nbsp;               visible\_start,

&nbsp;               self.content\_height

&nbsp;           )

&nbsp;           line += f"{color}{scrollbar\_char}{reset}"

&nbsp;       else:

&nbsp;           line += " "  # Right padding

&nbsp;       

&nbsp;       # Right border

&nbsp;       if self.style.border != BorderStyle.NONE:

&nbsp;           line += f"{color}{chars\['v']}{reset}"

&nbsp;       

&nbsp;       return line

&nbsp;   

&nbsp;   def \_render\_bottom\_border(self, chars: dict, content\_width: int) -> str:

&nbsp;       """Render bottom border"""

&nbsp;       color = self.style.border\_color or ""

&nbsp;       reset = "\\033\[0m" if color else ""

&nbsp;       

&nbsp;       line = f"{color}{chars\['bl']}"

&nbsp;       line += chars\['h'] \* (content\_width + 2)

&nbsp;       line += f"{chars\['br']}{reset}"

&nbsp;       return line

&nbsp;   

&nbsp;   def \_get\_scrollbar\_char(self, 

&nbsp;                          line\_idx: int,

&nbsp;                          content\_height: int,

&nbsp;                          scroll\_offset: int,

&nbsp;                          total\_height: int) -> str:

&nbsp;       """Calculate scrollbar character for this line"""

&nbsp;       if total\_height <= content\_height:

&nbsp;           return '│'

&nbsp;       

&nbsp;       # Calculate scrollbar position and size

&nbsp;       scrollbar\_height = max(1, int(content\_height \* content\_height / total\_height))

&nbsp;       scrollbar\_start = int(scroll\_offset \* content\_height / total\_height)

&nbsp;       scrollbar\_end = scrollbar\_start + scrollbar\_height

&nbsp;       

&nbsp;       if scrollbar\_start <= line\_idx < scrollbar\_end:

&nbsp;           return '█'  # Scrollbar thumb

&nbsp;       else:

&nbsp;           return '│'  # Scrollbar track

&nbsp;   

&nbsp;   def handle\_key(self, key: str, state: Any) -> bool:

&nbsp;       """Handle scrolling keys"""

&nbsp;       if not self.style.scrollable:

&nbsp;           return False

&nbsp;       

&nbsp;       content\_height = self.bounds.height - 2  # Minus borders

&nbsp;       max\_scroll\_y = max(0, self.content\_height - content\_height)

&nbsp;       max\_scroll\_x = max(0, self.content\_width - (self.bounds.width - 2))

&nbsp;       

&nbsp;       if key == 'up':

&nbsp;           self.style.scroll\_y = max(0, self.style.scroll\_y - 1)

&nbsp;           return True

&nbsp;       elif key == 'down':

&nbsp;           self.style.scroll\_y = min(max\_scroll\_y, self.style.scroll\_y + 1)

&nbsp;           return True

&nbsp;       elif key == 'pageup':

&nbsp;           self.style.scroll\_y = max(0, self.style.scroll\_y - content\_height)

&nbsp;           return True

&nbsp;       elif key == 'pagedown':

&nbsp;           self.style.scroll\_y = min(max\_scroll\_y, self.style.scroll\_y + content\_height)

&nbsp;           return True

&nbsp;       elif key == 'home':

&nbsp;           self.style.scroll\_y = 0

&nbsp;           return True

&nbsp;       elif key == 'end':

&nbsp;           self.style.scroll\_y = max\_scroll\_y

&nbsp;           return True

&nbsp;       

&nbsp;       return False

&nbsp;   

&nbsp;   # Utility methods

&nbsp;   

&nbsp;   def \_normalize\_padding(self, padding) -> tuple\[int, int, int, int]:

&nbsp;       """Convert padding to (top, right, bottom, left)"""

&nbsp;       if isinstance(padding, int):

&nbsp;           return (padding, padding, padding, padding)

&nbsp;       return padding

&nbsp;   

&nbsp;   def \_strip\_ansi\_len(self, text: str) -> int:

&nbsp;       """Get visible length of text (excluding ANSI codes)"""

&nbsp;       import re

&nbsp;       ansi\_escape = re.compile(r'\\x1b\\\[\[0-9;]\*m')

&nbsp;       return len(ansi\_escape.sub('', text))

&nbsp;   

&nbsp;   def \_clip\_to\_width(self, text: str, max\_width: int) -> str:

&nbsp;       """Clip text to max\_width, preserving ANSI codes"""

&nbsp;       import re

&nbsp;       

&nbsp;       ansi\_escape = re.compile(r'(\\x1b\\\[\[0-9;]\*m)')

&nbsp;       parts = ansi\_escape.split(text)

&nbsp;       

&nbsp;       result = \[]

&nbsp;       visible\_count = 0

&nbsp;       

&nbsp;       for part in parts:

&nbsp;           if ansi\_escape.match(part):

&nbsp;               # ANSI code - always include

&nbsp;               result.append(part)

&nbsp;           else:

&nbsp;               # Regular text - count and clip

&nbsp;               remaining = max\_width - visible\_count

&nbsp;               if remaining <= 0:

&nbsp;                   break

&nbsp;               

&nbsp;               if len(part) <= remaining:

&nbsp;                   result.append(part)

&nbsp;                   visible\_count += len(part)

&nbsp;               else:

&nbsp;                   result.append(part\[:remaining])

&nbsp;                   visible\_count += remaining

&nbsp;                   break

&nbsp;       

&nbsp;       return ''.join(result)

&nbsp;   

&nbsp;   def \_slice\_with\_ansi(self, text: str, start: int) -> str:

&nbsp;       """Slice text starting at position, preserving ANSI codes"""

&nbsp;       import re

&nbsp;       

&nbsp;       ansi\_escape = re.compile(r'(\\x1b\\\[\[0-9;]\*m)')

&nbsp;       parts = ansi\_escape.split(text)

&nbsp;       

&nbsp;       result = \[]

&nbsp;       visible\_count = 0

&nbsp;       started = False

&nbsp;       

&nbsp;       for part in parts:

&nbsp;           if ansi\_escape.match(part):

&nbsp;               # Keep ANSI codes once we've started

&nbsp;               if started or visible\_count >= start:

&nbsp;                   result.append(part)

&nbsp;                   started = True

&nbsp;           else:

&nbsp;               # Regular text

&nbsp;               if visible\_count + len(part) <= start:

&nbsp;                   # Skip this part entirely

&nbsp;                   visible\_count += len(part)

&nbsp;               elif visible\_count < start:

&nbsp;                   # Partial skip

&nbsp;                   skip\_amount = start - visible\_count

&nbsp;                   result.append(part\[skip\_amount:])

&nbsp;                   visible\_count = start

&nbsp;                   started = True

&nbsp;               else:

&nbsp;                   # Include this part

&nbsp;                   result.append(part)

&nbsp;                   visible\_count += len(part)

&nbsp;                   started = True

&nbsp;       

&nbsp;       return ''.join(result)

```



\## Scroll State Management



```python

\# wijjit/layout/scroll.py

from typing import Dict



class ScrollManager:

&nbsp;   """Manages scroll state across frames"""

&nbsp;   

&nbsp;   def \_\_init\_\_(self):

&nbsp;       self.scroll\_states: Dict\[str, tuple\[int, int]] = {}  # frame\_id -> (x, y)

&nbsp;       self.focused\_frame: Optional\[str] = None

&nbsp;   

&nbsp;   def get\_scroll(self, frame\_id: str) -> tuple\[int, int]:

&nbsp;       """Get scroll offset for a frame"""

&nbsp;       return self.scroll\_states.get(frame\_id, (0, 0))

&nbsp;   

&nbsp;   def set\_scroll(self, frame\_id: str, x: int, y: int):

&nbsp;       """Set scroll offset for a frame"""

&nbsp;       self.scroll\_states\[frame\_id] = (x, y)

&nbsp;   

&nbsp;   def scroll\_up(self, frame\_id: str, amount: int = 1):

&nbsp;       """Scroll frame up"""

&nbsp;       x, y = self.get\_scroll(frame\_id)

&nbsp;       self.set\_scroll(frame\_id, x, max(0, y - amount))

&nbsp;   

&nbsp;   def scroll\_down(self, frame\_id: str, amount: int, max\_scroll: int):

&nbsp;       """Scroll frame down"""

&nbsp;       x, y = self.get\_scroll(frame\_id)

&nbsp;       self.set\_scroll(frame\_id, x, min(max\_scroll, y + amount))

&nbsp;   

&nbsp;   def reset\_scroll(self, frame\_id: str):

&nbsp;       """Reset scroll to top"""

&nbsp;       self.scroll\_states.pop(frame\_id, None)

```



\## Template Usage



```jinja

{# Various frame configurations #}



{# Simple frame with auto-sizing #}

{% frame id="header" border="single" %}

&nbsp; Welcome to Wijjit!

{% endframe %}



{# Fixed size with scrolling #}

{% frame id="logs" 

&nbsp;        border="double" 

&nbsp;        height=20 

&nbsp;        overflow\_y="scroll"

&nbsp;        title="Application Logs" %}

&nbsp; {% for log in logs %}

&nbsp;   {{ log.timestamp }} - {{ log.message }}

&nbsp; {% endfor %}

{% endframe %}



{# Fill available space #}

{% frame id="content" 

&nbsp;        border="rounded"

&nbsp;        width="fill"

&nbsp;        height="fill"

&nbsp;        padding=2

&nbsp;        overflow\_y="auto" %}

&nbsp; {{ main\_content }}

{% endframe %}



{# No border, just padding and overflow #}

{% frame id="text" 

&nbsp;        border="none"

&nbsp;        padding=(1, 2, 1, 2)

&nbsp;        overflow\_y="wrap" %}

&nbsp; {{ long\_text | wordwrap(60) }}

{% endframe %}



{# Colored border #}

{% frame id="error" 

&nbsp;        border="heavy"

&nbsp;        border\_color="\\033\[31m"  {# Red #}

&nbsp;        title="Error" %}

&nbsp; Something went wrong!

{% endframe %}



{# Min/max constraints #}

{% frame id="sidebar"

&nbsp;        width="25%"

&nbsp;        min\_width=20

&nbsp;        max\_width=40

&nbsp;        fill=true %}

&nbsp; Navigation menu

{% endframe %}

```



\## Focus Integration



```python

\# Update InputHandler to manage frame focus

class InputHandler:

&nbsp;   def \_\_init\_\_(self, app):

&nbsp;       self.app = app

&nbsp;       self.focused\_element = None

&nbsp;       self.focused\_frame = None  # Track which frame can scroll

&nbsp;   

&nbsp;   def process\_input(self):

&nbsp;       key = self.\_read\_key()

&nbsp;       

&nbsp;       # Try focused element first

&nbsp;       if self.focused\_element:

&nbsp;           handled = self.focused\_element.handle\_key(key, self.app.state)

&nbsp;           if handled:

&nbsp;               self.app.renderer.render()

&nbsp;               return

&nbsp;       

&nbsp;       # Then try focused frame for scrolling

&nbsp;       if self.focused\_frame and self.focused\_frame.style.scrollable:

&nbsp;           handled = self.focused\_frame.handle\_key(key, self.app.state)

&nbsp;           if handled:

&nbsp;               self.app.renderer.render()

&nbsp;               return

&nbsp;       

&nbsp;       # Global shortcuts

&nbsp;       if key == 'ctrl+c':

&nbsp;           self.app.exit()

```



\## Performance Optimization



```python

class Frame(Container):

&nbsp;   """Add virtual rendering for large content"""

&nbsp;   

&nbsp;   def \_\_init\_\_(self, id: str, style: FrameStyle):

&nbsp;       super().\_\_init\_\_(id)

&nbsp;       self.style = style

&nbsp;       self.content\_lines: List\[str] = \[]

&nbsp;       self.\_render\_cache: Optional\[str] = None

&nbsp;       self.\_cache\_key: Optional\[tuple] = None

&nbsp;   

&nbsp;   def render(self, state: Any) -> str:

&nbsp;       # Cache key includes scroll position and bounds

&nbsp;       cache\_key = (

&nbsp;           self.bounds,

&nbsp;           self.style.scroll\_x,

&nbsp;           self.style.scroll\_y,

&nbsp;           len(self.content\_lines)

&nbsp;       )

&nbsp;       

&nbsp;       if self.\_cache\_key == cache\_key and self.\_render\_cache:

&nbsp;           return self.\_render\_cache

&nbsp;       

&nbsp;       result = self.\_do\_render(state)

&nbsp;       self.\_render\_cache = result

&nbsp;       self.\_cache\_key = cache\_key

&nbsp;       

&nbsp;       return result

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



The key insight is treating frames as \*\*viewports\*\* into potentially larger content. When `overflow\_y="scroll"`, the frame tracks its scroll offset and only renders the visible slice.



Want to tackle the layout calculation for splits and stacks next? That's where we'd handle the `hstack`, `vstack`, and `split` macros.

