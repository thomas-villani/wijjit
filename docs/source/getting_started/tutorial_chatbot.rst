Tutorial: Chatbot
=================

This tutorial builds a conversational TUI: a self-scrolling chat window with a
text input, a "bot" that streams its reply one word at a time, and Send / Clear
buttons. It is a great second project after the :doc:`quickstart` because it
touches reactive state, a live template, a self-tailing log, a plain action
handler, and an ``async`` handler - the exact shape you'd use to render tokens
from a streaming LLM response.

The finished script ships as :file:`examples/apps/chatbot.py`.

What you'll build
-----------------

* A conversation history that automatically scrolls to the newest message.
* A message box that sends on Enter or via the Send button.
* Word-by-word streaming of the bot's reply.
* A rule-based "bot" (no network or LLM required) you can later swap for a real
  API call.
* A Clear button that resets the conversation.

Prerequisites
-------------

* Python 3.11+
* Wijjit installed (see :doc:`installation`)

Step 1 - state and a bot
------------------------

Start with the imports, a tiny rule-based responder, and the app state. The
transcript is just a list of strings - one line per turn - which is exactly what
the ``LogView`` widget consumes.

.. code-block:: python
   :caption: chatbot.py

    from __future__ import annotations

    import asyncio
    from datetime import datetime

    from wijjit import Wijjit, render_template_string

    STREAM_DELAY = 0.05  # seconds between words while streaming

    WELCOME = "Bot: Hi! I'm a little Wijjit bot. Type 'help' to see what I can do."


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
            "history": [WELCOME],
            "chat_input": "",
            "status": "Tab to the message box, type, and press Enter",
        }
    )

Step 2 - render the chat window with LogView
--------------------------------------------

The :class:`~wijjit.elements.display.logview.LogView` widget is purpose-built for
scrolling text. Two of its options do the heavy lifting for us:

* ``auto_scroll=True`` (the default) tails the newest line as content grows, and
  automatically pauses if the user scrolls up to read history.
* ``soft_wrap=True`` wraps long messages to the width, so we don't have to wrap
  them ourselves.

We also set ``detect_log_levels=False`` so ordinary words (like "info") aren't
colored as if they were log levels.

.. code-block:: python

    @app.view("main", default=True)
    def main_view():
        return render_template_string("""
    {% frame border="rounded" title="Wijjit Chatbot" width=72 height=24 %}
      {% vstack spacing=1 padding=1 %}

        {% logview id="history" lines=history width="fill" height=15
            auto_scroll=True soft_wrap=True detect_log_levels=False
            border="single" %}
        {% endlogview %}

        {% hstack spacing=1 %}
          {% textinput id="chat_input" placeholder="Type your message..." width="fill" action="send" %}{% endtextinput %}
          {% button action="send" %}Send{% endbutton %}
          {% button action="clear" %}Clear{% endbutton %}
        {% endhstack %}

        {% text %}{{ state.status }}{% endtext %}

      {% endvstack %}
    {% endframe %}
            """, history=app.state["history"])

The ``textinput`` ``id="chat_input"`` binds to ``state["chat_input"]``
automatically, and its ``action="send"`` fires the ``send`` action when you press
Enter in the box. ``history`` is passed as **live context** (recomputed every
render), so the log always reflects the current transcript.

Step 3 - stream the reply
-------------------------

Here's the interesting part. Making the handler ``async`` lets us ``await``
between updates; each assignment to ``state["history"]`` schedules a render, and
the ``await`` yields to the event loop so the UI repaints between words. That is
precisely how you'd render a streaming model response.

.. code-block:: python

    async def stream_bot_reply(reply: str) -> None:
        app.state["history"] = app.state["history"] + ["Bot:"]
        app.state["status"] = "Bot is typing..."

        partial = "Bot:"
        for word in reply.split():
            partial = f"{partial} {word}"
            # Rewrite the last line in place as the reply grows.
            app.state["history"] = app.state["history"][:-1] + [partial]
            await asyncio.sleep(STREAM_DELAY)

        app.state["status"] = f"{len(app.state['history'])} messages - Ctrl+Q to quit"


    @app.on_action("send")
    async def send_message(event):
        text = app.state.get("chat_input", "").strip()
        if not text:
            app.state["status"] = "Nothing to send - type a message first."
            return

        app.state["chat_input"] = ""
        app.state["history"] = app.state["history"] + [f"You: {text}"]
        await stream_bot_reply(bot_reply(text))


    @app.on_action("clear")
    def clear_conversation(event):
        app.state["history"] = [WELCOME]
        app.state["status"] = "Conversation cleared"


    if __name__ == "__main__":
        app.run()

To use a real model, replace the ``for word in reply.split()`` loop with an
``async for`` over your provider's stream::

    partial = "Bot:"
    async for chunk in client.stream(...):
        partial += chunk
        app.state["history"] = app.state["history"][:-1] + [partial]

.. important::

   Wijjit's reactive ``State`` detects **reassignment**, not in-place mutation.
   Building a new list with ``old + [items]`` (or ``old[:-1] + [line]``) and
   assigning it back is what schedules the re-render; calling
   ``app.state["history"].append(...)`` would not.

Step 4 - run it
---------------

.. code-block:: bash

    uv run python examples/apps/chatbot.py

Press ``Tab`` to reach the message box, type something, and press Enter. The bot
"types" its reply word by word, and the history tails to the bottom on its own.
Scroll up with the arrow keys to read earlier messages - auto-scroll pauses until
you scroll back to the bottom. Quit with ``Ctrl+Q``.

Where to next
-------------

* Swap ``bot_reply`` + the streaming loop for a real chat API. Keeping the call
  in the ``async`` handler is what keeps the UI responsive while tokens arrive -
  see :doc:`../user_guide/event_handling`.
* Ready for something meatier? :doc:`tutorial_spreadsheet` builds an editable
  spreadsheet with a live chart.
