"""Overlay/display callbacks route through invoke_callback (audit CC-8).

These six sites previously called user callbacks directly, so an ``async def``
handler became a coroutine that was created and never awaited (silently
dropped). They now go through ``invoke_callback``, which schedules async
handlers on the running loop and calls sync handlers immediately. Each test
attaches an *async* handler, triggers the code path, and asserts the coroutine
actually ran.
"""

import asyncio

import pytest

from wijjit.elements.display.notification import NotificationElement
from wijjit.elements.display.pager import Page, Pager
from wijjit.elements.display.tabbed_panel import TabbedPanel
from wijjit.elements.menu import MenuElement, MenuItem
from wijjit.layout.frames import Frame


@pytest.mark.asyncio
async def test_notification_action_callback_awaits_async_handler():
    """Notification action_callback + on_dismiss run async handlers."""
    action_ran = asyncio.Event()
    dismiss_ran = asyncio.Event()

    async def on_action():
        action_ran.set()

    async def on_dismiss():
        dismiss_ran.set()

    notif = NotificationElement(message="Hi")
    notif.action_callback = on_action
    notif.on_dismiss = on_dismiss
    notif.dismiss_on_action = True

    notif._handle_action_click()

    await asyncio.wait_for(action_ran.wait(), timeout=1.0)
    await asyncio.wait_for(dismiss_ran.wait(), timeout=1.0)


@pytest.mark.asyncio
async def test_pager_on_page_change_awaits_async_handler():
    """Pager.go_to_page fires an async on_page_change."""
    ran = asyncio.Event()

    async def on_page_change(old, new):
        ran.set()

    pager = Pager()
    pager.add_page(Page(title="One", content="1"))
    pager.add_page(Page(title="Two", content="2"))
    pager.on_page_change = on_page_change

    pager.go_to_page(1)

    await asyncio.wait_for(ran.wait(), timeout=1.0)


@pytest.mark.asyncio
async def test_tabbed_panel_on_tab_change_awaits_async_handler():
    """TabbedPanel.switch_to_tab fires an async on_tab_change."""
    ran = asyncio.Event()

    async def on_tab_change(index, label):
        ran.set()

    panel = TabbedPanel()
    panel.add_tab("Tab 1", Frame(width=20, height=5))
    panel.add_tab("Tab 2", Frame(width=20, height=5))
    panel.on_tab_change = on_tab_change

    panel.switch_to_tab(1)

    await asyncio.wait_for(ran.wait(), timeout=1.0)


@pytest.mark.asyncio
async def test_menu_on_item_select_awaits_async_handler():
    """Menu selection fires an async on_item_select and close_callback."""
    select_ran = asyncio.Event()
    close_ran = asyncio.Event()

    async def on_item_select(action, item):
        select_ran.set()

    async def close_callback():
        close_ran.set()

    item = MenuItem(label="Save", action="save")
    menu = MenuElement(items=[item])
    menu.on_item_select = on_item_select
    menu.close_callback = close_callback

    menu._select_item(item)

    await asyncio.wait_for(select_ran.wait(), timeout=1.0)
    await asyncio.wait_for(close_ran.wait(), timeout=1.0)
