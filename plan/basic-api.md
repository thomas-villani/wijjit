

\## View Decorators



```python

from wijjit import Wijjit, view, state



app = Wijjit()



@app.view('main', default=True)

def main\_view():

&nbsp;   return {

&nbsp;       'template': 'main.tui',

&nbsp;       'data': {

&nbsp;           'files': state.files,

&nbsp;           'current\_path': state.current\_path,

&nbsp;       },

&nbsp;       'handlers': {

&nbsp;           'open\_file': lambda file: open\_file\_handler(file),

&nbsp;           'show\_config': lambda: app.navigate('config'),

&nbsp;           'quit': lambda: app.exit(),

&nbsp;       }

&nbsp;   }



@app.view('config')

def config\_view():

&nbsp;   return {

&nbsp;       'template': 'config.tui',

&nbsp;       'data': {

&nbsp;           'server': state.config.server,

&nbsp;           'port': state.config.port,

&nbsp;       },

&nbsp;       'handlers': {

&nbsp;           'save': save\_config,

&nbsp;           'cancel': lambda: app.navigate('main'),

&nbsp;       },

&nbsp;       'on\_enter': lambda: state.view\_context.update({'editing': False}),

&nbsp;       'on\_exit': lambda: validate\_config(),

&nbsp;   }



@app.view('confirm\_delete')

def confirm\_delete\_view(item):

&nbsp;   """Views can take parameters"""

&nbsp;   return {

&nbsp;       'template': 'confirm.tui',

&nbsp;       'data': {'item': item},

&nbsp;       'handlers': {

&nbsp;           'yes': lambda: delete\_item(item) or app.navigate('main'),

&nbsp;           'no': lambda: app.navigate('main'),

&nbsp;       }

&nbsp;   }

```



\## Navigation in Templates



```jinja

{% frame title="Main Menu" %}

&nbsp; 

&nbsp; {% menu id="main\_menu" %}

&nbsp;   {% item key="f" action="browse\_files" %}Browse Files{% enditem %}

&nbsp;   {% item key="c" navigate="config" %}Configuration{% enditem %}

&nbsp;   {% item key="s" navigate="search" %}Search{% enditem %}

&nbsp;   {% item key="q" action="quit" %}Quit{% enditem %}

&nbsp; {% endmenu %}

&nbsp; 

{% endframe %}

```



Or programmatically from handlers:



```python

def on\_file\_select(file):

&nbsp;   if file.is\_dir:

&nbsp;       state.current\_path = file.path

&nbsp;       # Stay on same view, triggers re-render

&nbsp;   else:

&nbsp;       # Navigate to editor view with parameter

&nbsp;       app.navigate('editor', file=file)

```



\## Pre-built Element Library



\*\*Input Elements:\*\*

```python

\# Text input

{% textinput id="username" 

&nbsp;            placeholder="Enter username"

&nbsp;            value=state.username

&nbsp;            on\_change="update\_username"

&nbsp;            validate=username\_validator %}



\# Password input

{% textinput id="password" type="password" %}



\# Number input with validation

{% numberinput id="port" 

&nbsp;              min=1024 

&nbsp;              max=65535 

&nbsp;              value=state.port %}



\# Select/dropdown

{% select id="theme" 

&nbsp;         options=\["dark", "light", "auto"]

&nbsp;         selected=state.theme

&nbsp;         on\_select="change\_theme" %}



\# Multi-select

{% multiselect id="features"

&nbsp;              options=available\_features

&nbsp;              selected=state.enabled\_features %}



\# Checkbox

{% checkbox id="remember" 

&nbsp;           label="Remember me"

&nbsp;           checked=state.remember %}



\# Radio group

{% radiogroup id="mode" selected=state.mode %}

&nbsp; {% option value="auto" %}Automatic{% endoption %}

&nbsp; {% option value="manual" %}Manual{% endoption %}

{% endradiogroup %}

```



\*\*Display Elements:\*\*

```python

\# Progress bar

{% progress id="download" 

&nbsp;           value=state.progress 

&nbsp;           max=100 

&nbsp;           format="{percent}% \[{bar}] {current}/{total}" %}



\# Spinner

{% spinner id="loading" 

&nbsp;          active=state.is\_loading 

&nbsp;          style="dots" %}



\# Table with sorting/filtering

{% table id="results" 

&nbsp;        data=state.results

&nbsp;        columns=\["Name", "Size", "Modified"]

&nbsp;        sortable=true

&nbsp;        selectable=true

&nbsp;        on\_select="view\_details" %}



\# Tree view

{% tree id="file\_tree"

&nbsp;       data=state.tree

&nbsp;       expanded=state.expanded\_nodes

&nbsp;       on\_toggle="toggle\_node"

&nbsp;       on\_select="select\_node" %}



\# Log viewer

{% logview id="logs"

&nbsp;          lines=state.log\_lines

&nbsp;          follow=true

&nbsp;          max\_lines=1000 %}



\# Tabs

{% tabs id="main\_tabs" active=state.active\_tab %}

&nbsp; {% tab key="overview" %}Overview{% endtab %}

&nbsp; {% tab key="details" %}Details{% endtab %}

&nbsp; {% tab key="logs" %}Logs{% endtab %}

{% endtabs %}

```



