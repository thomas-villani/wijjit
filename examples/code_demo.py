"""Code Block Demo - Demonstrates syntax-highlighted code rendering.

This example shows the CodeBlock element with cell-based rendering,
featuring Rich syntax highlighting for multiple languages.

Run with: python examples/code_demo_new.py

Controls:
- Arrow keys: Scroll up/down
- Page Up/Down: Scroll by page
- Home/End: Jump to top/bottom
- Mouse wheel: Scroll content
- q: Quit
"""

from wijjit import Wijjit
from wijjit.core.events import EventType, HandlerScope
from wijjit.logging_config import configure_logging

# Enable debug logging
configure_logging("code_demo_debug.log", level="DEBUG")

# Sample Python code
PYTHON_CODE = """
import asyncio
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class User:
    '''Represents a user in the system.'''
    id: int
    name: str
    email: str
    is_active: bool = True
    roles: List[str] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = ['user']


class UserRepository:
    '''Repository for managing users.'''

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id = 1

    async def create(self, name: str, email: str) -> User:
        '''Create a new user.

        Parameters
        ----------
        name : str
            User's full name
        email : str
            User's email address

        Returns
        -------
        User
            The created user instance
        '''
        user = User(
            id=self._next_id,
            name=name,
            email=email,
        )
        self._users[user.id] = user
        self._next_id += 1

        # Simulate async database operation
        await asyncio.sleep(0.1)

        return user

    async def find_by_email(self, email: str) -> Optional[User]:
        '''Find a user by email address.'''
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    def list_active(self) -> List[User]:
        '''Get all active users.'''
        return [u for u in self._users.values() if u.is_active]


# Example usage
async def main():
    repo = UserRepository()

    # Create users
    alice = await repo.create("Alice Smith", "alice@example.com")
    bob = await repo.create("Bob Jones", "bob@example.com")

    # Find user by email
    user = await repo.find_by_email("alice@example.com")
    if user:
        print(f"Found: {user.name}")

    # List active users
    active = repo.list_active()
    print(f"Active users: {len(active)}")


if __name__ == "__main__":
    asyncio.run(main())
"""


def create_app():
    """Create and configure the code demo application."""
    # Create app with initial state
    app = Wijjit(initial_state={"source_code": PYTHON_CODE.strip()})

    @app.view("main", default=True)
    def main_view():
        """Main view with code block."""
        # IMPORTANT: Code must be wrapped in a layout container (frame/vstack/hstack)
        # to get bounds assigned and render properly
        template = """
{% frame width="100%" height="100%" %}
  {% code id="codeblock"
          language="python"
          width="fill"
          height="fill"
          border_style="double"
          title="Python Example - User Repository"
          show_line_numbers=true %}
{{ state.source_code }}
  {% endcode %}
{% endframe %}
        """.strip()

        return {
            "template": template,
            "data": {},
            "on_enter": setup_handlers,
        }

    def setup_handlers():
        """Set up keyboard handlers."""

        def on_key(event):
            """Handle keyboard events."""
            if event.key == "q":
                app.quit()
                event.cancel()

        app.on(
            EventType.KEY,
            on_key,
            scope=HandlerScope.VIEW,
            view_name="main",
            priority=100,
        )

    return app


def main():
    """Run the code demo application."""
    app = create_app()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running app: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
