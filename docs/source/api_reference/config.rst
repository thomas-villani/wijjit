Configuration API
=================

Wijjit uses a Flask-inspired configuration system. ``Config`` is the dict-like
container exposed as ``app.config``, and ``DefaultConfig`` supplies the built-in
defaults (and the authoritative list of recognised keys).

.. autosummary::
   :toctree: ../api/
   :nosignatures:

   wijjit.config.Config
   wijjit.config.DefaultConfig

See the User Guide :doc:`../user_guide/configuration` for the full catalog of
configuration keys and their meanings.
