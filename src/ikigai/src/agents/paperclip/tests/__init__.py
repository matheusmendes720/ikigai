"""Paperclip test package — smoke + HIL flow tests.

Both files import only from paperclip package internals + the standard
library; they do NOT shell out to ``claude`` or touch git. They verify
the graph compiles, the factory signature is correct, the state schema
is intact, and the HIL pause/resume cycle behaves.
"""
