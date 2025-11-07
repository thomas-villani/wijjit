The templates become semantic rather than presentational:



```jinja

{% frame id="main" title="Editor" border="double" width="100%" height="100%" %}

{% frame id="header" height=3 %}
  File: {{ state.current\_file }}
  Modified: {{ state.modified\_time }}
{% endframe %}

{% frame id="content" fill=true padding=1 %}
  {% textbox id="editor" focusable=true %}
    {{ state.editor\_buffer }}
  {% endtextbox %}
{% endframe %}

{% frame id="footer" height=1 %}
  {% button id="save" %}Save{% endbutton %}
  {% button id="quit" %}Quit{% endbutton %}
{% endframe %}


{% endframe %}

```



The pre-renderer translates this to actual box-drawing characters and calculates all dimensions:



```

╔══ Editor ══════════════════╗
║ File: config.py            ║
║ Modified: 2m ago           ║
╟────────────────────────────╢
║                            ║
║  def main():               ║
║      print("hello")        ║
║                            ║
╟────────────────────────────╢
║ \[Save] \[Quit]            ║
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
{{ button("OK") }}
{{ button("Cancel") }}

{% endhstack %}



{% vstack fill=true %}
{% for item in items %}
  {{ list\_item(item) }}
{% endfor %}

{% endvstack %}



{% split direction="horizontal" ratio="30:70" %}
{% left %}
  {# Sidebar #}
{% endleft %}
{% right %}
  {# Main content #}
{% endright %}

{% endsplit %}

```



\*\*Composite widgets:\*\*

```jinja

{% table id="results" headers=\["Name", "Size", "Modified"] %}
{% for file in files %}
  {% row focusable=true data=file %}
    {{ file.name }}
    {{ file.size | humanize }}
    {{ file.modified | timeago }}
  {% endrow %}
{% endfor %}

{% endtable %}



{% menu id="actions" %}
{% item key="o" %}Open{% enditem %}
{% item key="d" %}Delete{% enditem %}
{% item key="r" %}Rename{% enditem %}
{% separator %}
{% item key="q" %}Quit{% enditem %}

{% endmenu %}

```



\## Smart Sizing



The frame macro handles sizing logic:



```python

class Frame:
  def calculate\_dimensions(self, available\_width, available\_height):
      # Explicit dimensions
      if self.width == "100%" or self.width == "fill":
          self.actual\_width = available\_width
      elif isinstance(self.width, int):
          self.actual\_width = self.width
      else:  # "auto"
          # Calculate based on content
          self.actual\_width = max(child.min\_width for child in children) + padding
      
      # Border takes 2 chars from width
      if self.border != "none":
          self.actual\_width += 2
          self.actual\_height += 2
      
      # Distribute remaining space to fill children
      fill\_children = \[c for c in self.children if c.fill]
      if fill\_children:
          remaining = self.actual\_height - sum(c.height for c in fixed\_children)
          per\_child = remaining // len(fill\_children)
          for child in fill\_children:
              child.height = per\_child

```



\## Composition Example



A complete file manager TUI:



```jinja

{% frame title="File Manager" border="double" width="100%" height="100%" %}

{% split direction="horizontal" ratio="25:75" %}
  
  {% left %}
    {% frame title="Folders" border="single" fill=true %}
      {% tree id="folders" focusable=true %}
        {{ folder\_tree }}
      {% endtree %}
    {% endframe %}
  {% endleft %}
  
  {% right %}
    {% vstack fill=true %}
      
      {% frame id="breadcrumb" height=3 %}
        Path: {{ current\_path }}
      {% endframe %}
      
      {% frame title="Files" fill=true %}
        {% table id="files" focusable=true selectable=true %}
          {% for file in files %}
            {% row data=file %}
              {{ file.icon }} {{ file.name }}
              {{ file.size | humanize }}
              {{ file.modified | timeago }}
            {% endrow %}
          {% endfor %}
        {% endtable %}
      {% endframe %}
      
      {% frame id="statusbar" height=1 %}
        {{ files|length }} items | {{ selected|length }} selected
      {% endframe %}
      
    {% endvstack %}
  {% endright %}
  
{% endsplit %}


{% endframe %}

```



\## Implementation Details



The pre-renderer walks the AST:



```python

class LayoutEngine:
  def prepare(self, template\_ast, width, height):
      # Parse custom tags
      root = self.parse\_frames(template\_ast)
      
      # Calculate dimensions bottom-up
      root.calculate\_dimensions(width, height)
      
      # Assign absolute positions top-down
      root.assign\_positions(0, 0)
      
      # Generate box-drawing characters
      rendered = root.render\_borders()
      
      # Create coordinate map for focusable elements
      self.focus\_map = root.collect\_focusable()
      
      return rendered

```



This gives you \*\*responsive layouts\*\* where resizing the terminal automatically recalculates everything. And the templates stay clean and semantic - you're describing \*what\* the UI is, not \*how\* to draw it.

