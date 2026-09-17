This directory is a placeholder for optional fonts and sounds.

The game runs fully without any files here:

- Fonts: drop ``arial.ttf`` (or set ``FONT_CANDIDATES`` in ``config.py`` to
  any ``.ttf`` you like); the built-in pygame font is used otherwise.
- Sounds: effects are synthesized procedurally at startup (see
  ``audio.py``), so no ``.wav``/``.ogg`` files are needed. Drop files here
  only if you later want custom samples.
