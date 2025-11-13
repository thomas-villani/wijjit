"""Demo of different tree indicator styles.

This example demonstrates the various expand/collapse indicator styles
available for the Tree element, including Unicode triangles, circles,
squares, and ASCII fallbacks.
"""

from wijjit.core.app import App
from wijjit.elements.display import Tree, TreeIndicatorStyle

# Sample tree data
tree_data = {
    "label": "Root Node",
    "value": "root",
    "children": [
        {
            "label": "Documents",
            "value": "docs",
            "children": [
                {"label": "resume.pdf", "value": "resume"},
                {"label": "cover_letter.docx", "value": "cover"},
            ],
        },
        {
            "label": "Pictures",
            "value": "pics",
            "children": [
                {"label": "vacation.jpg", "value": "vacation"},
                {"label": "family.png", "value": "family"},
            ],
        },
        {
            "label": "Music",
            "value": "music",
            "children": [
                {"label": "playlist1.m3u", "value": "pl1"},
                {"label": "album", "value": "album", "children": []},
            ],
        },
    ],
}


def main():
    """Main application entry point."""
    app = App()

    # Create multiple trees with different indicator styles
    styles = [
        (TreeIndicatorStyle.TRIANGLES_LARGE, "Large Triangles (Default)"),
        (TreeIndicatorStyle.TRIANGLES, "Small Triangles"),
        (TreeIndicatorStyle.CIRCLES, "Circles"),
        (TreeIndicatorStyle.SQUARES, "Squares"),
        (TreeIndicatorStyle.BRACKETS, "Brackets (ASCII Safe)"),
        (TreeIndicatorStyle.MINIMAL, "Minimal"),
    ]

    @app.view("/")
    def main_view(state):
        """Main view showing all indicator styles."""
        # Initialize expansion state if not set
        if "expanded" not in state:
            state["expanded"] = {}
            for style, _ in styles:
                state["expanded"][style.name] = set()

        # Render template showing all styles
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("Tree Indicator Styles Demo".center(70))
        lines.append("=" * 70)
        lines.append("")
        lines.append("Navigate: Use arrow keys, Enter/Space to expand/collapse")
        lines.append("Press Q to quit")
        lines.append("")

        for i, (style, description) in enumerate(styles):
            lines.append("-" * 70)
            lines.append(f"{description}".center(70))
            lines.append("-" * 70)

            # Create tree with this style
            tree = Tree(
                id=f"tree_{i}",
                data=tree_data,
                width=68,
                height=10,
                indicator_style=style,
            )

            # Restore expansion state
            tree.expanded_nodes = state["expanded"][style.name]

            # Handle tree expansion
            @tree.on_expand
            def handle_expand(node_id, style_name=style.name):
                state["expanded"][style_name].add(node_id)

            @tree.on_collapse
            def handle_collapse(node_id, style_name=style.name):
                state["expanded"][style_name].discard(node_id)

            lines.append(tree.render())
            lines.append("")

        return "\n".join(lines)

    # Handle quit key
    @app.on_key("q")
    def quit_app():
        app.stop()

    app.run()


if __name__ == "__main__":
    main()