\*\*Interaction Elements:\*\*

```python

\# Button

{% button id="submit" 

&nbsp;         action="submit\_form"

&nbsp;         variant="primary" %}

&nbsp; Submit

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

&nbsp;   return {

&nbsp;       'template': 'browser.tui',

&nbsp;       'data': {

&nbsp;           'path': state.current\_dir,

&nbsp;           'files': state.files,

&nbsp;           'selected': state.selected\_files,

&nbsp;       },

&nbsp;       'handlers': {

&nbsp;           'open': open\_file,

&nbsp;           'delete': confirm\_delete,

&nbsp;           'refresh': refresh\_files,

&nbsp;           'settings': lambda: app.navigate('settings'),

&nbsp;       }

&nbsp;   }



@app.view('settings')

def settings():

&nbsp;   return {

&nbsp;       'template': 'settings.tui',

&nbsp;       'data': state.config,

&nbsp;       'handlers': {

&nbsp;           'save': save\_and\_return,

&nbsp;           'cancel': lambda: app.navigate('browser'),

&nbsp;       }

&nbsp;   }



def open\_file(file):

&nbsp;   if file.is\_dir():

&nbsp;       state.current\_dir = file

&nbsp;       state.files = list(file.iterdir())

&nbsp;       # Stays on browser view

&nbsp;   else:

&nbsp;       app.navigate('viewer', file=file)



def confirm\_delete():

&nbsp;   if state.selected\_files:

&nbsp;       app.navigate('confirm', 

&nbsp;                   message=f"Delete {len(state.selected\_files)} files?",

&nbsp;                   on\_confirm=delete\_files)



if \_\_name\_\_ == '\_\_main\_\_':

&nbsp;   app.run()

```



```jinja

{# browser.tui #}

{% frame title="File Browser - {{ path }}" border="double" width="100%" height="100%" %}

&nbsp; 

&nbsp; {% frame id="content" fill=true %}

&nbsp;   {% table id="files" 

&nbsp;            data=files

&nbsp;            selectable=true

&nbsp;            multi\_select=true

&nbsp;            selected=selected

&nbsp;            on\_enter="open" %}

&nbsp;     {% column key="name" %}Name{% endcolumn %}

&nbsp;     {% column key="size" format="humanize" %}Size{% endcolumn %}

&nbsp;     {% column key="modified" format="timeago" %}Modified{% endcolumn %}

&nbsp;   {% endtable %}

&nbsp; {% endframe %}

&nbsp; 

&nbsp; {% frame id="actions" height=3 %}

&nbsp;   {% hstack spacing=2 %}

&nbsp;     {% button action="open" %}{% hint key="Enter" %}Open{% endbutton %}

&nbsp;     {% button action="delete" %}{% hint key="Del" %}Delete{% endbutton %}

&nbsp;     {% button action="refresh" %}{% hint key="F5" %}Refresh{% endbutton %}

&nbsp;     {% button navigate="settings" %}{% hint key="," %}Settings{% endbutton %}

&nbsp;   {% endhstack %}

&nbsp; {% endframe %}

&nbsp; 

&nbsp; {% frame id="status" height=1 %}

&nbsp;   {{ files|length }} items | {{ selected|length }} selected

&nbsp; {% endframe %}

&nbsp; 

{% endframe %}

```



\## State Management Hooks



```python

\# Watch for state changes

@app.on\_state\_change('current\_dir')

def reload\_files():

&nbsp;   state.files = list(state.current\_dir.iterdir())

&nbsp;   state.selected\_files = \[]



\# Middleware for all navigation

@app.before\_navigate

def log\_navigation(from\_view, to\_view):

&nbsp;   logger.info(f"Navigating from {from\_view} to {to\_view}")



\# Global error handler

@app.on\_error

def handle\_error(error):

&nbsp;   app.navigate('error', error=error)

```



This gives you everything you need:

\- \*\*Declarative templates\*\* with semantic markup

\- \*\*View-based routing\*\* with decorators

\- \*\*Rich element library\*\* for common patterns  

\- \*\*Global state\*\* with reactivity

\- \*\*Navigation system\*\* that works from templates or code



You could even add \*\*async support\*\* for streaming updates and \*\*plugin system\*\* for custom elements. This would be a genuinely useful library - nothing quite like it exists in the Python TUI space!

