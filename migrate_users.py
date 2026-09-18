from database import get_connection, hash_password


connection = get_connection()
cursor = connection.cursor()


# Reset Charlie's password.
cursor.execute(
    "UPDATE users SET password = ? WHERE username = ?",
    (hash_password("1234"), "charlie")
)


# Reset Bob's password.
cursor.execute(
    "UPDATE users SET password = ? WHERE username = ?",
    (hash_password("1234"), "bob")
)


connection.commit()
connection.close()


print("Charlie password migrated successfully.")
print("Bob password migrated successfully.")