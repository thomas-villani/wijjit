"""Jinja2 template extensions for chart elements.

This module provides Jinja2 extensions for data visualization elements
including sparklines, bar charts, column charts, line charts, gauges, and heat maps.
"""

from collections.abc import Callable
from typing import Any, Literal, cast

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser

from wijjit.core.render_context import get_render_context
from wijjit.core.vdom import VNodeBuilder
from wijjit.logging_config import get_logger
from wijjit.tags.layout import get_element_marker

logger = get_logger(__name__)


class SparklineExtension(Extension):
    """Jinja2 extension for {% sparkline %} tag.

    Syntax:
        {% sparkline id="cpu" data=history width=20 style="line" %}
        {% endsparkline %}
    """

    tags = {"sparkline"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the sparkline tag."""
        lineno = next(parser.stream).lineno

        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endsparkline"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        node = nodes.CallBlock(
            self.call_method("_render_sparkline", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endsparkline",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_sparkline(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        data: list[Any] | None = None,
        width: int = 20,
        height: int = 1,
        style: Literal["line", "bar", "dot"] = "line",
        show_minmax: bool = False,
        show_current: bool = False,
        color: str | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the sparkline tag."""
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        if id is None:
            id = context.generate_id("sparkline")

        # Get data from state if binding enabled
        if bind and id:
            try:
                if id in state:
                    data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create VNode for reconciliation
        vnode = VNodeBuilder("Sparkline", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("data", data or [])
        vnode.set_prop("width", int(width))
        vnode.set_prop("height", int(height))
        vnode.set_prop("style", style)
        vnode.set_prop("show_minmax", bool(show_minmax))
        vnode.set_prop("show_current", bool(show_current))
        if color:
            vnode.set_prop("color", color)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_prop("bind", bind)
        vnode.set_layout(width=width, height=height)

        context.add_vnode(vnode)

        # Consume body
        caller()

        return get_element_marker(context)


class BarChartExtension(Extension):
    """Jinja2 extension for {% barchart %} tag.

    Syntax:
        {% barchart id="sales" data=metrics width=40 height=10
           show_labels=true show_values=true color="gradient" %}
        {% endbarchart %}
    """

    tags = {"barchart"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the barchart tag."""
        lineno = next(parser.stream).lineno

        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endbarchart"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        node = nodes.CallBlock(
            self.call_method("_render_barchart", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endbarchart",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_barchart(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        data: list[Any] | None = None,
        width: int = 40,
        height: int = 10,
        bar_height: int = 1,
        show_labels: bool = True,
        show_values: bool = True,
        label_width: int | None = None,
        value_width: int = 6,
        color: Literal["default", "gradient", "threshold"] = "default",
        color_scale: str = "green",
        show_scrollbar: bool = True,
        show_border: bool = False,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the barchart tag."""
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        if id is None:
            id = context.generate_id("barchart")

        # Get data from state if binding enabled
        if bind and id:
            try:
                if id in state:
                    data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create VNode for reconciliation
        vnode = VNodeBuilder("BarChart", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("data", data or [])
        vnode.set_prop("width", int(width))
        vnode.set_prop("height", int(height))
        vnode.set_prop("bar_height", int(bar_height))
        vnode.set_prop("show_labels", bool(show_labels))
        vnode.set_prop("show_values", bool(show_values))
        if label_width is not None:
            vnode.set_prop("label_width", int(label_width))
        vnode.set_prop("value_width", int(value_width))
        vnode.set_prop("color", color)
        vnode.set_prop("color_scale", color_scale)
        vnode.set_prop("show_scrollbar", bool(show_scrollbar))
        vnode.set_prop("show_border", bool(show_border))
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_prop("bind", bind)
        vnode.set_layout(width=width, height=height)

        context.add_vnode(vnode)

        # Consume body
        caller()

        return get_element_marker(context)


class ColumnChartExtension(Extension):
    """Jinja2 extension for {% columnchart %} tag.

    Syntax:
        {% columnchart id="monthly" data=metrics width=60 height=15
           column_width=3 spacing=1 show_labels=true %}
        {% endcolumnchart %}
    """

    tags = {"columnchart"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the columnchart tag."""
        lineno = next(parser.stream).lineno

        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endcolumnchart"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        node = nodes.CallBlock(
            self.call_method("_render_columnchart", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endcolumnchart",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_columnchart(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        data: list[Any] | None = None,
        width: int = 60,
        height: int = 15,
        column_width: int = 3,
        spacing: int = 1,
        show_labels: bool = True,
        show_axis: bool = True,
        axis_width: int = 6,
        show_grid: bool = False,
        color: Literal["default", "gradient", "threshold"] = "default",
        color_scale: str = "green",
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the columnchart tag."""
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        if id is None:
            id = context.generate_id("columnchart")

        # Get data from state if binding enabled
        if bind and id:
            try:
                if id in state:
                    data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create VNode for reconciliation
        vnode = VNodeBuilder("ColumnChart", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("data", data or [])
        vnode.set_prop("width", int(width))
        vnode.set_prop("height", int(height))
        vnode.set_prop("column_width", int(column_width))
        vnode.set_prop("spacing", int(spacing))
        vnode.set_prop("show_labels", bool(show_labels))
        vnode.set_prop("show_axis", bool(show_axis))
        vnode.set_prop("axis_width", int(axis_width))
        vnode.set_prop("show_grid", bool(show_grid))
        vnode.set_prop("color", color)
        vnode.set_prop("color_scale", color_scale)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_prop("bind", bind)
        vnode.set_layout(width=width, height=height)

        context.add_vnode(vnode)

        # Consume body
        caller()

        return get_element_marker(context)


class LineChartExtension(Extension):
    """Jinja2 extension for {% linechart %} tag.

    Syntax:
        {% linechart id="trend" data=points width=60 height=12
           style="line" show_axis=true show_points=false %}
        {% endlinechart %}
    """

    tags = {"linechart"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the linechart tag."""
        lineno = next(parser.stream).lineno

        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endlinechart"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        node = nodes.CallBlock(
            self.call_method("_render_linechart", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endlinechart",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_linechart(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        data: list[Any] | dict[str, list[Any]] | None = None,
        width: int = 60,
        height: int = 12,
        style: Literal["line", "area", "dots"] = "line",
        show_axis: bool = True,
        axis_width: int = 6,
        show_labels: bool = True,
        show_points: bool = False,
        show_legend: bool = True,
        color: str | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the linechart tag."""
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        if id is None:
            id = context.generate_id("linechart")

        # Get data from state if binding enabled
        if bind and id:
            try:
                if id in state:
                    data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create VNode for reconciliation
        vnode = VNodeBuilder("LineChart", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("data", data)
        vnode.set_prop("width", int(width))
        vnode.set_prop("height", int(height))
        vnode.set_prop("style", style)
        vnode.set_prop("show_axis", bool(show_axis))
        vnode.set_prop("axis_width", int(axis_width))
        vnode.set_prop("show_labels", bool(show_labels))
        vnode.set_prop("show_points", bool(show_points))
        vnode.set_prop("show_legend", bool(show_legend))
        vnode.set_prop("color", color)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_prop("bind", bind)
        vnode.set_layout(width=width, height=height)

        context.add_vnode(vnode)

        # Consume body
        caller()

        return get_element_marker(context)


class GaugeExtension(Extension):
    """Jinja2 extension for {% gauge %} tag.

    Syntax:
        {% gauge id="temp" value=75 max_value=100 width=20
           style="linear" show_value=true %}
        {% endgauge %}
    """

    tags = {"gauge"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the gauge tag."""
        lineno = next(parser.stream).lineno

        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endgauge"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        node = nodes.CallBlock(
            self.call_method("_render_gauge", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endgauge",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_gauge(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        value: float = 0,
        min_value: float = 0,
        max_value: float = 100,
        width: int = 20,
        height: int | None = None,
        style: Literal["linear", "arc"] = "linear",
        show_value: bool = True,
        show_minmax: bool = False,
        show_ticks: bool = False,
        color: Literal["default", "gradient", "threshold"] = "threshold",
        color_scale: str = "green",
        label: str | None = None,
        unit: str = "",
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the gauge tag."""
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        if id is None:
            id = context.generate_id("gauge")

        # Get value from state if binding enabled
        if bind and id:
            try:
                if id in state:
                    value = float(state[id])
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Determine actual height (Gauge computes this based on style)
        # For VNode, we'll use the requested height or let the element decide
        actual_height = int(height) if height is not None else "auto"

        # Create VNode for reconciliation
        vnode = VNodeBuilder("Gauge", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("value", float(value))
        vnode.set_prop("min_value", float(min_value))
        vnode.set_prop("max_value", float(max_value))
        vnode.set_prop("width", int(width))
        if height is not None:
            vnode.set_prop("height", int(height))
        vnode.set_prop("style", style)
        vnode.set_prop("show_value", bool(show_value))
        vnode.set_prop("show_minmax", bool(show_minmax))
        vnode.set_prop("show_ticks", bool(show_ticks))
        vnode.set_prop("color", color)
        vnode.set_prop("color_scale", color_scale)
        if label:
            vnode.set_prop("label", label)
        if unit:
            vnode.set_prop("unit", unit)
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_prop("bind", bind)
        vnode.set_layout(width=width, height=actual_height)

        context.add_vnode(vnode)

        # Consume body
        caller()

        return get_element_marker(context)


class HeatMapExtension(Extension):
    """Jinja2 extension for {% heatmap %} tag.

    Syntax:
        {% heatmap id="activity" data=grid width=40 height=10
           color_scale="heat" show_legend=true %}
        {% endheatmap %}
    """

    tags = {"heatmap"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the heatmap tag."""
        lineno = next(parser.stream).lineno

        kwargs: list[nodes.Keyword] = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endheatmap"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        node = nodes.CallBlock(
            self.call_method("_render_heatmap", [], kwargs),
            [],
            [],
            parser.parse_statements(("name:endheatmap",), drop_needle=True),
        ).set_lineno(lineno)

        return cast(nodes.CallBlock, node)

    def _render_heatmap(
        self,
        caller: Callable[[], str],
        id: str | None = None,
        data: list[list[float | int]] | None = None,
        width: int = 40,
        height: int = 10,
        cell_width: int = 2,
        cell_height: int = 1,
        color_scale: Literal["green", "red", "blue", "heat", "cool"] = "heat",
        show_values: bool = False,
        show_legend: bool = True,
        show_labels: bool = False,
        row_labels: list[str] | None = None,
        col_labels: list[str] | None = None,
        min_value: float | None = None,
        max_value: float | None = None,
        bind: bool = True,
        **kwargs: Any,
    ) -> str:
        """Render the heatmap tag."""
        classes = kwargs.get("class", None)

        # Get layout context from RenderContext
        render_ctx = get_render_context()
        context = render_ctx.layout_context
        state = render_ctx.state

        if id is None:
            id = context.generate_id("heatmap")

        # Get data from state if binding enabled
        if bind and id:
            try:
                if id in state:
                    data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        # Create VNode for reconciliation
        vnode = VNodeBuilder("HeatMap", key=id)
        vnode.set_prop("id", id)
        vnode.set_prop("data", data or [])
        vnode.set_prop("width", int(width))
        vnode.set_prop("height", int(height))
        vnode.set_prop("cell_width", int(cell_width))
        vnode.set_prop("cell_height", int(cell_height))
        vnode.set_prop("color_scale", color_scale)
        vnode.set_prop("show_values", bool(show_values))
        vnode.set_prop("show_legend", bool(show_legend))
        vnode.set_prop("show_labels", bool(show_labels))
        if row_labels:
            vnode.set_prop("row_labels", row_labels)
        if col_labels:
            vnode.set_prop("col_labels", col_labels)
        if min_value is not None:
            vnode.set_prop("min_value", float(min_value))
        if max_value is not None:
            vnode.set_prop("max_value", float(max_value))
        if classes:
            vnode.set_prop("classes", classes)
        vnode.set_prop("bind", bind)
        vnode.set_layout(width=width, height=height)

        context.add_vnode(vnode)

        # Consume body
        caller()

        return get_element_marker(context)


# List of all chart extensions for easy registration
CHART_EXTENSIONS = [
    SparklineExtension,
    BarChartExtension,
    ColumnChartExtension,
    LineChartExtension,
    GaugeExtension,
    HeatMapExtension,
]
