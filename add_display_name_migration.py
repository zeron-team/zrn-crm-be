"""
Migration script: Add display_name column to task_attachments table.
Run once: python add_display_name_migration.py
"""
import sys
sys.path.insert(0, '.')

from app.database import engine
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='task_attachments' AND column_name='display_name'"
        ))
        if result.fetchone():
            print("✅ Column 'display_name' already exists. Nothing to do.")
            return

        conn.execute(text(
            "ALTER TABLE task_attachments ADD COLUMN display_name VARCHAR(255)"
        ))
        conn.commit()
        print("✅ Column 'display_name' added to task_attachments successfully.")

if __name__ == "__main__":
    migrate()
