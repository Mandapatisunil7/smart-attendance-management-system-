import sqlite3

conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE attendance
        ADD COLUMN subject TEXT
    """)
    print("✅ Subject column added successfully.")
except sqlite3.OperationalError:
    print("⚠️ Subject column already exists.")

conn.commit()
conn.close()