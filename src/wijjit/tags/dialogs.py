"""Jinja2 extensions for pre-built dialog tags.

This module provides template tags for confirm, alert, and text input dialogs.
"""

from jinja2 import nodes
from jinja2.ext import Extension

from wijjit.core.overlay import LayerType
from wijjit.elements.modal import AlertDialog, ConfirmDialog, TextInputDialog
from wijjit.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


class ConfirmDialogExtension(Extension):
    """Jinja2 extension for {% confirmdialog %} tag.

    Creates a confirmation dialog with confirm/cancel buttons.

    Syntax:
        {% confirmdialog visible="show_confirm"
                         title="Confirm Delete"
                         message="Are you sure you want to delete this file?"
                         confirm_action="handle_confirm"
                         cancel_action="handle_cancel"
                         confirm_label="Delete"
                         cancel_label="Cancel" %}
        {% endconfirmdialog %}

        Or with body content as message:
        {% confirmdialog visible="show_confirm"
                         title="Confirm Action"
                         confirm_action="confirm"
                         cancel_action="cancel" %}
            Are you sure you want to proceed with this action?
        {% endconfirmdialog %}
    """

    tags = {"confirmdialog"}

    def parse(self, parser):
        """Parse the confirmdialog tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endconfirmdialog"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (optional message content)
        node = nodes.CallBlock(
            self.call_method("_render_confirmdialog", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endconfirmdialog"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_confirmdialog(
        self,
        caller,
        id=None,
        visible=None,
        title="Confirm",
        message=None,
        confirm_action=None,
        cancel_action=None,
        confirm_label="Confirm",
        cancel_label="Cancel",
        width=50,
        height=10,
        border="single",
    ) -> str:
        """Render the confirmdialog tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        visible : str, optional
            State key name for visibility control
        title : str
            Dialog title (default: "Confirm")
        message : str, optional
            Confirmation message (if not provided in body)
        confirm_action : str, optional
            Action ID to dispatch when confirm button is clicked
        cancel_action : str, optional
            Action ID to dispatch when cancel button is clicked
        confirm_label : str
            Confirm button label (default: "Confirm")
        cancel_label : str
            Cancel button label (default: "Cancel")
        width : int
            Dialog width (default: 50)
        height : int
            Dialog height (default: 10)
        border : str
            Border style (default: "single")

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Check visibility state
        is_visible = False
        if visible:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    is_visible = bool(state.get(visible, False))
            except Exception as e:
                logger.warning(f"Failed to check visibility state: {e}")

        # If not visible, don't create the dialog
        if not is_visible:
            # Still consume body
            caller()
            return ""

        # Get message from body if not provided as attribute
        if message is None:
            message = caller().strip()
        else:
            # Message provided as attribute, consume body anyway
            caller()

        # Convert numeric parameters
        width = int(width)
        height = int(height)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("confirmdialog")

        # Create confirm dialog
        dialog = ConfirmDialog(
            message=message,
            title=title,
            confirm_label=confirm_label,
            cancel_label=cancel_label,
            width=width,
            height=height,
            border=border,
        )

        # Set action IDs on buttons if provided
        if confirm_action:
            dialog.confirm_button.action = confirm_action
        if cancel_action:
            dialog.cancel_button.action = cancel_action

        # Store overlay info for app to register
        overlay_info = {
            "element": dialog,
            "layer_type": LayerType.MODAL,
            "close_on_escape": True,
            "close_on_click_outside": False,
            "trap_focus": True,
            "dim_background": True,
            "visible_state_key": visible,
        }

        # Add to context's overlay list
        if not hasattr(context, "_overlays"):
            context._overlays = []
        context._overlays.append(overlay_info)

        return ""


class AlertDialogExtension(Extension):
    """Jinja2 extension for {% alertdialog %} tag.

    Creates an alert dialog with a single OK button.

    Syntax:
        {% alertdialog visible="show_alert"
                       title="Success"
                       message="File saved successfully!"
                       ok_action="dismiss_alert"
                       ok_label="OK" %}
        {% endalertdialog %}

        Or with body content as message:
        {% alertdialog visible="show_alert"
                       title="Information"
                       ok_action="dismiss" %}
            Your changes have been saved.
        {% endalertdialog %}
    """

    tags = {"alertdialog"}

    def parse(self, parser):
        """Parse the alertdialog tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endalertdialog"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (optional message content)
        node = nodes.CallBlock(
            self.call_method("_render_alertdialog", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endalertdialog"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_alertdialog(
        self,
        caller,
        id=None,
        visible=None,
        title="Alert",
        message=None,
        ok_action=None,
        ok_label="OK",
        width=50,
        height=8,
        border="single",
    ) -> str:
        """Render the alertdialog tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        visible : str, optional
            State key name for visibility control
        title : str
            Dialog title (default: "Alert")
        message : str, optional
            Alert message (if not provided in body)
        ok_action : str, optional
            Action ID to dispatch when OK button is clicked
        ok_label : str
            OK button label (default: "OK")
        width : int
            Dialog width (default: 50)
        height : int
            Dialog height (default: 8)
        border : str
            Border style (default: "single")

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Check visibility state
        is_visible = False
        if visible:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    is_visible = bool(state.get(visible, False))
            except Exception as e:
                logger.warning(f"Failed to check visibility state: {e}")

        # If not visible, don't create the dialog
        if not is_visible:
            # Still consume body
            caller()
            return ""

        # Get message from body if not provided as attribute
        if message is None:
            message = caller().strip()
        else:
            # Message provided as attribute, consume body anyway
            caller()

        # Convert numeric parameters
        width = int(width)
        height = int(height)

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("alertdialog")

        # Create alert dialog
        dialog = AlertDialog(
            message=message,
            title=title,
            ok_label=ok_label,
            width=width,
            height=height,
            border=border,
        )

        # Set action ID on button if provided
        if ok_action:
            dialog.ok_button.action = ok_action

        # Store overlay info for app to register
        overlay_info = {
            "element": dialog,
            "layer_type": LayerType.MODAL,
            "close_on_escape": True,
            "close_on_click_outside": False,
            "trap_focus": True,
            "dim_background": True,
            "visible_state_key": visible,
        }

        # Add to context's overlay list
        if not hasattr(context, "_overlays"):
            context._overlays = []
        context._overlays.append(overlay_info)

        return ""


