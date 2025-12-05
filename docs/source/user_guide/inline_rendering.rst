Inline Rendering
================

Wijjit's inline rendering lets you output styled UI directly to terminal scrollback without entering full-screen (alternate buffer) mode. This is ideal for:

* CLI tools that output formatted results
* Progress indicators that update in-place
* Quick interactive prompts that don't need a full TUI
* Styled output that should remain visible after the program exits

Two APIs are provided:

* ``render_inline()`` - One-shot rendering of a template to stdout
* ``InlineApp`` - Interactive inline display with reactive state updates

One-shot Rendering
------------------

Use ``render_inline()`` when you want to output styled content once:

.. code-block:: python

    from wijjit import render_inline

    # Render a styled frame with data
    render_inline('''
    {% frame title="Build Results" border="rounded" %}
      {% vstack %}
        Status: {{ status }}
        Duration: {{ duration }}s
        Tests: {{ passed }}/{{ total }} passed
      {% endvstack %}
    {% endframe %}
    ''',
        status="SUCCESS",
        duration=12.5,
        passed=42,
        total=42
    )

The output appears in your terminal's scrollback and remains visible after the script exits.

Options
^^^^^^^

``render_inline()`` accepts these parameters:

* ``template`` - Jinja2 template string with Wijjit tags
* ``width`` - Output width in columns (default: terminal width)
* ``height`` - Output height in lines (default: "auto" to fit content)
* ``print_output`` - If ``True`` (default), print to stdout. If ``False``, return the ANSI string.
* ``file`` - File object to write to (default: sys.stdout)
* ``**context`` - Template context variables

.. code-block:: python

    # Capture output instead of printing
    ansi_str = render_inline(template, print_output=False, **data)

    # Fixed width rendering
    render_inline(template, width=60, **data)

    # Write to a file
    with open("output.txt", "w") as f:
        render_inline(template, file=f, **data)

Interactive Inline Apps
-----------------------

Use ``InlineApp`` when you need reactive updates that refresh in-place:

.. code-block:: python

    import asyncio
    from wijjit import InlineApp

    template = '''
    {% frame title="Download Progress" %}
      {% vstack %}
        {% progress value=state.progress max=100 %}{% endprogress %}
        {{ state.status }}
      {% endvstack %}
    {% endframe %}
    '''

    async def main():
        async with InlineApp(template, initial_state={"progress": 0, "status": "Starting..."}) as app:
            for i in range(101):
                app.state.progress = i
                app.state.status = f"Downloading... {i}%"
                await asyncio.sleep(0.05)
            app.state.status = "Complete!"
            await asyncio.sleep(1)

    asyncio.run(main())

The display updates in-place as state changes. When the context manager exits, the content remains in scrollback.

InlineApp Parameters
^^^^^^^^^^^^^^^^^^^^

* ``template`` - Jinja2 template string
* ``height`` - Display height: integer for fixed, ``"auto"`` to calculate from content
* ``width`` - Display width (default: terminal width)
* ``initial_state`` - Dictionary of initial state values
* ``refresh_interval`` - Seconds between refresh checks (default: 0.1)
* ``enable_input`` - Enable keyboard input handling (default: False)
* ``quit_key`` - Key to exit when input enabled (default: "ctrl+q")

Keyboard Input
--------------

Enable ``enable_input=True`` to accept keyboard input:

.. code-block:: python

    template = '''
    {% frame title="Quick Entry" %}
      {% vstack %}
        Name:
        {% textinput id="name" placeholder="Enter your name" %}{% endtextinput %}

        Email:
        {% textinput id="email" placeholder="Enter your email" %}{% endtextinput %}

        Press Ctrl+Q when done
      {% endvstack %}
    {% endframe %}
    '''

    async with InlineApp(template, enable_input=True, quit_key="ctrl+q") as app:
        await app.wait()  # Block until quit key pressed

    print(f"Name: {app.state.name}")
    print(f"Email: {app.state.email}")

Features when input is enabled:

* **Tab / Shift+Tab** - Navigate between focusable elements
* **Typing** - Input goes to the focused element
* **Quit key** - Exit the app (default: Ctrl+Q)
* **State sync** - Element values automatically sync to ``app.state`` by element ID

Methods
^^^^^^^

* ``app.state`` - Reactive state object (changes trigger re-render)
* ``app.refresh()`` - Force immediate re-render
* ``app.stop()`` - Stop the app programmatically
* ``await app.wait()`` - Block until app is stopped

Animation Support
-----------------

InlineApp automatically animates spinners:

.. code-block:: python

    template = '''
    {% frame title="Processing" %}
      {% hstack %}
        {% spinner active=true %}{% endspinner %}
        {{ state.message }}
      {% endhstack %}
    {% endframe %}
    '''

    async with InlineApp(template, initial_state={"message": "Working..."}) as app:
        await asyncio.sleep(3)
        app.state.message = "Done!"

The spinner animates automatically via the internal refresh loop.

Comparison with Full-Screen Apps
--------------------------------

+---------------------------+------------------+----------------------+
| Feature                   | Wijjit (full)    | InlineApp            |
+===========================+==================+======================+
| Alternate screen buffer   | Yes              | No                   |
+---------------------------+------------------+----------------------+
| Content after exit        | Cleared          | Stays in scrollback  |
+---------------------------+------------------+----------------------+
| Mouse support             | Yes              | No                   |
+---------------------------+------------------+----------------------+
| Keyboard input            | Yes              | Optional             |
+---------------------------+------------------+----------------------+
| Multiple views            | Yes              | Single template      |
+---------------------------+------------------+----------------------+
| Overlays/modals           | Yes              | No                   |
+---------------------------+------------------+----------------------+
| Use case                  | Full TUI apps    | CLI output, prompts  |
+---------------------------+------------------+----------------------+

Examples
--------

See these examples in the ``examples/basic/`` directory:

* ``inline_demo.py`` - One-shot rendering with frames, tables, nested layouts
* ``inline_progress_demo.py`` - Interactive progress bar with InlineApp
* ``inline_input_demo.py`` - Interactive forms with keyboard input
