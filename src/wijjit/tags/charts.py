"""Jinja2 template extensions for chart elements.

This module provides Jinja2 extensions for data visualization elements
including sparklines, bar charts, column charts, line charts, gauges, and heat maps.
"""

from collections.abc import Callable
from typing import Any, Literal, cast

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser

from wijjit.elements.display.barchart import BarChart
from wijjit.elements.display.columnchart import ColumnChart
from wijjit.elements.display.gauge import Gauge
from wijjit.elements.display.heatmap import HeatMap
from wijjit.elements.display.linechart import LineChart
from wijjit.elements.display.sparkline import Sparkline
from wijjit.layout.engine import ElementNode
from wijjit.logging_config import get_logger
from wijjit.tags.layout import LayoutContext, get_element_marker

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

        context = cast(
            LayoutContext | None, self.environment.globals.get("_wijjit_layout_context")
        )
        if context is None:
            return ""

        if id is None:
            id = context.generate_id("sparkline")

        # Get data from state if binding enabled
        if bind and id:
            try:
                ctx = cast(
                    dict[str, Any] | None,
                    self.environment.globals.get("_wijjit_current_context"),
                )
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        element = Sparkline(
            id=id,
            classes=classes,
            data=data or [],
            width=int(width),
            height=int(height),
            style=style,
            show_minmax=bool(show_minmax),
            show_current=bool(show_current),
            color=color,
        )

        element.bind = bind

        element_node = ElementNode(element, width=width, height=height)
        context.add_element(element_node)

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

        context = cast(
            LayoutContext | None, self.environment.globals.get("_wijjit_layout_context")
        )
        if context is None:
            return ""

        if id is None:
            id = context.generate_id("barchart")

        # Get data from state if binding enabled
        if bind and id:
            try:
                ctx = cast(
                    dict[str, Any] | None,
                    self.environment.globals.get("_wijjit_current_context"),
                )
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        element = BarChart(
            id=id,
            classes=classes,
            data=data or [],
            width=int(width),
            height=int(height),
            bar_height=int(bar_height),
            show_labels=bool(show_labels),
            show_values=bool(show_values),
            label_width=int(label_width) if label_width is not None else None,
            value_width=int(value_width),
            color=color,
            color_scale=color_scale,
            show_scrollbar=bool(show_scrollbar),
            show_border=bool(show_border),
        )

        element.bind = bind

        element_node = ElementNode(element, width=width, height=height)
        context.add_element(element_node)

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

        context = cast(
            LayoutContext | None, self.environment.globals.get("_wijjit_layout_context")
        )
        if context is None:
            return ""

        if id is None:
            id = context.generate_id("columnchart")

        # Get data from state if binding enabled
        if bind and id:
            try:
                ctx = cast(
                    dict[str, Any] | None,
                    self.environment.globals.get("_wijjit_current_context"),
                )
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        element = ColumnChart(
            id=id,
            classes=classes,
            data=data or [],
            width=int(width),
            height=int(height),
            column_width=int(column_width),
            spacing=int(spacing),
            show_labels=bool(show_labels),
            show_axis=bool(show_axis),
            axis_width=int(axis_width),
            show_grid=bool(show_grid),
            color=color,
            color_scale=color_scale,
        )

        element.bind = bind

        element_node = ElementNode(element, width=width, height=height)
        context.add_element(element_node)

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

        context = cast(
            LayoutContext | None, self.environment.globals.get("_wijjit_layout_context")
        )
        if context is None:
            return ""

        if id is None:
            id = context.generate_id("linechart")

        # Get data from state if binding enabled
        if bind and id:
            try:
                ctx = cast(
                    dict[str, Any] | None,
                    self.environment.globals.get("_wijjit_current_context"),
                )
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        element = LineChart(
            id=id,
            classes=classes,
            data=data,
            width=int(width),
            height=int(height),
            style=style,
            show_axis=bool(show_axis),
            axis_width=int(axis_width),
            show_labels=bool(show_labels),
            show_points=bool(show_points),
            show_legend=bool(show_legend),
            color=color,
        )

        element.bind = bind

        element_node = ElementNode(element, width=width, height=height)
        context.add_element(element_node)

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

        context = cast(
            LayoutContext | None, self.environment.globals.get("_wijjit_layout_context")
        )
        if context is None:
            return ""

        if id is None:
            id = context.generate_id("gauge")

        # Get value from state if binding enabled
        if bind and id:
            try:
                ctx = cast(
                    dict[str, Any] | None,
                    self.environment.globals.get("_wijjit_current_context"),
                )
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        value = float(state[id])
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        element = Gauge(
            id=id,
            classes=classes,
            value=float(value),
            min_value=float(min_value),
            max_value=float(max_value),
            width=int(width),
            height=int(height) if height is not None else None,
            style=style,
            show_value=bool(show_value),
            show_minmax=bool(show_minmax),
            show_ticks=bool(show_ticks),
            color=color,
            color_scale=color_scale,
            label=label,
            unit=unit,
        )

        element.bind = bind

        actual_height = element.height
        element_node = ElementNode(element, width=width, height=actual_height)
        context.add_element(element_node)

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

        context = cast(
            LayoutContext | None, self.environment.globals.get("_wijjit_layout_context")
        )
        if context is None:
            return ""

        if id is None:
            id = context.generate_id("heatmap")

        # Get data from state if binding enabled
        if bind and id:
            try:
                ctx = cast(
                    dict[str, Any] | None,
                    self.environment.globals.get("_wijjit_current_context"),
                )
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    if id in state:
                        data = state[id]
            except Exception as e:
                logger.warning(f"Failed to restore state: {e}")

        element = HeatMap(
            id=id,
            classes=classes,
            data=data or [],
            width=int(width),
            height=int(height),
            cell_width=int(cell_width),
            cell_height=int(cell_height),
            color_scale=color_scale,
            show_values=bool(show_values),
            show_legend=bool(show_legend),
            show_labels=bool(show_labels),
            row_labels=row_labels,
            col_labels=col_labels,
            min_value=float(min_value) if min_value is not None else None,
            max_value=float(max_value) if max_value is not None else None,
        )

        element.bind = bind

        element_node = ElementNode(element, width=width, height=height)
        context.add_element(element_node)

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
