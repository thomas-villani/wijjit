"""Demo of interactive inline apps with keyboard input.

This example shows how to use InlineApp with enable_input=True to create
interactive inline applications that accept keyboard input without using
the alternate screen buffer.

Run with: python examples/basic/inline_input_demo.py

Controls:
  - Tab / Shift+Tab: Navigate between input fields
  - Type: Enter text in focused input
  - Ctrl+Q: Exit the app
"""

import asyncio

from wijjit import InlineApp


async def demo_simple_form():
    """Demo a simple form with text inputs."""
    template = """
{% frame title="User Registration" border="rounded" %}
  {% vstack spacing=1 %}
    Name:
    {% textinput id="name" placeholder="Enter your name" %}{% endtextinput %}

    Email:
    {% textinput id="email" placeholder="Enter your email" %}{% endtextinput %}

    Press Ctrl+Q to submit
  {% endvstack %}
{% endframe %}
"""

    print()
    print("=== Interactive Form Demo ===")
    print("Tab to switch fields, type to enter text, Ctrl+Q to submit")
    print()

    async with InlineApp(
        template,
        enable_input=True,
        quit_key="ctrl+q",
        initial_state={"name": "", "email": ""},
    ) as app:
        await app.wait()

    print()
    print(f"Submitted: name={app.state.get('name', '')!r}, email={app.state.get('email', '')!r}")
    print()


async def demo_checkbox_form():
    """Demo a form with checkboxes."""
    template = """
{% frame title="Preferences" border="single" %}
  {% vstack spacing=1 %}
    Select your preferences:

    {% checkbox id="newsletter" label="Subscribe to newsletter" %}{% endcheckbox %}
    {% checkbox id="notifications" label="Enable notifications" %}{% endcheckbox %}
    {% checkbox id="dark_mode" label="Dark mode" %}{% endcheckbox %}

    Press Ctrl+Q to save
  {% endvstack %}
{% endframe %}
"""

    print()
    print("=== Checkbox Demo ===")
    print("Tab to switch, Space to toggle, Ctrl+Q to save")
    print()

    async with InlineApp(
        template,
        enable_input=True,
        quit_key="ctrl+q",
        initial_state={
            "newsletter": False,
            "notifications": True,
            "dark_mode": False,
        },
    ) as app:
        await app.wait()

    print()
    print("Saved preferences:")
    print(f"  Newsletter: {app.state.get('newsletter', False)}")
    print(f"  Notifications: {app.state.get('notifications', False)}")
    print(f"  Dark mode: {app.state.get('dark_mode', False)}")
    print()


async def demo_live_search():
    """Demo live search/filter with text input."""
    items = ["Apple", "Banana", "Cherry", "Date", "Elderberry", "Fig", "Grape"]

    template = """
{% frame title="Fruit Search" %}
  {% vstack %}
    Search:
    {% textinput id="query" placeholder="Type to filter..." %}{% endtextinput %}

    Results: {{ matches | length }} items
    {% for item in matches %}
    - {{ item }}
    {% endfor %}
  {% endvstack %}
{% endframe %}
"""

    print()
    print("=== Live Search Demo ===")
    print("Type to filter the list, Ctrl+Q to exit")
    print()

    async with InlineApp(
        template,
        enable_input=True,
        quit_key="ctrl+q",
        initial_state={"query": "", "matches": items},
    ) as app:
        # The refresh loop will automatically update display
        # as state changes from typing
        await app.wait()

    print()
    print(f"Final search: {app.state.get('query', '')!r}")
    print()


async def main():
    """Run all interactive inline demos."""
    print()
    print("=" * 60)
    print("  Wijjit Interactive Inline Demo")
    print("  Forms that stay in terminal scrollback")
    print("=" * 60)

    await demo_simple_form()
    await demo_checkbox_form()
    # Note: Live search needs wiring between textinput and filter logic
    # which requires additional setup beyond basic input routing

    print("=" * 60)
    print("  Demo complete!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
