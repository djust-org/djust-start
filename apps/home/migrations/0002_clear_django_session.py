"""Drop every row of django_session and shrink the database file.

Sessions moved to signed cookies (config/settings/base.py), so the table is
unused. Its expired rows had filled the deployed database: 121 MiB of a
127 MiB file on djustlive's 128 MiB /var tmpfs, so every write failed with
"database or disk is full". Writes cut off by the full disk also left the
table's b-tree corrupt ("database disk image is malformed"), and that
corruption is in the Litestream replica, so every restore brings it back.

A DELETE or DROP TABLE has to walk the corrupt b-tree, and in WAL mode it
needs free space for its WAL frames, so neither works here. Instead, on
SQLite (file databases):

1. Use an in-memory rollback journal and in-memory temp storage, so no
   step needs space on the full filesystem. djustlive runs migrate on boot
   before Litestream starts, so leaving WAL mode for a moment is safe.
2. Unlink django_session and its indexes from the schema (writable_schema),
   keeping their CREATE statements. Their pages are never read.
3. VACUUM: rebuild the file from the tables still in the schema. The
   orphaned session pages are not copied; the file shrinks to a few
   hundred KB.
4. Recreate the empty table and its index from the saved statements, and
   switch back to WAL.

Other backends and in-memory test databases just DELETE.
Every existing session is discarded (signed-in users are logged out).
"""

import sqlite3

from django.db import migrations

TABLE = "django_session"


def clear_sessions(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "sqlite" or connection.is_in_memory_db():
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {TABLE}")
        return
    path = connection.settings_dict["NAME"]
    # Changing the journal mode needs the only connection to the file.
    connection.close()
    rebuild_without_sessions(str(path))


def rebuild_without_sessions(path):
    db = sqlite3.connect(path, isolation_level=None)
    try:
        if hasattr(db, "setconfig"):  # Python 3.12+
            db.setconfig(sqlite3.SQLITE_DBCONFIG_DEFENSIVE, False)
        before = db.execute("PRAGMA page_count").fetchone()[0]
        db.execute("PRAGMA temp_store=MEMORY")
        mode = db.execute("PRAGMA journal_mode=MEMORY").fetchone()[0]
        if mode != "memory":
            raise RuntimeError(f"could not leave WAL mode (journal_mode={mode})")
        rows = db.execute(
            "SELECT type, name, sql FROM sqlite_schema"
            " WHERE tbl_name = ? ORDER BY type DESC",
            (TABLE,),
        ).fetchall()
        create = [sql for _type, _name, sql in rows if sql]  # table first, then indexes
        db.execute("PRAGMA writable_schema=ON")
        db.execute("DELETE FROM sqlite_schema WHERE tbl_name = ?", (TABLE,))
        db.execute("PRAGMA writable_schema=OFF")
        db.execute("PRAGMA writable_schema=RESET")
        db.execute("VACUUM")
        for sql in create:
            db.execute(sql)
        db.execute("PRAGMA journal_mode=WAL")
        after = db.execute("PRAGMA page_count").fetchone()[0]
        # print, not logging: migrate's output is the boot console on djustlive.
        print(
            f"  home.0002: rebuilt {path} without {TABLE} ({before} -> {after} pages)"
        )
    finally:
        db.close()


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("home", "0001_initial"),
        ("sessions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(clear_sessions, migrations.RunPython.noop),
    ]
