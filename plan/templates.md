The templates become semantic rather than presentational:



```jinja

{% frame id="main" title="Editor" border="double" width="100%" height="100%" %}

&nbsp; 

&nbsp; {% frame id="header" height=3 %}

&nbsp;   File: {{ state.current\_file }}

&nbsp;   Modified: {{ state.modified\_time }}

&nbsp; {% endframe %}

&nbsp; 

&nbsp; {% frame id="content" fill=true padding=1 %}

&nbsp;   {% textbox id="editor" focusable=true %}

&nbsp;     {{ state.editor\_buffer }}

&nbsp;   {% endtextbox %}

&nbsp; {% endframe %}

&nbsp; 

&nbsp; {% frame id="footer" height=1 %}

&nbsp;   {% button id="save" %}Save{% endbutton %}

&nbsp;   {% button id="quit" %}Quit{% endbutton %}

&nbsp; {% endframe %}

&nbsp; 

{% endframe %}

```



The pre-renderer translates this to actual box-drawing characters and calculates all dimensions:



```

╔══ Editor ══════════════════╗

║ File: config.py            ║

║ Modified: 2m ago           ║

╟────────────────────────────╢

║                            ║

║  def main():              ║

║      print("hello")       ║

║                            ║

╟────────────────────────────╢

║ \[Save] \[Quit]              ║

╚════════════════════════════╝

```



\## Built-in Macros



\*\*Frames with different styles:\*\*

```jinja

{% frame border="single" %}  {# ┌─┐ │ └─┘ #}

{% frame border="double" %}  {# ╔═╗ ║ ╚═╝ #}

{% frame border="rounded" %} {# ╭─╮ │ ╰─╯ #}

{% frame border="heavy" %}   {# ┏━┓ ┃ ┗━┛ #}

{% frame border="none" %}    {# no border, just spacing #}

```



\*\*Layout helpers:\*\*

```jinja

{% hstack spacing=2 %}

&nbsp; {{ button("OK") }}

&nbsp; {{ button("Cancel") }}

{% endhstack %}



{% vstack fill=true %}

&nbsp; {% for item in items %}

&nbsp;   {{ list\_item(item) }}

&nbsp; {% endfor %}

{% endvstack %}



{% split direction="horizontal" ratio="30:70" %}

&nbsp; {% left %}

&nbsp;   {# Sidebar #}

&nbsp; {% endleft %}

&nbsp; {% right %}

&nbsp;   {# Main content #}

&nbsp; {% endright %}

{% endsplit %}

```



\*\*Composite widgets:\*\*

```jinja

{% table id="results" headers=\["Name", "Size", "Modified"] %}

&nbsp; {% for file in files %}

&nbsp;   {% row focusable=true data=file %}

&nbsp;     {{ file.name }}

&nbsp;     {{ file.size | humanize }}

&nbsp;     {{ file.modified | timeago }}

&nbsp;   {% endrow %}

&nbsp; {% endfor %}

{% endtable %}



{% menu id="actions" %}

&nbsp; {% item key="o" %}Open{% enditem %}

&nbsp; {% item key="d" %}Delete{% enditem %}

&nbsp; {% item key="r" %}Rename{% enditem %}

&nbsp; {% separator %}

&nbsp; {% item key="q" %}Quit{% enditem %}

{% endmenu %}

```



\## Smart Sizing



The frame macro handles sizing logic:



```python

class Frame:

&nbsp;   def calculate\_dimensions(self, available\_width, available\_height):

&nbsp;       # Explicit dimensions

&nbsp;       if self.width == "100%" or self.width == "fill":

&nbsp;           self.actual\_width = available\_width

&nbsp;       elif isinstance(self.width, int):

&nbsp;           self.actual\_width = self.width

&nbsp;       else:  # "auto"

&nbsp;           # Calculate based on content

&nbsp;           self.actual\_width = max(child.min\_width for child in children) + padding

&nbsp;       

&nbsp;       # Border takes 2 chars from width

&nbsp;       if self.border != "none":

&nbsp;           self.actual\_width += 2

&nbsp;           self.actual\_height += 2

&nbsp;       

&nbsp;       # Distribute remaining space to fill children

&nbsp;       fill\_children = \[c for c in self.children if c.fill]

&nbsp;       if fill\_children:

&nbsp;           remaining = self.actual\_height - sum(c.height for c in fixed\_children)

&nbsp;           per\_child = remaining // len(fill\_children)

&nbsp;           for child in fill\_children:

&nbsp;               child.height = per\_child

```



\## Composition Example



A complete file manager TUI:



```jinja

{% frame title="File Manager" border="double" width="100%" height="100%" %}

&nbsp; 

&nbsp; {% split direction="horizontal" ratio="25:75" %}

&nbsp;   

&nbsp;   {% left %}

&nbsp;     {% frame title="Folders" border="single" fill=true %}

&nbsp;       {% tree id="folders" focusable=true %}

&nbsp;         {{ folder\_tree }}

&nbsp;       {% endtree %}

&nbsp;     {% endframe %}

&nbsp;   {% endleft %}

&nbsp;   

&nbsp;   {% right %}

&nbsp;     {% vstack fill=true %}

&nbsp;       

&nbsp;       {% frame id="breadcrumb" height=3 %}

&nbsp;         Path: {{ current\_path }}

&nbsp;       {% endframe %}

&nbsp;       

&nbsp;       {% frame title="Files" fill=true %}

&nbsp;         {% table id="files" focusable=true selectable=true %}

&nbsp;           {% for file in files %}

&nbsp;             {% row data=file %}

&nbsp;               {{ file.icon }} {{ file.name }}

&nbsp;               {{ file.size | humanize }}

&nbsp;               {{ file.modified | timeago }}

&nbsp;             {% endrow %}

&nbsp;           {% endfor %}

&nbsp;         {% endtable %}

&nbsp;       {% endframe %}

&nbsp;       

&nbsp;       {% frame id="statusbar" height=1 %}

&nbsp;         {{ files|length }} items | {{ selected|length }} selected

&nbsp;       {% endframe %}

&nbsp;       

&nbsp;     {% endvstack %}

&nbsp;   {% endright %}

&nbsp;   

&nbsp; {% endsplit %}

&nbsp; 

{% endframe %}

```



\## Implementation Details



The pre-renderer walks the AST:



```python

class LayoutEngine:

&nbsp;   def prepare(self, template\_ast, width, height):

&nbsp;       # Parse custom tags

&nbsp;       root = self.parse\_frames(template\_ast)

&nbsp;       

&nbsp;       # Calculate dimensions bottom-up

&nbsp;       root.calculate\_dimensions(width, height)

&nbsp;       

&nbsp;       # Assign absolute positions top-down

&nbsp;       root.assign\_positions(0, 0)

&nbsp;       

&nbsp;       # Generate box-drawing characters

&nbsp;       rendered = root.render\_borders()

&nbsp;       

&nbsp;       # Create coordinate map for focusable elements

&nbsp;       self.focus\_map = root.collect\_focusable()

&nbsp;       

&nbsp;       return rendered

```



This gives you \*\*responsive layouts\*\* where resizing the terminal automatically recalculates everything. And the templates stay clean and semantic - you're describing \*what\* the UI is, not \*how\* to draw it.

