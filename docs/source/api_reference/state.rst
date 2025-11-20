State API
=========

``wijjit.core.state`` provides the reactive dictionary that powers every application. ``State`` tracks mutations, fires watchers, and integrates with the renderer to trigger re-renders.

Key classes
-----------

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.core.state.State

Usage highlights
----------------

* Attribute and dict-style access (``state.username`` / ``state["username"]``).
* ``on_change`` and ``watch`` support sync and async callbacks.
* Reserved keys guard against name clashes with dict methods.
* Async change handling is coordinated via per-state task tracking.

Module documentation
--------------------

.. automodule:: wijjit.core.state
   :members:
   :show-inheritance:
   :noindex:
