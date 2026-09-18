
import sqlite3
import hashlib
import secrets


from config import DATABASE_NAME


# Create a connection to the database.
def get_connection():

    return sqlite3.connect(DATABASE_NAME)


# Hash a password using PBKDF2-HMAC-SHA256.
def hash_password(password, salt=None):

    if salt is None:

        salt = secrets.token_bytes(16)

    password_bytes = password.encode("utf-8")

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password_bytes,
        salt,
        100_000
    )

    # Store salt and hash together as hexadecimal text.
    return (
        salt.hex()
        + ":"
        + password_hash.hex()
    )


# Check a password against its stored hash.
def verify_password(password, stored_password):

    try:

        salt_hex, hash_hex = stored_password.split(":")

        salt = bytes.fromhex(salt_hex)

        password_bytes = password.encode("utf-8")

        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password_bytes,
            salt,
            100_000
        )

        return secrets.compare_digest(
            password_hash.hex(),
            hash_hex
        )

    except (ValueError, TypeError):

        return False


# Create the required database tables.
def create_database():

    connection = get_connection()
    cursor = connection.cursor()

    # Users table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Contacts table.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            contact_username TEXT NOT NULL,
            UNIQUE(username, contact_username)
        )
    """)

    connection.commit()
    connection.close()


# Register a new user.
def register_user(username, password):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # Hash the password before storing it.
        password_hash = hash_password(password)

        cursor.execute(
            """
            INSERT INTO users (username, password)
            VALUES (?, ?)
            """,
            (username, password_hash)
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError:

        # Username already exists.
        return False

    finally:

        connection.close()


# Check whether a user's login details are correct.
def login_user(username, password):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT password
        FROM users
        WHERE username = ?
        """,
        (username,)
    )

    user = cursor.fetchone()

    connection.close()

    if not user:
        return False

    stored_password = user[0]

    return verify_password(
        password,
        stored_password
    )


# Add a contact for a user.
def add_contact(username, contact_username):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        # Check that the contact user exists.
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            (contact_username,)
        )

        contact = cursor.fetchone()

        if not contact:

            return False

        # Add the contact.
        cursor.execute(
            """
            INSERT INTO contacts (
                username,
                contact_username
            )
            VALUES (?, ?)
            """,
            (username, contact_username)
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError:

        # Contact already exists.
        return False

    finally:

        connection.close()


# Get all contacts of a user.
def get_contacts(username):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT contact_username
        FROM contacts
        WHERE username = ?
        """,
        (username,)
    )

    contacts = cursor.fetchall()

    connection.close()

    # Convert database results into a simple list.
    return [contact[0] for contact in contacts]