class TextInputDialogExtension(Extension):
    """Jinja2 extension for {% inputdialog %} tag.

    Creates a text input dialog with submit/cancel buttons.

    Syntax:
        {% inputdialog visible="show_rename"
                       title="Rename File"
                       prompt="Enter new name:"
                       initial_value="{{ state.current_filename }}"
                       submit_action="do_rename"
                       cancel_action="cancel_rename"
                       placeholder="filename.txt"
                       submit_label="Rename"
                       cancel_label="Cancel" %}
        {% endinputdialog %}
    """

    tags = {"inputdialog"}

    def parse(self, parser):
        """Parse the inputdialog tag.

        Parameters
        ----------
        parser : jinja2.parser.Parser
            Jinja2 parser

        Returns
        -------
        jinja2.nodes.CallBlock
            Parsed node tree
        """
        lineno = next(parser.stream).lineno

        # Parse attributes as keyword arguments
        kwargs = []
        while parser.stream.current.test("name") and not parser.stream.current.test(
            "name:endinputdialog"
        ):
            key = parser.stream.expect("name").value
            if parser.stream.current.test("assign"):
                parser.stream.expect("assign")
                value = parser.parse_expression()
                kwargs.append(nodes.Keyword(key, value, lineno=lineno))
            else:
                break

        # Parse body (should be empty for input dialog)
        node = nodes.CallBlock(
            self.call_method("_render_inputdialog", [], kwargs),
            [],
            [],
            parser.parse_statements(["name:endinputdialog"], drop_needle=True),
        ).set_lineno(lineno)

        return node

    def _render_inputdialog(
        self,
        caller,
        id=None,
        visible=None,
        title="Input",
        prompt="Enter value:",
        initial_value="",
        submit_action=None,
        cancel_action=None,
        placeholder="",
        submit_label="Submit",
        cancel_label="Cancel",
        width=50,
        height=12,
        border="single",
        input_width=30,
    ) -> str:
        """Render the inputdialog tag.

        Parameters
        ----------
        caller : callable
            Jinja2 caller for body content
        id : str, optional
            Element identifier
        visible : str, optional
            State key name for visibility control
        title : str
            Dialog title (default: "Input")
        prompt : str
            Input prompt (default: "Enter value:")
        initial_value : str
            Initial text input value (default: "")
        submit_action : str, optional
            Action ID to dispatch when submit button is clicked
        cancel_action : str, optional
            Action ID to dispatch when cancel button is clicked
        placeholder : str
            Input placeholder text (default: "")
        submit_label : str
            Submit button label (default: "Submit")
        cancel_label : str
            Cancel button label (default: "Cancel")
        width : int
            Dialog width (default: 50)
        height : int
            Dialog height (default: 12)
        border : str
            Border style (default: "single")
        input_width : int
            Text input width (default: 30)

        Returns
        -------
        str
            Rendered output
        """
        # Get layout context from environment globals
        context = self.environment.globals.get("_wijjit_layout_context")
        if context is None:
            return ""

        # Check visibility state
        is_visible = False
        if visible:
            try:
                ctx = self.environment.globals.get("_wijjit_current_context")
                if ctx and "state" in ctx:
                    state = ctx["state"]
                    is_visible = bool(state.get(visible, False))
            except Exception as e:
                logger.warning(f"Failed to check visibility state: {e}")

        # If not visible, don't create the dialog
        if not is_visible:
            # Still consume body
            caller()
            return ""

        # Convert numeric parameters
        width = int(width)
        height = int(height)
        input_width = int(input_width)

        # Consume body (should be empty)
        caller()

        # Auto-generate ID if not provided
        if id is None:
            id = context.generate_id("inputdialog")

        # Create text input dialog
        dialog = TextInputDialog(
            prompt=prompt,
            initial_value=str(initial_value),
            title=title,
            placeholder=placeholder,
            submit_label=submit_label,
            cancel_label=cancel_label,
            width=width,
            height=height,
            border=border,
            input_width=input_width,
        )

        # Set action IDs on buttons if provided
        if submit_action:
            dialog.submit_button.action = submit_action
        if cancel_action:
            dialog.cancel_button.action = cancel_action

        # Store overlay info for app to register
        overlay_info = {
            "element": dialog,
            "layer_type": LayerType.MODAL,
            "close_on_escape": True,
            "close_on_click_outside": False,
            "trap_focus": True,
            "dim_background": True,
            "visible_state_key": visible,
        }

        # Add to context's overlay list
        if not hasattr(context, "_overlays"):
            context._overlays = []
        context._overlays.append(overlay_info)

        return ""
