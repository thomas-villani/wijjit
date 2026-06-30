"""DataGrid demo - spreadsheet-like data entry component.

This demo showcases the DataGrid element which provides a spreadsheet-like
editing experience with:
- Entry line at top (VisiCalc/Lotus 1-2-3 style)
- Arrow/Tab/Enter navigation
- Cell editing with F2 or by typing
- Mouse click to select, double-click to edit
- Row numbers and column headers
- Vertical scrolling for large datasets

Press Ctrl+Q to quit.
"""

from wijjit import Wijjit, render_template_string


def get_initial_data():
    """Get initial inventory data."""
    return [
        ["Widget Pro", "WGT-001", "42", "29.99", "Electronics"],
        ["Gadget Plus", "GDG-002", "17", "49.99", "Electronics"],
        ["Gizmo Basic", "GZM-003", "103", "9.99", "Accessories"],
        ["Super Tool", "STL-004", "28", "79.99", "Tools"],
        ["Mini Device", "MND-005", "55", "14.99", "Electronics"],
        ["Power Unit", "PWR-006", "12", "199.99", "Hardware"],
        ["Smart Sensor", "SNS-007", "89", "34.99", "Electronics"],
        ["Quick Clip", "QCL-008", "234", "4.99", "Accessories"],
    ]


# Initialize app with state
app = Wijjit(
    initial_state={
        "inventory": get_initial_data(),
        "row_count": len(get_initial_data()),
    }
)


@app.view("main", default=True)
def main_view():
    return render_template_string(
        """
{% frame title="DataGrid Demo - Inventory Manager" border="rounded" width="fill" height="fill" %}
    {% vstack spacing=1 %}
        {% datagrid id="inventory"
            data=inventory
            columns=columns
            width=70
            height=15
            show_row_numbers=True
            editable=True %}
        {% enddatagrid %}

        {% hstack spacing=2 %}
            {% button action="add_row" %}Add Row{% endbutton %}
            {% button action="delete_row" %}Delete Row{% endbutton %}
            {% button action="reset" %}Reset Data{% endbutton %}
        {% endhstack %}

        {% frame border="single" title="Instructions" width=70 height=8 %}
            Navigate: Arrow keys, Tab, Enter
            Edit: F2 to edit, or just start typing
            Mouse: Click to select, double-click to edit
            Scroll: Mouse wheel or Page Up/Down
            Actions: Use buttons below to add/delete rows
            Quit: Ctrl+Q
        {% endframe %}

        Rows: {{ row_count }}
    {% endvstack %}
{% endframe %}
        """,
        columns=[
            {"key": "product", "label": "Product", "width": 20},
            {"key": "sku", "label": "SKU", "width": 12},
            {"key": "qty", "label": "Qty", "width": 8},
            {"key": "price", "label": "Price", "width": 10},
            {"key": "category", "label": "Category", "width": 15},
        ],
        inventory=app.state.get("inventory", []),
        row_count=app.state.get("row_count", 0),
    )


@app.on_action("add_row")
def add_row(event):
    """Add a new empty row to the inventory."""
    # Create a new list (don't mutate in place) so state change is detected
    data = list(app.state.get("inventory", []))
    data.append(["New Item", "NEW-000", "0", "0.00", "Uncategorized"])
    app.state["inventory"] = data
    app.state["row_count"] = len(data)


@app.on_action("delete_row")
def delete_row(event):
    """Delete the last row from inventory."""
    # Create a new list (don't mutate in place) so state change is detected
    data = list(app.state.get("inventory", []))
    if len(data) > 0:
        data.pop()
        app.state["inventory"] = data
        app.state["row_count"] = len(data)


@app.on_action("reset")
def reset_data(event):
    """Reset to initial data."""
    data = get_initial_data()
    app.state["inventory"] = data
    app.state["row_count"] = len(data)


if __name__ == "__main__":
    app.run()
