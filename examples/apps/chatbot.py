"""Chatbot - a streaming conversational TUI built with Wijjit.

A rule-based chatbot that demonstrates the core Wijjit building blocks in a
compact, real-world app: reactive state, a live template, a self-scrolling
conversation log, action handlers, and an ``async`` handler that streams the
reply one word at a time - exactly the shape you'd use to render tokens from a
streaming LLM response.

There is no network or LLM dependency - the "bot" is a small rule-based
responder (`bot_reply`). To turn this into a real assistant, replace the body of
`stream_bot_reply` with an ``async for`` over your provider's streaming API (see
the note on that function).

Features:
- Self-scrolling conversation history (a LogView that tails new messages)
- Word-by-word streaming of the bot's reply
- Send a message with Enter or the Send button
- Rule-based replies (greetings, help, time, echo)
- Clear the conversation

Controls:
- Tab/Shift+Tab: Move focus (the history, then the input, then the buttons)
- Enter: Send the message in the input box
- In the history: arrows/PageUp/PageDown to scroll (auto-scroll pauses while you
  read older messages and resumes when you scroll back to the bottom)
- Ctrl+Q: Quit
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from wijjit import Wijjit, render_template_string

# Seconds between words while streaming the bot's reply.
STREAM_DELAY = 0.05

WELCOME = "Bot: Hi! I'm a little Wijjit bot. Type 'help' to see what I can do."


def bot_reply(message: str) -> str:
    """Produce a canned reply for a user message.

    This is deliberately simple - it keeps the demo dependency-free. Replace it
    (and the streaming loop in `stream_bot_reply`) with a call to a chat API to
    build a real assistant.

    Parameters
    ----------
    message : str
        The user's message text.

    Returns
    -------
    str
        The bot's reply.
    """
    text = message.strip().lower()

    if not text:
        return "Say something and I'll do my best to reply!"
    if any(word in text for word in ("hello", "hi", "hey")):
        return "Hello there! How can I help?"
    if "help" in text:
        return (
            "I can chat about anything (loosely). Try asking for the 'time', "
            "say 'hello', or just type and I'll echo you. Use the Clear button "
            "to start over."
        )
    if "time" in text:
        return f"It's {datetime.now().strftime('%H:%M:%S')} right now."
    if "bye" in text or "quit" in text:
        return "Goodbye! Press Ctrl+Q to close the app."
    if text.endswith("?"):
        return "That's a great question. I'm only a demo, so I'll say: maybe!"
    return f'You said: "{message.strip()}". Tell me more!'


app = Wijjit(
    initial_state={
        # Each entry is one line of the transcript; the LogView soft-wraps long
        # lines and tails the bottom as new ones arrive.
        "history": [WELCOME],
        "chat_input": "",
        "status": "Tab to the message box, type, and press Enter",
    }
)


@app.view("main", default=True)
def main_view():
    """Render the chat window with a self-scrolling conversation log."""
    return render_template_string(
        """
{% frame border="rounded" title="Wijjit Chatbot" width=72 height=24 %}
  {% vstack spacing=1 padding=1 %}

    {# A LogView tails the newest line automatically (auto_scroll) and wraps
       long messages (soft_wrap). detect_log_levels is off so ordinary words
       aren't colored as if they were log levels. #}
    {% logview id="history"
        lines=history
        width="fill"
        height=15
        auto_scroll=True
        soft_wrap=True
        detect_log_levels=False
        border="single" %}
    {% endlogview %}

    {# Input row - Enter in the textinput fires the "send" action #}
    {% hstack spacing=1 %}
      {% textinput id="chat_input" placeholder="Type your message..." width="fill" action="send" %}{% endtextinput %}
      {% button action="send" %}Send{% endbutton %}
      {% button action="clear" %}Clear{% endbutton %}
    {% endhstack %}

    {% text %}{{ state.status }}{% endtext %}

  {% endvstack %}
{% endframe %}
        """,
        history=app.state["history"],
    )


async def stream_bot_reply(reply: str) -> None:
    """Append the bot's reply one word at a time (simulated streaming).

    This mirrors how you'd render a streaming LLM response: append a placeholder
    line, then rewrite its tail as each chunk arrives. Every assignment to
    ``state["history"]`` schedules a render, and the ``await`` yields to the
    event loop so the UI repaints between words.

    To use a real model, replace the ``for word in reply.split()`` loop with an
    ``async for`` over your provider's stream, e.g.::

        partial = "Bot:"
        async for chunk in client.stream(...):
            partial += chunk
            app.state["history"] = app.state["history"][:-1] + [partial]

    Parameters
    ----------
    reply : str
        The full text the bot will "type out".
    """
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
    """Append the user's message, then stream the bot's reply."""
    text = app.state.get("chat_input", "").strip()
    if not text:
        app.state["status"] = "Nothing to send - type a message first."
        return

    app.state["chat_input"] = ""
    app.state["history"] = app.state["history"] + [f"You: {text}"]
    await stream_bot_reply(bot_reply(text))


@app.on_action("clear")
def clear_conversation(event):
    """Reset the conversation to just the welcome message."""
    app.state["history"] = [WELCOME]
    app.state["status"] = "Conversation cleared"


if __name__ == "__main__":
    app.run()
