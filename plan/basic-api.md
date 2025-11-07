

\## View Decorators



```python

from wijjit import Wijjit, view, state



app = Wijjit()



@app.view('main', default=True)

def main\_view():
   return {
       'template': 'main.tui',
       'data': {
           'files': state.files,
           'current\_path': state.current\_path,
       },
       'handlers': {
           'open\_file': lambda file: open\_file\_handler(file),
           'show\_config': lambda: app.navigate('config'),
           'quit': lambda: app.exit(),
       }
   }



@app.view('config')

def config\_view():
   return {
       'template': 'config.tui',
       'data': {
           'server': state.config.server,
           'port': state.config.port,
       },
       'handlers': {
           'save': save\_config,
           'cancel': lambda: app.navigate('main'),
       },
       'on\_enter': lambda: state.view\_context.update({'editing': False}),
       'on\_exit': lambda: validate\_config(),
   }



@app.view('confirm\_delete')

def confirm\_delete\_view(item):
   """Views can take parameters"""
   return {
       'template': 'confirm.tui',
       'data': {'item': item},
       'handlers': {
           'yes': lambda: delete\_item(item) or app.navigate('main'),
           'no': lambda: app.navigate('main'),
       }
   }

```



\## Navigation in Templates



```jinja

{% frame title="Main Menu" %}
 
 {% menu id="main\_menu" %}
   {% item key="f" action="browse\_files" %}Browse Files{% enditem %}
   {% item key="c" navigate="config" %}Configuration{% enditem %}
   {% item key="s" navigate="search" %}Search{% enditem %}
   {% item key="q" action="quit" %}Quit{% enditem %}
 {% endmenu %}
 

{% endframe %}

```



Or programmatically from handlers:



```python

def on\_file\_select(file):
   if file.is\_dir:
       state.current\_path = file.path
       # Stay on same view, triggers re-render
   else:
       # Navigate to editor view with parameter
       app.navigate('editor', file=file)

```



\## Pre-built Element Library



\*\*Input Elements:\*\*

```python

\# Text input

{% textinput id="username" 
            placeholder="Enter username"
            value=state.username
            on\_change="update\_username"
            validate=username\_validator %}



\# Password input

{% textinput id="password" type="password" %}



\# Number input with validation

{% numberinput id="port" 
              min=1024 
              max=65535 
              value=state.port %}



\# Select/dropdown

{% select id="theme" 
         options=\["dark", "light", "auto"]
         selected=state.theme
         on\_select="change\_theme" %}



\# Multi-select

{% multiselect id="features"
              options=available\_features
              selected=state.enabled\_features %}



\# Checkbox

{% checkbox id="remember" 
           label="Remember me"
           checked=state.remember %}



\# Radio group

{% radiogroup id="mode" selected=state.mode %}
 {% option value="auto" %}Automatic{% endoption %}
 {% option value="manual" %}Manual{% endoption %}

{% endradiogroup %}

```



\*\*Display Elements:\*\*

```python

\# Progress bar

{% progress id="download" 
           value=state.progress 
           max=100 
           format="{percent}% \[{bar}] {current}/{total}" %}



\# Spinner

{% spinner id="loading" 
          active=state.is\_loading 
          style="dots" %}



\# Table with sorting/filtering

{% table id="results" 
        data=state.results
        columns=\["Name", "Size", "Modified"]
        sortable=true
        selectable=true
        on\_select="view\_details" %}



\# Tree view

{% tree id="file\_tree"
       data=state.tree
       expanded=state.expanded\_nodes
       on\_toggle="toggle\_node"
       on\_select="select\_node" %}



\# Log viewer

{% logview id="logs"
          lines=state.log\_lines
          follow=true
          max\_lines=1000 %}



\# Tabs

{% tabs id="main\_tabs" active=state.active\_tab %}
 {% tab key="overview" %}Overview{% endtab %}
 {% tab key="details" %}Details{% endtab %}
 {% tab key="logs" %}Logs{% endtab %}

{% endtabs %}

```



