"""Empty the django_session table and shrink the database file.

Sessions moved to signed cookies (config/settings/base.py), so the table is
unused. Its expired rows had filled the deployed database: 121 MiB of a
127 MiB file on djustlive's 128 MiB /var tmpfs, so every write failed with
"database or disk is full".

* ``wal_checkpoint(TRUNCATE)`` first returns any WAL left over from earlier
  writes to the filesystem; it needs no new space.
* ``DELETE FROM django_session`` with no WHERE clause lets SQLite drop the
  table's pages in bulk instead of rewriting each row, so it commits in the
  few hundred KB a nearly full filesystem has left.
* ``VACUUM`` then rewrites the database from its live rows (a few KB), and
  a second ``wal_checkpoint(TRUNCATE)`` hands the space back. If the VACUUM
  fails for lack of space, the freed pages are still reused by later
  writes, so the migration does not fail.

Every existing session is discarded (signed-in users are logged out).
Non-atomic: VACUUM cannot run inside a transaction.
"""

import logging

from django.db import migrations
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


def clear_sessions(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM django_session")
        return
    try:
        _clear_and_vacuum(connection)
    except OperationalError as exc:
        if "full" not in str(exc):
            raise
        # A WAL write needs free space for its frames. With the filesystem
        # (almost) full, use an in-memory rollback journal instead: pages
        # are rewritten in place, so the DELETE and VACUUM need no new
        # space. Litestream has not started yet when djustlive runs
        # migrate on boot, so leaving WAL mode for a moment is safe.
        logger.warning("django_session: no room for WAL (%s); clearing in place", exc)
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=MEMORY")
        try:
            _clear_and_vacuum(connection)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA journal_mode=WAL")


def _clear_and_vacuum(connection):
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        cursor.execute("DELETE FROM django_session")
    try:
        with connection.cursor() as cursor:
            cursor.execute("VACUUM")
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except OperationalError as exc:
        logger.warning("django_session cleared but VACUUM failed: %s", exc)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("home", "0001_initial"),
        ("sessions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(clear_sessions, migrations.RunPython.noop),
    ]
