Tutorial: Terminal Spreadsheet
==============================

This tutorial builds "Excel in the console": an editable spreadsheet grid, a live
column chart of per-product totals, and Save that writes back to a real
``.xlsx`` file (with a graceful CSV fallback). It's a tour of Wijjit's richer
pieces - the :class:`~wijjit.elements.input.datagrid.DataGrid` widget, charts,
reading a widget's live contents in a handler, and integrating an optional
third-party dependency.

The finished script ships as :file:`examples/apps/spreadsheet.py`.

What you'll build
-----------------

* An editable ``DataGrid`` seeded from a workbook on disk.
* A ``columnchart`` that visualizes each product's total across four quarters.
* Save / Update Chart / Add Row / Reset actions.
* Persistence to ``budget.xlsx`` via ``openpyxl`` when available, falling back to
  ``budget.csv`` with the standard library so the demo always works.

Prerequisites
-------------

* Python 3.11+ and Wijjit installed (see :doc:`installation`).
* Optional: ``pip install openpyxl`` (or ``pip install wijjit[xlsx]``) to read and
  write real Excel files. Without it, the app transparently uses CSV.

Step 1 - optional dependency and file I/O
-----------------------------------------

Import ``openpyxl`` behind a flag so the app runs whether or not it is installed,
then define the columns, seed data, and load/save helpers that switch format
based on that flag.

.. code-block:: python
   :caption: spreadsheet.py

    from __future__ import annotations

    import csv
    from pathlib import Path

    from wijjit import Wijjit, render_template_string

    try:
        import openpyxl

        HAVE_OPENPYXL = True
    except ImportError:  # graceful fallback to CSV
        openpyxl = None  # type: ignore[assignment]
        HAVE_OPENPYXL = False

    DATA_DIR = Path(__file__).resolve().parent
    XLSX_PATH = DATA_DIR / "budget.xlsx"
    CSV_PATH = DATA_DIR / "budget.csv"

    COLUMNS = [
        {"key": "product", "label": "Product", "width": 16},
        {"key": "q1", "label": "Q1", "width": 7},
        {"key": "q2", "label": "Q2", "width": 7},
        {"key": "q3", "label": "Q3", "width": 7},
        {"key": "q4", "label": "Q4", "width": 7},
    ]
    HEADERS = [column["label"] for column in COLUMNS]

    SAMPLE_ROWS = [
        ["Widgets", "120", "135", "150", "160"],
        ["Gadgets", "90", "110", "95", "130"],
        ["Gizmos", "60", "75", "80", "70"],
        ["Doohickeys", "40", "55", "50", "65"],
    ]


    def storage_path() -> Path:
        return XLSX_PATH if HAVE_OPENPYXL else CSV_PATH


    def load_rows() -> list[list[str]]:
        path = storage_path()
        if not path.exists():
            return [row[:] for row in SAMPLE_ROWS]
        if HAVE_OPENPYXL:
            sheet = openpyxl.load_workbook(path).active
            rows = [
                ["" if cell is None else str(cell) for cell in record]
                for record in sheet.iter_rows(min_row=2, values_only=True)
                if record is not None
            ]
        else:
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))[1:]  # skip header
        return rows or [row[:] for row in SAMPLE_ROWS]


    def save_rows(rows: list[list[str]]) -> None:
        path = storage_path()
        if HAVE_OPENPYXL:
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = "Budget"
            sheet.append(HEADERS)
            for row in rows:
                sheet.append(row)
            workbook.save(path)
        else:
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(HEADERS)
                writer.writerows(rows)

``DataGrid`` stores every cell as a string, so the helpers keep everything as
text - no type juggling on the round-trip.

Step 2 - chart data and app state
---------------------------------

The chart sums the four quarter columns for each product. Parsing each cell
defensively means a half-typed edit never crashes the chart.

.. code-block:: python

    def compute_chart(rows: list[list[str]]) -> list[tuple[str, float]]:
        chart_data: list[tuple[str, float]] = []
        for row in rows:
            name = row[0] if row else ""
            total = 0.0
            for cell in row[1:]:
                try:
                    total += float(cell)
                except (ValueError, TypeError):
                    pass  # blank or non-numeric cell
            chart_data.append((name or "?", total))
        return chart_data


    _initial_rows = load_rows()

    app = Wijjit(
        initial_state={
            "sheet": _initial_rows,
            "chart_data": compute_chart(_initial_rows),
            "status": f"Loaded {len(_initial_rows)} rows. Edit cells, then Save.",
        }
    )

Step 3 - the layout
-------------------

