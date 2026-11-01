"""The store's SQL migrations, applied by a single runner with a single lock.

Files are ordered by their numeric prefix. Each `NNNN_name.sql` is applied once;
the reverse lives in `NNNN_name.down.sql`.
"""
