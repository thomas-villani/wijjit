Template Tags API
=================

Custom Jinja extensions make Wijjit templates declarative. Tags are grouped by purpose: layout containers, input widgets, display widgets, dialogs, and menus.

Layout tags
-----------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.tags.layout.VStackExtension
   wijjit.tags.layout.HStackExtension
   wijjit.tags.layout.FrameExtension
   wijjit.tags.layout.GridExtension
   wijjit.tags.layout.ColspanExtension
   wijjit.tags.layout.RowspanExtension
   wijjit.tags.layout.SplitPanelExtension

Input tags
----------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.tags.input.TextInputExtension
   wijjit.tags.input.TextAreaExtension
   wijjit.tags.input.CodeEditorExtension
   wijjit.tags.input.ButtonExtension
   wijjit.tags.input.CheckboxExtension
   wijjit.tags.input.CheckboxGroupExtension
   wijjit.tags.input.RadioExtension
   wijjit.tags.input.RadioGroupExtension
   wijjit.tags.input.SelectExtension
   wijjit.tags.input.SliderExtension
   wijjit.tags.input.ToggleExtension
   wijjit.tags.input.DataGridExtension

Display tags
------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.tags.display.TextExtension
   wijjit.tags.display.TableExtension
   wijjit.tags.display.TreeExtension
   wijjit.tags.display.ProgressBarExtension
   wijjit.tags.display.SpinnerExtension
   wijjit.tags.display.ContentViewExtension
   wijjit.tags.display.LogViewExtension
   wijjit.tags.display.ListViewExtension
   wijjit.tags.display.StatusBarExtension
   wijjit.tags.display.StatusIndicatorExtension
   wijjit.tags.display.LinkExtension
   wijjit.tags.display.ImageViewExtension
   wijjit.tags.display.PageExtension
   wijjit.tags.display.PagerExtension
   wijjit.tags.display.TabExtension
   wijjit.tags.display.TabbedPanelExtension
   wijjit.tags.display.ModalExtension

Chart tags
----------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.tags.charts.SparklineExtension
   wijjit.tags.charts.BarChartExtension
   wijjit.tags.charts.ColumnChartExtension
   wijjit.tags.charts.LineChartExtension
   wijjit.tags.charts.GaugeExtension
   wijjit.tags.charts.HeatMapExtension

Dialogs & menus
---------------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.tags.dialogs.ConfirmDialogExtension
   wijjit.tags.dialogs.AlertDialogExtension
   wijjit.tags.dialogs.TextInputDialogExtension
   wijjit.tags.menu.MenuItemExtension
   wijjit.tags.menu.DropdownExtension
   wijjit.tags.menu.ContextMenuExtension

Item tags
---------

Child-item tags used inside their parent container tags.

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.tags.input.SelectItemExtension
   wijjit.tags.display.TreeItemExtension
