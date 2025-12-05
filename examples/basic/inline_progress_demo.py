"""Demo of InlineApp for interactive inline updates.

This example shows how to use InlineApp for progress displays and
other interactive content that updates in place without alternate screen.

The content stays in terminal scrollback after the app exits.

Run with: python examples/basic/inline_progress_demo.py
"""

import asyncio

from wijjit import InlineApp


async def demo_progress_bar():
    """Show a progress bar that updates in place."""
    print("=== Progress Bar Demo ===")
    print("Watch the progress update in place:")
    print()

    template = """
{% frame title="Download Progress" border="rounded" %}
  {% vstack %}
    File: {{ state.filename }}
    {% progressbar value=state.progress max=100 %}{% endprogressbar %}
    {{ state.status }}
  {% endvstack %}
{% endframe %}
"""

    async with InlineApp(
        template,
        height=6,
        initial_state={
            "filename": "large_file.zip",
            "progress": 0,
            "status": "Starting...",
        },
    ) as app:
        # Simulate download progress
        for i in range(101):
            app.state.progress = i
            if i < 100:
                app.state.status = f"Downloading... {i}%"
            else:
                app.state.status = "Download complete!"
            await asyncio.sleep(0.03)

    print()
    print("Progress bar complete! Content stays in scrollback.")
    print()


async def demo_multi_task():
    """Show multiple tasks progressing."""
    print("=== Multi-Task Progress Demo ===")
    print()

    template = """
{% frame title="Installation Progress" border="single" %}
  {% vstack spacing=1 %}
    {% hstack %}
      Task 1: {% progressbar value=state.task1 max=100 width=20 %}{% endprogressbar %} {{ state.task1 }}%
    {% endhstack %}
    {% hstack %}
      Task 2: {% progressbar value=state.task2 max=100 width=20 %}{% endprogressbar %} {{ state.task2 }}%
    {% endhstack %}
    {% hstack %}
      Task 3: {% progressbar value=state.task3 max=100 width=20 %}{% endprogressbar %} {{ state.task3 }}%
    {% endhstack %}
    Status: {{ state.status }}
  {% endvstack %}
{% endframe %}
"""

    async with InlineApp(
        template,
        height=9,
        initial_state={
            "task1": 0,
            "task2": 0,
            "task3": 0,
            "status": "Starting installation...",
        },
    ) as app:
        # Task 1 runs first
        app.state.status = "Installing core components..."
        for i in range(101):
            app.state.task1 = i
            await asyncio.sleep(0.02)

        # Task 2 runs next
        app.state.status = "Installing dependencies..."
        for i in range(101):
            app.state.task2 = i
            await asyncio.sleep(0.015)

        # Task 3 runs last
        app.state.status = "Configuring system..."
        for i in range(101):
            app.state.task3 = i
            await asyncio.sleep(0.01)

        app.state.status = "Installation complete!"
        await asyncio.sleep(0.5)

    print()
    print("All tasks complete!")
    print()


async def demo_status_updates():
    """Show status updates with spinner."""
    print("=== Status Updates Demo ===")
    print()

    template = """
{% frame title="Build Status" %}
  {% vstack %}
    {% spinner style="dots" %}{% endspinner %} {{ state.step }}

    Completed: {{ state.completed }} / {{ state.total }}
  {% endvstack %}
{% endframe %}
"""

    steps = [
        "Compiling source files...",
        "Running type checks...",
        "Bundling assets...",
        "Optimizing output...",
        "Generating documentation...",
        "Build complete!",
    ]

    async with InlineApp(
        template,
        height=6,
        initial_state={
            "step": steps[0],
            "completed": 0,
            "total": len(steps) - 1,
        },
        refresh_interval=0.08,  # Faster refresh for spinner animation
    ) as app:
        for i, step in enumerate(steps):
            app.state.step = step
            app.state.completed = min(i, len(steps) - 1)
            await asyncio.sleep(1.0)

    print()
    print("Build finished!")
    print()


async def main():
    """Run all InlineApp demos."""
    print()
    print("=" * 60)
    print("  Wijjit InlineApp Demo")
    print("  Interactive updates without alternate screen")
    print("=" * 60)
    print()

    await demo_progress_bar()
    await asyncio.sleep(0.5)

    await demo_multi_task()
    await asyncio.sleep(0.5)

    await demo_status_updates()

    print("=" * 60)
    print("  All demos complete!")
    print("  Scroll up to see the full history.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
