import sqlite3

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# Add subject column
try:
    cursor.execute("""
        ALTER TABLE attendance
        ADD COLUMN subject TEXT
    """)
    print("✅ subject column added.")
except sqlite3.OperationalError:
    print("ℹ️ subject column already exists.")

# Add is_deleted to attendance table
try:
    cursor.execute("""
        ALTER TABLE attendance
        ADD COLUMN is_deleted INTEGER DEFAULT 0
    """)
    print("✅ is_deleted column added.")
except sqlite3.OperationalError:
    print("ℹ️ is_deleted column already exists.")

conn.commit()
conn.close()

print("Database updated successfully.")