"""Async Demo - Demonstrates async/await support in Wijjit.

This example showcases Phase 3 async features:
- Async view functions
- Async event handlers
- Async state callbacks
- Async lifecycle hooks

Run with: python examples/async_demo.py
Press 'f' to fetch data, 'q' to quit.
"""

import asyncio

from wijjit import Wijjit


async def fetch_data_from_api(user_id: int):
    """Simulate async API call."""
    await asyncio.sleep(1)  # Simulate network delay
    return {
        "user_id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
        "status": "active",
    }


async def save_to_database(key: str, value):
    """Simulate async database save."""
    await asyncio.sleep(0.5)  # Simulate DB write delay
    print(f"[DB] Saved {key} = {value}")


def main():
    """Run the async demo app."""
    app = Wijjit()

    # Initialize state with loading flag
    app.state.update(
        {
            "loading": False,
            "user_data": None,
            "fetch_count": 0,
        }
    )

    # Async state callback - triggered when fetch_count changes
    async def on_fetch_count_change(old_value, new_value):
        """Log fetch count changes to database."""
        await save_to_database("fetch_count", new_value)

    app.state.watch("fetch_count", on_fetch_count_change)

    # Async view function
    @app.view("main", default=True)
    async def main_view():
        """Main view with async data loading."""
        # Could load initial data here
        await asyncio.sleep(0.1)  # Simulate some async work

        return {
            "template": """
{% frame title="Async Demo" %}
Fetch Count: {{ state.fetch_count }}

{% if state.loading %}
  Loading data...
{% elif state.user_data %}
  User Data:
  - ID: {{ state.user_data.user_id }}
  - Name: {{ state.user_data.name }}
  - Email: {{ state.user_data.email }}
  - Status: {{ state.user_data.status }}
{% else %}
  Press 'f' to fetch user data
{% endif %}

Press 'q' to quit
{% endframe %}
""",
            "on_enter": on_enter_async,
            "on_exit": on_exit_async,
        }

    async def on_enter_async():
        """Async lifecycle hook called when entering view."""
        print("[Lifecycle] Entering main view (async)")
        await asyncio.sleep(0.1)
        print("[Lifecycle] View initialization complete")

    async def on_exit_async():
        """Async lifecycle hook called when exiting view."""
        print("[Lifecycle] Exiting main view (async)")
        await asyncio.sleep(0.1)
        print("[Lifecycle] Cleanup complete")

    # Async event handler
    @app.on_key("f")
    async def fetch_user_data(event):
        """Fetch user data asynchronously."""
        if app.state.loading:
            return  # Already loading

        # Update state to show loading
        app.state.loading = True
        app.state.user_data = None

        try:
            # Simulate fetching data from API
            user_id = app.state.fetch_count + 1
            user_data = await fetch_data_from_api(user_id)

            # Update state with fetched data
            app.state.user_data = user_data
            app.state.fetch_count += 1  # This triggers async state callback

        finally:
            app.state.loading = False

    # Sync event handler (backward compatibility)
    @app.on_key("q")
    def on_quit(event):
        """Quit the app (sync handler still works)."""
        app.quit()

    try:
        app.run()  # Internally calls asyncio.run(app.run_async())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
