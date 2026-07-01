"""Tabbed Panel Demo.

Demonstrates the TabbedPanel element with tabs positioned on top.

Features:
- Keyboard navigation (Left/Right arrow keys to switch tabs)
- Mouse click navigation (click tabs to switch)
- Mouse scroll wheel support (scroll content with wheel)
- Visual highlighting of active tab (brackets + reverse)
- Scrollable content with Up/Down/PageUp/PageDown/Home/End
- Multiple tabs with different content
- State persistence

Controls:
- Left/Right arrows: Navigate between tabs
- Up/Down/PageUp/PageDown/Home/End: Scroll content
- Mouse click: Click on tabs to switch
- Mouse wheel: Scroll content up/down
- q or Ctrl+Q: Quit
"""

from wijjit import Wijjit, render_template_string

app = Wijjit(enable_mouse=True)


@app.view("main", default=True)
def main_view():
    template = """
    {% vstack spacing=1 padding=1 %}
        {% frame title="Tabbed Panel Demo - Top Position" border="double" %}
            Use Left/Right arrows to switch tabs | Up/Down to scroll content
        {% endframe %}

        {% tabbedpanel id="main_tabs" tab_position="top"
                       active_tab="active_tab" width=78 height=25 border="single" %}
            {% tab label="Welcome" %}
Welcome to the Wijjit Tabbed Panel Demo!

{% button %}Test Button{% endbutton %}

This demonstrates a tabbed interface with tabs positioned at the TOP.

Features:
- Navigate between tabs with Left/Right arrow keys
- Active tab is highlighted with [brackets] and reverse styling
- Click tabs with your mouse to switch
- Scroll content with Up/Down/PageUp/PageDown
- Content persists when switching tabs
- Multiple border styles supported

Try the Dashboard tab to see scrollable content!

The tabbed panel element makes it easy to organize
complex interfaces into logical sections.
            {% endtab %}

            {% tab label="Dashboard" %}
Dashboard Overview - Use Up/Down or PageUp/PageDown to scroll

Statistics:
- Active Users: 1,234
- Total Projects: 56
- Pending Tasks: 23
- Completed Today: 8

System Status:
- CPU Usage: 45%
- Memory: 2.1 GB / 8 GB
- Disk Space: 142 GB free
- Network: Online

Recent Activity:
- User login from 192.168.1.100
- Project "Website Redesign" updated
- 3 new tasks created
- Backup completed successfully

Additional Statistics:
- Response Time: 45ms average
- Error Rate: 0.02%
- Uptime: 99.9%
- Active Sessions: 342

Server Metrics:
- Load Average: 0.45, 0.52, 0.48
- Swap Usage: 128MB / 2GB
- Open Files: 1,234
- Network I/O: 45 MB/s

Recent Deployments:
- v2.1.5 deployed 2 hours ago
- v2.1.4 deployed yesterday
- v2.1.3 deployed 3 days ago

Scroll down to see more content...
Line 35
Line 36
Line 37
Line 38
Line 39
Line 40 - End of content
            {% endtab %}

            {% tab label="Projects" %}
Project Management

Active Projects:

1. Website Redesign
   Status: 80% complete
   Team: 5 members
   Deadline: Next week

2. Mobile App Development
   Status: 45% complete
   Team: 8 members
   Deadline: End of month

3. API Integration
   Status: 90% complete
   Team: 3 members
   Deadline: Tomorrow

4. Database Migration
   Status: 10% complete
   Team: 4 members
   Deadline: Next quarter
            {% endtab %}

            {% tab label="Messages" %}
Message Inbox

Unread: 5 | Total: 142

Recent Messages:

[2 hours ago] Sarah Johnson
  "Can we schedule a meeting to discuss the new feature?"

[5 hours ago] Mike Chen
  "The deployment is complete and all tests are passing!"

[Yesterday] Lisa Anderson
  "I've reviewed your pull request, looks good!"

[Yesterday] Tom Williams
  "Project deadline has been extended by one week"

[2 days ago] Emma Davis
  "New design mockups are ready for review"
            {% endtab %}

            {% tab label="Settings" %}
Application Settings

General:
- Theme: Dark Mode
- Language: English
- Timezone: UTC-5
- Date Format: MM/DD/YYYY

Interface:
- Font Size: 14px
- Editor Mode: Vim
- Line Numbers: Enabled
- Auto-save: Every 5 minutes

Notifications:
- Email: Enabled
- Desktop: Enabled
- Mobile Push: Disabled
- Sound: Enabled

Privacy:
- Share Usage Data: No
- Crash Reports: Yes
- Activity Tracking: No
            {% endtab %}

            {% tab label="About" %}
Wijjit Tabbed Panel
Version 1.0.0

A declarative TUI framework for Python

This tabbed panel element provides:
- Multiple tab positions (top, bottom, left, right)
- Keyboard navigation support
- Mouse interaction
- State persistence
- Customizable styling
- Border style options

Developer: Tom Villani
Framework: Wijjit - "Flask for the Console"

Built with Python and lots of coffee!

Press Left/Right arrows to navigate between tabs.
Click tabs with your mouse to switch instantly.

Press 'q' to quit this demo.
            {% endtab %}
        {% endtabbedpanel %}

        {% frame title="Navigation" border="single" %}
Left/Right: switch tabs | Up/Down/PgUp/PgDn: scroll | Click tabs | Q to quit
        {% endframe %}
    {% endvstack %}
    """

    return render_template_string(template)


@app.on_key("q")
def quit_app(event):
    app.quit()


if __name__ == "__main__":
    app.run()
