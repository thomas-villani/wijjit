"""Element wiring manager for callback and state binding.

This module provides the ElementWiringManager class which handles wiring
callbacks for interactive elements, state bindings, and menu shortcuts.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wijjit.core.events import HandlerScope
from wijjit.elements.display.tree import Tree
from wijjit.elements.input.button import Button
from wijjit.elements.input.checkbox import Checkbox, CheckboxGroup
from wijjit.elements.input.radio import Radio, RadioGroup
from wijjit.elements.input.select import Select
from wijjit.elements.input.text import TextInput
from wijjit.elements.menu import ContextMenu, DropdownMenu, MenuElement
from wijjit.logging_config import get_logger

if TYPE_CHECKING:
    from wijjit.core.app import Wijjit
    from wijjit.core.state import State
    from wijjit.elements.base import Element, ScrollableElement

logger = get_logger(__name__)


class ElementWiringManager:
    """Manages element callback wiring and state binding.

    This manager is responsible for:
    - Wiring action callbacks for buttons
    - Binding state to inputs (two-way data binding)
    - Registering menu shortcuts
    - Managing scroll position persistence
    - Managing highlight state for selectable elements

    Parameters
    ----------
    app : Wijjit
        Reference to the main application

    Attributes
    ----------
    app : Wijjit
        Application reference
    _registered_menuitem_shortcuts : set[str]
        Set of registered menu item shortcut handler IDs
    _registered_menu_shortcuts : set[str]
        Set of registered menu trigger shortcut handler IDs
    """

    def __init__(self, app: Wijjit) -> None:
        """Initialize the element wiring manager.

        Parameters
        ----------
        app : Wijjit
            Reference to the main application
        """
        self.app = app
        self._registered_menuitem_shortcuts: set[str] = set()
        self._registered_menu_shortcuts: set[str] = set()

    def clear_view_shortcuts(self) -> None:
        """Clear shortcut tracking sets when navigating away from view.

        This method clears the internal tracking sets used to prevent
        duplicate handler registration within a single view render.

        Note: With VIEW-scoped handlers, the actual handler cleanup is
        handled automatically by handler_registry.clear_view(). This method
        primarily resets the duplicate-detection sets for the next view.
        """
        self._registered_menuitem_shortcuts.clear()
        self._registered_menu_shortcuts.clear()

    def wire_elements(
        self,
        elements: list[Element],
        state: State,
    ) -> None:
        """Wire callbacks for all elements.

        This method wires up action callbacks, state bindings, and
        menu shortcuts for all positioned elements.

        Parameters
        ----------
        elements : list[Element]
            List of positioned elements to wire
        state : State
            Application state for bindings
        """
        for elem in elements:
            self._wire_element(elem, state)

    def _wire_element(self, elem: Element, state: State) -> None:
        """Wire callbacks for a single element.

        Parameters
        ----------
        elem : Element
            Element to wire
        state : State
            Application state
        """
        # Wire up action callbacks for buttons
        if isinstance(elem, Button) and hasattr(elem, "action") and elem.action:
            action_id = elem.action
            # Pass the ActionEvent through, but use the action from the element
            elem.on_activate = lambda event, aid=action_id: self.app._dispatch_action(
                aid, event=event
            )

        # Wire up TextInput callbacks
        if isinstance(elem, TextInput):
            self._wire_textinput(elem, state)

        # Wire up Select callbacks
        if isinstance(elem, Select):
            self._wire_select(elem, state)

        # Wire up scroll position persistence for all ScrollableElement elements
        from wijjit.elements.base import ScrollableElement

        if isinstance(elem, ScrollableElement):
            self._wire_scrollable(elem, state)

        # Wire up Tree callbacks
        if isinstance(elem, Tree):
            self._wire_tree(elem, state)

        # Wire up Checkbox callbacks
        if isinstance(elem, Checkbox):
            self._wire_checkbox(elem, state)

        # Wire up Radio callbacks
        if isinstance(elem, Radio):
            self._wire_radio(elem, state)

        # Wire up CheckboxGroup callbacks
        if isinstance(elem, CheckboxGroup):
            self._wire_checkbox_group(elem, state)

        # Wire up RadioGroup callbacks
        if isinstance(elem, RadioGroup):
            self._wire_radio_group(elem, state)

    def _wire_textinput(self, elem: TextInput, state: State) -> None:
        """Wire TextInput callbacks.

        Parameters
        ----------
        elem : TextInput
            TextInput element to wire
        state : State
            Application state
        """
        # Wire up action callback if action is specified
        if hasattr(elem, "action") and elem.action:
            action_id = elem.action
            elem.on_action = lambda aid=action_id: self.app._dispatch_action(aid)

        # Wire up state binding if enabled
        if hasattr(elem, "bind") and elem.bind and elem.id:
            # Initialize element value from state if key exists
            if elem.id in state:
                elem.value = str(state[elem.id])
                elem.cursor_pos = len(elem.value)

            # Set up two-way binding
            elem_id = elem.id

            def on_change_handler(old_val, new_val, eid=elem_id):
                # Update state when element changes
                state[eid] = new_val

            elem.on_change = on_change_handler

    def _wire_select(self, elem: Select, state: State) -> None:
        """Wire Select callbacks.

        Parameters
        ----------
        elem : Select
            Select element to wire
        state : State
            Application state
        """
        # Wire up action callback if action is specified
        if hasattr(elem, "action") and elem.action:
            action_id = elem.action
            elem.on_action = lambda aid=action_id: self.app._dispatch_action(aid)

        # Wire up state binding if enabled
        if hasattr(elem, "bind") and elem.bind and elem.id:
            # Initialize element value from state if key exists
            if elem.id in state:
                elem.value = state[elem.id]
                # Update selected_index to match the value
                elem.selected_index = elem._find_option_index(elem.value)

            # Set up two-way binding
            elem_id = elem.id

            def on_change_handler(old_val, new_val, eid=elem_id):
                # Update state when element changes
                state[eid] = new_val

            elem.on_change = on_change_handler

        # Wire up highlighted_index persistence if element has the state key
        if hasattr(elem, "highlight_state_key") and elem.highlight_state_key:
            highlight_key = elem.highlight_state_key

            def on_highlight_handler(new_index, hkey=highlight_key):
                # Update state when highlight changes
                state[hkey] = new_index

            elem.on_highlight_change = on_highlight_handler

    def _wire_scrollable(self, elem: ScrollableElement, state: State) -> None:
        """Wire scroll position persistence for ScrollableElement elements.

        Parameters
        ----------
        elem : ScrollableElement
            Scrollable element to wire
        state : State
            Application state
        """
        if hasattr(elem, "scroll_state_key") and elem.scroll_state_key:
            scroll_key = elem.scroll_state_key

            def on_scroll_handler(position, skey=scroll_key):
                # Update state when scroll position changes
                state[skey] = position

            elem.on_scroll = on_scroll_handler

    def _wire_tree(self, elem: Tree, state: State) -> None:
        """Wire Tree callbacks.

        Parameters
        ----------
        elem : Tree
            Tree element to wire
        state : State
            Application state
        """
        # Wire up action callback if action is specified
        if hasattr(elem, "action") and elem.action:
            action_id = elem.action

            def on_select_handler(node, aid=action_id):
                # Dispatch action with node data
                self.app._dispatch_action(aid, data=node)

            elem.on_select = on_select_handler

    def _wire_checkbox(self, elem: Checkbox, state: State) -> None:
        """Wire Checkbox callbacks.

        Parameters
        ----------
        elem : Checkbox
            Checkbox element to wire
        state : State
            Application state
        """
        # Wire up action callback if action is specified
        if hasattr(elem, "action") and elem.action:
            action_id = elem.action
            elem.on_action = lambda aid=action_id: self.app._dispatch_action(aid)

        # Wire up state binding if enabled
        if hasattr(elem, "bind") and elem.bind and elem.id:
            # Initialize element checked state from state if key exists
            if elem.id in state:
                elem.checked = bool(state[elem.id])

            # Set up two-way binding
            elem_id = elem.id

            def on_change_handler(old_val, new_val, eid=elem_id):
                # Update state when element changes
                state[eid] = new_val

            elem.on_change = on_change_handler

    def _wire_radio(self, elem: Radio, state: State) -> None:
        """Wire Radio callbacks.

        Parameters
        ----------
        elem : Radio
            Radio element to wire
        state : State
            Application state
        """
        # Wire up action callback if action is specified
        if hasattr(elem, "action") and elem.action:
            action_id = elem.action
            elem.on_action = lambda aid=action_id: self.app._dispatch_action(aid)

        # Wire up state binding if enabled (bind to group name, not id)
        if hasattr(elem, "bind") and elem.bind and elem.name:
            # Initialize element checked state from state[name]
            if elem.name in state:
                elem.checked = state[elem.name] == elem.value

            # Set up two-way binding
            radio_name = elem.name
            radio_value = elem.value

            def on_change_handler(old_val, new_val, rname=radio_name, rval=radio_value):
                # Update state when radio is selected
                if new_val:  # Only update state when radio is selected (not deselected)
                    state[rname] = rval

            elem.on_change = on_change_handler

    def _wire_checkbox_group(self, elem: CheckboxGroup, state: State) -> None:
        """Wire CheckboxGroup callbacks.

        Parameters
        ----------
        elem : CheckboxGroup
            CheckboxGroup element to wire
        state : State
            Application state
        """
        # Wire up action callback if action is specified
        if hasattr(elem, "action") and elem.action:
            action_id = elem.action
            elem.on_action = lambda aid=action_id: self.app._dispatch_action(aid)

        # Wire up state binding if enabled
        if hasattr(elem, "bind") and elem.bind and elem.id:
            # Initialize element selected values from state if key exists
            if elem.id in state:
                elem.selected_values = set(state[elem.id])

            # Set up two-way binding
            elem_id = elem.id

            def on_change_handler(old_val, new_val, eid=elem_id):
                # Update state when element changes
                state[eid] = new_val

            elem.on_change = on_change_handler

        # Wire up highlighted_index persistence if element has the state key
        if hasattr(elem, "highlight_state_key") and elem.highlight_state_key:
            highlight_key = elem.highlight_state_key

            def on_highlight_handler(new_index, hkey=highlight_key):
                # Update state when highlight changes
                state[hkey] = new_index

            elem.on_highlight_change = on_highlight_handler

    def _wire_radio_group(self, elem: RadioGroup, state: State) -> None:
        """Wire RadioGroup callbacks.

        Parameters
        ----------
        elem : RadioGroup
            RadioGroup element to wire
        state : State
            Application state
        """
        # Wire up action callback if action is specified
        if hasattr(elem, "action") and elem.action:
            action_id = elem.action
            elem.on_action = lambda aid=action_id: self.app._dispatch_action(aid)

        # Wire up state binding if enabled (bind to group name)
        if hasattr(elem, "bind") and elem.bind and elem.name:
            # Initialize element selected value from state[name]
            if elem.name in state:
                elem.selected_value = state[elem.name]
                elem.selected_index = elem._find_option_index(elem.selected_value)

            # Set up two-way binding
            group_name = elem.name

            def on_change_handler(old_val, new_val, gname=group_name):
                # Update state when element changes
                state[gname] = new_val

            elem.on_change = on_change_handler

        # Wire up highlighted_index persistence if element has the state key
        if hasattr(elem, "highlight_state_key") and elem.highlight_state_key:
            highlight_key = elem.highlight_state_key

            def on_highlight_handler(new_index, hkey=highlight_key):
                # Update state when highlight changes
                state[hkey] = new_index

            elem.on_highlight_change = on_highlight_handler

    def wire_menu_elements(
        self,
        menu_elements: list[tuple[MenuElement, dict[str, Any]]],
        dropdown_state_keys: list[str],
        elements: list[Element],
        state: State,
        event_type: Any,
        handler_scope: Any,
    ) -> None:
        """Wire menu element callbacks and shortcuts.

        Parameters
        ----------
        menu_elements : list[tuple[MenuElement, dict]]
            List of (menu_element, overlay_info) tuples
        dropdown_state_keys : list[str]
            List of dropdown menu visibility state keys for mutual exclusion
        elements : list[Element]
            List of all positioned elements (for finding trigger buttons)
        state : State
            Application state
        event_type : EventType
            EventType.KEY for shortcut registration
        handler_scope : HandlerScope
            HandlerScope.GLOBAL for shortcut registration
        """
        for elem, overlay_info in menu_elements:
            # Wire up menu item selection callback
            def on_item_select_handler(action_id: str, item):
                # Dispatch action
                self.app._dispatch_action(action_id)

            elem.on_item_select = on_item_select_handler

            # Wire up close callback - set visibility state to False
            visible_state_key = overlay_info.get("visible_state_key")

            def make_close_callback(state_key):
                def close_menu():
                    if state_key:
                        state[state_key] = False

                return close_menu

            elem.close_callback = make_close_callback(visible_state_key)

            # Register global keyboard shortcuts for menu items (e.g., Ctrl+N)
            for item in elem.items:
                if item.key and item.action and not item.disabled:
                    shortcut_key = item.key.lower()
                    action_id = item.action

                    # Validate that Ctrl+C is not being bound (reserved for app exit)
                    if shortcut_key in ("ctrl+c", "c-c"):
                        logger.warning(
                            f"Cannot bind Ctrl+C to action '{action_id}': "
                            "Ctrl+C is reserved for exiting the application. Skipping."
                        )
                        continue

                    # Check if we already registered this shortcut
                    handler_id = f"menuitem_shortcut_{action_id}_{shortcut_key}"
                    if handler_id not in self._registered_menuitem_shortcuts:
                        self._registered_menuitem_shortcuts.add(handler_id)

                        def make_shortcut_handler(act_id, key_combo):
                            def handle_shortcut(event):
                                # Check if this is the right key
                                if event.key.lower() == key_combo:
                                    # Dispatch the action
                                    self.app._dispatch_action(act_id)

                            return handle_shortcut

                        # Register the key handler with VIEW scope to auto-clear on navigation
                        self.app.on(
                            event_type,
                            make_shortcut_handler(action_id, shortcut_key),
                            scope=HandlerScope.VIEW,
                            view_name=self.app.current_view,
                        )

            # For context menus, check if we need to update mouse position
            if isinstance(elem, ContextMenu):
                # Mouse position will be set by right-click handler
                # But we need to recalculate bounds if position was set
                if elem.mouse_position:
                    elem.bounds = self.app.overlay_manager._calculate_menu_position(
                        elem
                    )

            # For dropdowns, try to find trigger button and set bounds
            if isinstance(elem, DropdownMenu):
                logger.debug(
                    f"Found DropdownMenu: id={elem.id}, trigger_text={elem.trigger_text}, "
                    f"trigger_key={elem.trigger_key}"
                )
                trigger_text = elem.trigger_text
                # Look for a button with matching label
                for el in elements:
                    if isinstance(el, Button) and hasattr(el, "label"):
                        if el.label == trigger_text and el.bounds:
                            elem.trigger_bounds = el.bounds
                            # Recalculate menu position
                            elem.bounds = (
                                self.app.overlay_manager._calculate_menu_position(elem)
                            )
                            break

                # Register keyboard shortcut if specified (e.g., Alt+F)
                if elem.trigger_key and hasattr(elem, "id") and elem.id:
                    if visible_state_key:
                        trigger_key = elem.trigger_key.lower()

                        # Validate that Ctrl+C is not being bound (reserved for app exit)
                        if trigger_key in ("ctrl+c", "c-c"):
                            logger.warning(
                                f"Cannot bind Ctrl+C to dropdown menu '{elem.id}': "
                                "Ctrl+C is reserved for exiting the application. Skipping."
                            )
                            continue

                        # Check if we already registered this handler
                        handler_id = f"menu_shortcut_{elem.id}"
                        if handler_id not in self._registered_menu_shortcuts:
                            self._registered_menu_shortcuts.add(handler_id)

                            # Debug logging
                            logger.debug(
                                f"Registering menu trigger shortcut: {trigger_key} "
                                f"for menu {elem.id} (state: {visible_state_key})"
                            )

                            def make_key_handler(
                                state_key, key_combo, all_dropdown_keys
                            ):
                                def toggle_menu(event):
                                    # Debug logging
                                    logger.debug(
                                        f"Key event: {event.key!r}, "
                                        f"comparing to {key_combo!r}"
                                    )
                                    # Check if this is the right key
                                    if event.key.lower() == key_combo:
                                        logger.debug(f"Matched! Toggling {state_key}")
                                        # Close all other dropdown menus first
                                        for other_key in all_dropdown_keys:
                                            if other_key != state_key:
                                                state[other_key] = False

                                        # Toggle current menu visibility
                                        current = state.get(state_key, False)
                                        state[state_key] = not current

                                return toggle_menu

                            # Register the key handler with VIEW scope to auto-clear on navigation
                            self.app.on(
                                event_type,
                                make_key_handler(
                                    visible_state_key, trigger_key, dropdown_state_keys
                                ),
                                scope=HandlerScope.VIEW,
                                view_name=self.app.current_view,
                            )