Put the grid and the chart side by side. Both widgets draw their own border by
default, so we wrap each in a titled frame and set ``border="none"`` on the inner
widget to avoid a double border.

.. code-block:: python

    @app.view("main", default=True)
    def main_view():
        return render_template_string(
            """
    {% frame title="Terminal Spreadsheet" border="rounded" width="fill" height="fill" %}
      {% vstack spacing=1 padding=1 %}

        {% hstack spacing=2 %}
          {% frame title="Budget (editable)" border="single" width=54 height=16 %}
            {% datagrid id="sheet" data=sheet columns=columns
                width=50 height=13 editable=True border="none" %}
            {% enddatagrid %}
          {% endframe %}

          {% frame title="Totals by product" border="single" width=44 height=16 %}
            {% columnchart id="chart" data=chart_data
                width=40 height=13 column_width=3 spacing=1
                show_axis=True border="none" %}
            {% endcolumnchart %}
          {% endframe %}
        {% endhstack %}

        {% hstack spacing=2 %}
          {% button action="save" %}Save{% endbutton %}
          {% button action="refresh_chart" %}Update Chart{% endbutton %}
          {% button action="add_row" %}Add Row{% endbutton %}
          {% button action="reset" %}Reset{% endbutton %}
        {% endhstack %}

        {% text %}{{ state.status }}{% endtext %}

      {% endvstack %}
    {% endframe %}
            """,
            columns=COLUMNS,
            sheet=app.state["sheet"],
            chart_data=app.state["chart_data"],
        )

Step 4 - reading the grid's live edits
--------------------------------------

This is the key concept. ``DataGrid`` binding is **one-directional**: the
``data=sheet`` prop pushes ``state["sheet"]`` into the grid at render time, but
the user's edits stay on the *element* - they are not written back into state
automatically. So a handler that needs the edited values must read the live
element with :meth:`~wijjit.Wijjit.get_element_by_id`:

.. code-block:: python

    def current_rows() -> list[list[str]]:
        grid = app.get_element_by_id("sheet")
        if grid is not None:
            return grid.get_data()  # committed cell edits
        return app.state.get("sheet", [])


    @app.on_action("refresh_chart")
    def refresh_chart(event):
        rows = current_rows()
        app.state["sheet"] = rows
        app.state["chart_data"] = compute_chart(rows)
        app.state["status"] = "Chart updated from the current grid."


    @app.on_action("save")
    def save(event):
        rows = current_rows()
        app.state["sheet"] = rows
        app.state["chart_data"] = compute_chart(rows)
        try:
            save_rows(rows)
        except Exception as exc:
            app.state["status"] = f"Save failed: {exc}"
            return
        app.state["status"] = f"Saved {len(rows)} rows to {storage_path().name}."


    @app.on_action("add_row")
    def add_row(event):
        rows = current_rows() + [["New product", "0", "0", "0", "0"]]
        app.state["sheet"] = rows
        app.state["status"] = "Added a row. Edit it, then Save."


    @app.on_action("reset")
    def reset(event):
        rows = [row[:] for row in SAMPLE_ROWS]
        app.state["sheet"] = rows
        app.state["chart_data"] = compute_chart(rows)
        app.state["status"] = "Reset to sample data (not yet saved)."


    if __name__ == "__main__":
        app.run()

.. note::

   A cell edit is only in ``grid.get_data()`` once it is **committed** - which
   happens automatically when you navigate out of the cell (Enter/Tab/arrows). If
   a user is mid-typing when they click Save, tell them to press Enter first. The
   handlers above write the freshly-read rows back to ``state["sheet"]``, so the
   grid and chart stay in sync after every action.

Step 5 - run it
---------------

.. code-block:: bash

    # CSV mode (works out of the box)
    uv run python examples/apps/spreadsheet.py

    # Real .xlsx mode
    uv run --with openpyxl python examples/apps/spreadsheet.py

Try the workflow: ``Tab`` into the grid, edit a quarter figure, press Enter to
commit, then click **Update Chart** to see the bar change, or **Save** to write
the file. Relaunch and your edits are still there.

Where to next
-------------

* Swap the four-quarter schema for your own columns - only ``COLUMNS``,
  ``HEADERS``, and ``SAMPLE_ROWS`` need to change.
* Add a second chart (a ``barchart`` of quarter-over-quarter totals) using the
  same ``compute_*`` pattern - see :doc:`../user_guide/components`.
* Explore the full ``DataGrid`` API (``get_data_as_dicts``,
  ``get_data_as_dataframe``, ``add_column``) in the
  :doc:`../api_reference/elements` reference.
