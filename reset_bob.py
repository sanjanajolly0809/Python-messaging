import sqlite3

connection = sqlite3.connect("messenger.db")
cursor = connection.cursor()

cursor.execute(
    "UPDATE users SET password = ? WHERE username = ?",
    ("1234", "bob")
)

connection.commit()
connection.close()

print("Bob password reset to 1234")