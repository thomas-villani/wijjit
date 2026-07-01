"""Chatbot - A simple conversational TUI built with Wijjit.

A rule-based chatbot that demonstrates the core Wijjit building blocks in a
compact, real-world app: reactive state, a live template, a scrollable
conversation log, and action handlers wired to a text input.

There is no network or LLM dependency - the "bot" is a small rule-based
responder (`bot_reply`), so the demo runs anywhere. Swap `bot_reply` for a call
to your favourite API to turn it into a real assistant.

Features:
- Scrollable conversation history (you + bot turns)
- Send a message with Enter or the Send button
- Rule-based replies (greetings, help, time, echo)
- Clear the conversation

Controls:
- Enter: Send the message in the input box
- Tab/Shift+Tab: Move focus between the input and buttons
- Ctrl+Q: Quit
"""

from __future__ import annotations

import textwrap
from datetime import datetime

from wijjit import Wijjit, render_template_string

# Width (in columns) available for a message line inside the history frame.
# Messages are wrapped to this width in Python so long replies stay readable.
HISTORY_WIDTH = 62

# The greeting the bot opens with. Each message is a (speaker, text) pair;
# speaker is "You" or "Bot".
WELCOME = ("Bot", "Hi! I'm a little Wijjit bot. Type 'help' to see what I can do.")


def bot_reply(message: str) -> str:
    """Produce a canned reply for a user message.

    This is deliberately simple - it keeps the demo dependency-free. Replace it
    with a call to a chat API to build a real assistant.

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
        "messages": [WELCOME],
        "chat_input": "",
        "status": "Type a message and press Enter",
    }
)


def wrap_history() -> list[str]:
    """Flatten the conversation into wrapped display lines.

    Each (speaker, text) turn becomes one or more physical lines (wrapped to
    ``HISTORY_WIDTH``) followed by a blank separator line.

    Returns
    -------
    list[str]
        Display-ready lines for the history frame.
    """
    lines: list[str] = []
    for speaker, text in app.state["messages"]:
        wrapped = textwrap.wrap(f"{speaker}: {text}", width=HISTORY_WIDTH) or [""]
        lines.extend(wrapped)
        lines.append("")  # blank line between turns
    return lines


@app.view("main", default=True)
def main_view():
    """Render the chat window with a live conversation log."""
    return render_template_string(
        """
{% frame border="rounded" title="Wijjit Chatbot" width=72 height=24 %}
  {% vstack spacing=1 padding=1 %}

    {# Scrollable conversation history #}
    {% frame border="single" height=15 scrollable=True show_scrollbar=True %}
      {% vstack spacing=0 %}
        {% for line in history %}
          {% text %}{{ line }}{% endtext %}
        {% endfor %}
      {% endvstack %}
    {% endframe %}

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
        history=wrap_history(),
    )


@app.on_action("send")
def send_message(event):
    """Append the user's message, generate a reply, and clear the input."""
    text = app.state.get("chat_input", "").strip()
    if not text:
        app.state["status"] = "Nothing to send - type a message first."
        return

    # Append both turns. Reassign the list (not .append) so State detects the
    # change and schedules a re-render.
    messages = app.state["messages"] + [("You", text), ("Bot", bot_reply(text))]
    app.state["messages"] = messages
    app.state["chat_input"] = ""
    app.state["status"] = f"{len(messages)} messages - Ctrl+Q to quit"


@app.on_action("clear")
def clear_conversation(event):
    """Reset the conversation to just the welcome message."""
    app.state["messages"] = [WELCOME]
    app.state["status"] = "Conversation cleared"


if __name__ == "__main__":
    app.run()
