Tutorial: Chatbot
=================

This short tutorial builds a conversational TUI: a scrollable chat window with a
text input, a "bot" that replies, and Send / Clear buttons. It is a great second
project after the :doc:`quickstart` because it touches reactive state, a live
template, a scrollable log, and action handlers without any heavy domain logic.

The finished script ships as :file:`examples/apps/chatbot.py`.

What you'll build
-----------------

* A scrollable history of the conversation (your turns and the bot's).
* A message box that sends on Enter or via the Send button.
* A rule-based "bot" (no network or LLM required) that you can later swap for a
  real API call.
* A Clear button that resets the conversation.

Prerequisites
-------------

* Python 3.11+
* Wijjit installed (see :doc:`installation`)

Step 1 - state and a bot
------------------------

Start with the imports, a tiny rule-based responder, and the app state. The
``bot_reply`` function is the only piece you'd replace to make this a real
assistant.

.. code-block:: python
   :caption: chatbot.py

    from __future__ import annotations

    import textwrap
    from datetime import datetime

    from wijjit import Wijjit, render_template_string

    # Width (in columns) for a wrapped message line inside the history frame.
    HISTORY_WIDTH = 62

    WELCOME = ("Bot", "Hi! I'm a little Wijjit bot. Type 'help' to see what I can do.")


    def bot_reply(message: str) -> str:
        text = message.strip().lower()
        if not text:
            return "Say something and I'll do my best to reply!"
        if any(word in text for word in ("hello", "hi", "hey")):
            return "Hello there! How can I help?"
        if "help" in text:
            return "I can chat (loosely). Try 'time', say 'hello', or just type."
        if "time" in text:
            return f"It's {datetime.now().strftime('%H:%M:%S')} right now."
        return f'You said: "{message.strip()}". Tell me more!'


    app = Wijjit(
        initial_state={
            "messages": [WELCOME],
            "chat_input": "",
            "status": "Type a message and press Enter",
        }
    )

Each entry in ``messages`` is a ``(speaker, text)`` pair, where ``speaker`` is
``"You"`` or ``"Bot"``.

Step 2 - render the chat window
-------------------------------

Wijjit's ``{% text %}`` tag hugs its content by default, so long replies would be
clipped inside a fixed-width frame. The simplest, most predictable fix is to wrap
each message in Python and emit one physical line per row:

.. code-block:: python

    def wrap_history() -> list[str]:
        lines: list[str] = []
        for speaker, text in app.state["messages"]:
            wrapped = textwrap.wrap(f"{speaker}: {text}", width=HISTORY_WIDTH) or [""]
            lines.extend(wrapped)
            lines.append("")  # blank line between turns
        return lines


    @app.view("main", default=True)
    def main_view():
        return render_template_string(
            """
    {% frame border="rounded" title="Wijjit Chatbot" width=72 height=24 %}
      {% vstack spacing=1 padding=1 %}

        {% frame border="single" height=15 scrollable=True show_scrollbar=True %}
          {% vstack spacing=0 %}
            {% for line in history %}
              {% text %}{{ line }}{% endtext %}
            {% endfor %}
          {% endvstack %}
        {% endframe %}

        {% hstack spacing=1 %}
          {% textinput id="chat_input" placeholder="Type your message..." width="fill" action="send" %}{% endtextinput %}
          {% button action="send" %}Send{% endbutton %}
          {% button action="clear" %}Clear{% endbutton %}
        {% endhstack %}

        {% text %}{{ state.status }}{% endtext %}

      {% endvstack %}
    {% endframe %}
            """,
            history=wrap_history(),
        )

Two things to notice:

* The ``textinput`` ``id="chat_input"`` binds to ``state["chat_input"]``
  automatically, and its ``action="send"`` fires the ``send`` action when you
  press Enter in the box.
* ``history`` is passed as **live context** (recomputed every render), so the log
  always reflects the current ``messages``.

Step 3 - wire the actions
-------------------------

.. code-block:: python

    @app.on_action("send")
    def send_message(event):
        text = app.state.get("chat_input", "").strip()
        if not text:
            app.state["status"] = "Nothing to send - type a message first."
            return

        # Reassign the list (not .append) so State detects the change.
        messages = app.state["messages"] + [("You", text), ("Bot", bot_reply(text))]
        app.state["messages"] = messages
        app.state["chat_input"] = ""
        app.state["status"] = f"{len(messages)} messages - Ctrl+Q to quit"


    @app.on_action("clear")
    def clear_conversation(event):
        app.state["messages"] = [WELCOME]
        app.state["status"] = "Conversation cleared"


    if __name__ == "__main__":
        app.run()

.. important::

   Wijjit's reactive ``State`` detects **reassignment**, not in-place mutation.
   Building a new list with ``old + [items]`` and assigning it back is what
   schedules the re-render; calling ``app.state["messages"].append(...)`` would
   not.

Step 4 - run it
---------------

.. code-block:: bash

    uv run python examples/apps/chatbot.py

Press ``Tab`` to focus the message box, type something, and press Enter. The bot
replies, the history scrolls, and the status line updates. Quit with ``Ctrl+Q``.

Where to next
-------------

* Replace ``bot_reply`` with a call to a chat API to build a real assistant. Keep
  network calls in an ``async`` handler so the UI stays responsive - see
  :doc:`../user_guide/event_handling`.
* Ready for something meatier? :doc:`tutorial_spreadsheet` builds an editable
  spreadsheet with a live chart.
