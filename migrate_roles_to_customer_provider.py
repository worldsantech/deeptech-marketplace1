import sqlite3

DB_PATH = "machinahub.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Starting role migration...")

cursor.execute("SELECT id, email, role FROM users ORDER BY id")
rows_before = cursor.fetchall()

print("\nRoles BEFORE migration:")
for row in rows_before:
    print(row)

cursor.execute("UPDATE users SET role = 'Customer' WHERE role = 'client'")
customer_updated = cursor.rowcount

cursor.execute("UPDATE users SET role = 'Provider' WHERE role = 'engineer'")
engineer_updated = cursor.rowcount

cursor.execute("UPDATE users SET role = 'Provider' WHERE role = 'factory'")
factory_updated = cursor.rowcount

conn.commit()

cursor.execute("SELECT id, email, role FROM users ORDER BY id")
rows_after = cursor.fetchall()

print("\nRoles AFTER migration:")
for row in rows_after:
    print(row)

print("\nMigration summary:")
print(f"client -> Customer: {customer_updated}")
print(f"engineer -> Provider: {engineer_updated}")
print(f"factory -> Provider: {factory_updated}")

conn.close()

print("\nRole migration completed successfully.")