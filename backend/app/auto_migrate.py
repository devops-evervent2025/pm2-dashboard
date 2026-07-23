"""
Lightweight automatic column migration.

Base.metadata.create_all() (called on every startup) only creates tables
that don't exist yet - it has no concept of "this table exists but is
missing a column that was just added to the model." That's normally what
a full migration tool (Alembic) is for, but for this app's scale, a
simple startup check covers the actual need: whenever a model gains a
new column, this detects it's missing from the real database and adds
it automatically via ALTER TABLE ... ADD COLUMN.

Safety: this ONLY ever adds missing columns. It never drops, renames, or
alters the type of an existing column, and never touches existing data
beyond backfilling a DEFAULT for newly-added NOT NULL columns (required
by MySQL when the table already has rows).
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.database import Base

logger = logging.getLogger("auto_migrate")


def run_auto_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue

            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue

                col_type = column.type.compile(dialect=engine.dialect)
                nullable_sql = "NULL" if column.nullable else "NOT NULL"

                default_sql = ""
                if column.default is not None and getattr(column.default, "is_scalar", False):
                    val = column.default.arg
                    if isinstance(val, bool):
                        default_sql = f" DEFAULT {1 if val else 0}"
                    elif isinstance(val, (int, float)):
                        default_sql = f" DEFAULT {val}"
                    elif isinstance(val, str):
                        default_sql = f" DEFAULT '{val}'"

                if not column.nullable and not default_sql:
                    type_name = col_type.upper()
                    if "INT" in type_name or "BOOL" in type_name or "TINYINT" in type_name:
                        default_sql = " DEFAULT 0"

                ddl = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} {nullable_sql}{default_sql}"

                try:
                    conn.execute(text(ddl))
                    logger.warning(f"[auto_migrate] Added missing column: {table_name}.{column.name}")
                    print(f"[auto_migrate] Added missing column: {table_name}.{column.name}")
                except Exception as exc:
                    logger.error(f"[auto_migrate] Failed to add {table_name}.{column.name}: {exc}")
                    print(f"[auto_migrate] FAILED to add {table_name}.{column.name}: {exc}")