\*\*Interaction Elements:\*\*

```python

\# Button

{% button id="submit" 
         action="submit\_form"
         variant="primary" %}
 Submit

{% endbutton %}



\# Link (navigates to view)

{% link navigate="help" %}Help{% endlink %}



\# Hotkey hint

{% hint key="Ctrl+S" %}Save{% endhint %}

{% hint key="?" %}Help{% endhint %}

```



\## Full Example App



```python

\# app.py

from wijjit import Wijjit, state

from pathlib import Path



app = Wijjit()

state.current\_dir = Path.cwd()

state.files = list(state.current\_dir.iterdir())

state.selected\_files = \[]



@app.view('browser', default=True)

def file\_browser():
   return {
       'template': 'browser.tui',
       'data': {
           'path': state.current\_dir,
           'files': state.files,
           'selected': state.selected\_files,
       },
       'handlers': {
           'open': open\_file,
           'delete': confirm\_delete,
           'refresh': refresh\_files,
           'settings': lambda: app.navigate('settings'),
       }
   }



@app.view('settings')

def settings():
   return {
       'template': 'settings.tui',
       'data': state.config,
       'handlers': {
           'save': save\_and\_return,
           'cancel': lambda: app.navigate('browser'),
       }
   }



def open\_file(file):
   if file.is\_dir():
       state.current\_dir = file
       state.files = list(file.iterdir())
       # Stays on browser view
   else:
       app.navigate('viewer', file=file)



def confirm\_delete():
   if state.selected\_files:
       app.navigate('confirm', 
                   message=f"Delete {len(state.selected\_files)} files?",
                   on\_confirm=delete\_files)



if \_\_name\_\_ == '\_\_main\_\_':
   app.run()

```



```jinja

{# browser.tui #}

{% frame title="File Browser - {{ path }}" border="double" width="100%" height="100%" %}
 
 {% frame id="content" fill=true %}
   {% table id="files" 
            data=files
            selectable=true
            multi\_select=true
            selected=selected
            on\_enter="open" %}
     {% column key="name" %}Name{% endcolumn %}
     {% column key="size" format="humanize" %}Size{% endcolumn %}
     {% column key="modified" format="timeago" %}Modified{% endcolumn %}
   {% endtable %}
 {% endframe %}
 
 {% frame id="actions" height=3 %}
   {% hstack spacing=2 %}
     {% button action="open" %}{% hint key="Enter" %}Open{% endbutton %}
     {% button action="delete" %}{% hint key="Del" %}Delete{% endbutton %}
     {% button action="refresh" %}{% hint key="F5" %}Refresh{% endbutton %}
     {% button navigate="settings" %}{% hint key="," %}Settings{% endbutton %}
   {% endhstack %}
 {% endframe %}
 
 {% frame id="status" height=1 %}
   {{ files|length }} items | {{ selected|length }} selected
 {% endframe %}
 

{% endframe %}

```



\## State Management Hooks



```python

\# Watch for state changes

@app.on\_state\_change('current\_dir')

def reload\_files():
   state.files = list(state.current\_dir.iterdir())
   state.selected\_files = \[]



\# Middleware for all navigation

@app.before\_navigate

def log\_navigation(from\_view, to\_view):
   logger.info(f"Navigating from {from\_view} to {to\_view}")



\# Global error handler

@app.on\_error

def handle\_error(error):
   app.navigate('error', error=error)

```



This gives you everything you need:

\- \*\*Declarative templates\*\* with semantic markup

\- \*\*View-based routing\*\* with decorators

\- \*\*Rich element library\*\* for common patterns  

\- \*\*Global state\*\* with reactivity

\- \*\*Navigation system\*\* that works from templates or code



You could even add \*\*async support\*\* for streaming updates and \*\*plugin system\*\* for custom elements. This would be a genuinely useful library - nothing quite like it exists in the Python TUI space!

