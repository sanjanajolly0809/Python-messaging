import socket
import threading
import logging

from protocol import encode_message, receive_message
from config import HOST, PORT

from database import (
    create_database,
    register_user,
    login_user,
    add_contact,
    get_contacts
)


# Configure logging.
logging.basicConfig(
    filename="server.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# Make sure the database exists.
create_database()


# Store connected users.
# Format: username -> socket
clients = {}


# Send a message to all connected users except the sender.
def broadcast(message, sender_socket):

    for username, client_socket in list(clients.items()):

        if client_socket != sender_socket:

            try:

                client_socket.sendall(message)

            except Exception as error:

                logger.error(
                    "Failed to send broadcast to %s: %s",
                    username,
                    error
                )


# Handle one connected client.
def handle_client(client_socket, client_address):

    logger.info(
        "Client connected: %s",
        client_address
    )

    print(
        "Client connected:",
        client_address
    )

    # The username is assigned after successful login.
    username = None

    while True:

        try:

            # Receive one complete framed message.
            message_data = receive_message(
                client_socket
            )

            if message_data is None:
                break

            message_type = message_data.get("type")


            # -------------------------------
            # USER REGISTRATION
            # -------------------------------

            if message_type == "REGISTER":

                new_username = message_data.get("username")
                password = message_data.get("password")

                if not new_username or not password:

                    response = {
                        "type": "REGISTER_RESPONSE",
                        "success": False,
                        "text": "Username and password are required."
                    }

                elif register_user(
                    new_username,
                    password
                ):

                    response = {
                        "type": "REGISTER_RESPONSE",
                        "success": True,
                        "text": "Registration successful."
                    }

                    logger.info(
                        "New user registered: %s",
                        new_username
                    )

                else:

                    response = {
                        "type": "REGISTER_RESPONSE",
                        "success": False,
                        "text": "Username already exists."
                    }

                    logger.warning(
                        "Registration failed for username: %s",
                        new_username
                    )

                client_socket.sendall(
                    encode_message(response)
                )

                continue


            # -------------------------------
            # USER LOGIN
            # -------------------------------

            if message_type == "LOGIN":

                login_username = message_data.get("username")
                password = message_data.get("password")

                if login_user(
                    login_username,
                    password
                ):

                    # Prevent the same account from being
                    # logged in from two clients.
                    if login_username in clients:

                        response = {
                            "type": "LOGIN_RESPONSE",
                            "success": False,
                            "text": "User is already online."
                        }

                        logger.warning(
                            "Duplicate login rejected: %s",
                            login_username
                        )

                    else:

                        username = login_username

                        clients[username] = client_socket

                        response = {
                            "type": "LOGIN_RESPONSE",
                            "success": True,
                            "text": "Login successful."
                        }

                        logger.info(
                            "User logged in: %s",
                            username
                        )

                else:

                    response = {
                        "type": "LOGIN_RESPONSE",
                        "success": False,
                        "text": "Incorrect username or password."
                    }

                    logger.warning(
                        "Failed login attempt: %s",
                        login_username
                    )

                client_socket.sendall(
                    encode_message(response)
                )

                continue


            # -------------------------------
            # AUTHENTICATION CHECK
            # -------------------------------

            # Every command below this point requires
            # the client to be logged in.
            if username is None:

                response = {
                    "type": "ERROR",
                    "text": "You must login first."
                }

                client_socket.sendall(
                    encode_message(response)
                )

                logger.warning(
                    "Unauthenticated request from %s: %s",
                    client_address,
                    message_type
                )

                continue


            # -------------------------------
            # ADD CONTACT
            # -------------------------------

            if message_type == "ADD_CONTACT":

                contact_username = message_data.get(
                    "contact_username"
                )

                if not contact_username:

                    response = {
                        "type": "ADD_CONTACT_RESPONSE",
                        "success": False,
                        "text": "Please specify a username."
                    }

                elif add_contact(
                    username,
                    contact_username
                ):

                    response = {
                        "type": "ADD_CONTACT_RESPONSE",
                        "success": True,
                        "text": (
                            f"{contact_username} "
                            "added to your contacts."
                        )
                    }

                    logger.info(
                        "%s added %s as a contact",
                        username,
                        contact_username
                    )

                else:

                    response = {
                        "type": "ADD_CONTACT_RESPONSE",
                        "success": False,
                        "text": (
                            "Contact does not exist "
                            "or is already added."
                        )
                    }

                client_socket.sendall(
                    encode_message(response)
                )

                continue


            # -------------------------------
            # GET CONTACTS
            # -------------------------------

            if message_type == "GET_CONTACTS":

                contacts = get_contacts(username)

                response = {
                    "type": "CONTACTS_RESPONSE",
                    "contacts": contacts
                }

                client_socket.sendall(
                    encode_message(response)
                )

                continue


            # -------------------------------
            # NORMAL BROADCAST MESSAGE
            # -------------------------------

            if message_type == "message":

                text = message_data.get(
                    "text",
                    ""
                )

                if not text.strip():

                    continue

                print(
                    f"{username}: {text}"
                )

                logger.info(
                    "Broadcast message from %s",
                    username
                )

                broadcast(
                    encode_message({
                        "type": "message",
                        "sender": username,
                        "text": text
                    }),
                    client_socket
                )

                continue


            # -------------------------------
            # PRIVATE MESSAGE
            # -------------------------------

            if message_type == "PRIVATE_MESSAGE":

                recipient = message_data.get(
                    "recipient"
                )

                text = message_data.get(
                    "text",
                    ""
                )

                if not recipient or not text.strip():

                    error_message = {
                        "type": "ERROR",
                        "text": "Recipient and message are required."
                    }

                    client_socket.sendall(
                        encode_message(error_message)
                    )

                    continue


                if recipient in clients:

                    recipient_socket = clients[
                        recipient
                    ]

                    private_message = {
                        "type": "PRIVATE_MESSAGE",
                        "sender": username,
                        "text": text
                    }

                    recipient_socket.sendall(
                        encode_message(
                            private_message
                        )
                    )

                    logger.info(
                        "Private message: %s -> %s",
                        username,
                        recipient
                    )

                else:

                    error_message = {
                        "type": "ERROR",
                        "text": "User is not online."
                    }

                    client_socket.sendall(
                        encode_message(
                            error_message
                        )
                    )

                    logger.warning(
                        "Private message failed: "
                        "%s -> %s (offline)",
                        username,
                        recipient
                    )

                continue


            # -------------------------------
            # FILE TRANSFER
            # -------------------------------

            if message_type == "FILE":

                recipient = message_data.get(
                    "recipient"
                )

                filename = message_data.get(
                    "filename"
                )

                file_data = message_data.get(
                    "file_data"
                )

                if not recipient or not filename or not file_data:

                    error_message = {
                        "type": "ERROR",
                        "text": "Invalid file transfer data."
                    }

                    client_socket.sendall(
                        encode_message(error_message)
                    )

                    continue


                print(
                    f"File transfer: "
                    f"{username} -> {recipient} "
                    f"({filename})"
                )

                logger.info(
                    "File transfer: %s -> %s (%s)",
                    username,
                    recipient,
                    filename
                )


                # Check whether the recipient is online.
                if recipient in clients:

                    recipient_socket = clients[
                        recipient
                    ]

                    file_message = {
                        "type": "FILE",
                        "sender": username,
                        "filename": filename,
                        "file_data": file_data
                    }

                    recipient_socket.sendall(
                        encode_message(
                            file_message
                        )
                    )

                    # Tell the sender that the transfer worked.
                    response = {
                        "type": "FILE_RESPONSE",
                        "success": True,
                        "text": "File sent successfully."
                    }

                    client_socket.sendall(
                        encode_message(
                            response
                        )
                    )

                else:

                    error_message = {
                        "type": "ERROR",
                        "text": "Recipient is not online."
                    }

                    client_socket.sendall(
                        encode_message(
                            error_message
                        )
                    )

                    logger.warning(
                        "File transfer failed: "
                        "%s -> %s (offline)",
                        username,
                        recipient
                    )

                continue


            # -------------------------------
            # UNKNOWN MESSAGE TYPE
            # -------------------------------

            logger.warning(
                "Unknown message type from %s: %s",
                username,
                message_type
            )

            error_message = {
                "type": "ERROR",
                "text": "Unknown message type."
            }

            client_socket.sendall(
                encode_message(
                    error_message
                )
            )


        except Exception as error:

            logger.exception(
                "Error handling client %s",
                client_address
            )

            print(
                "Error:",
                error
            )

            break


    # Remove the user when they disconnect.
    if username in clients:

        del clients[username]

        logger.info(
            "User disconnected: %s",
            username
        )


    client_socket.close()

    logger.info(
        "Connection closed: %s",
        client_address
    )

    print(
        "Client disconnected:",
        client_address
    )


# --------------------------------
# CREATE SERVER SOCKET
# --------------------------------

server_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)


# Allow the socket to be reused after shutdown.
server_socket.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)


# Bind the server to the configured address and port.
server_socket.bind(
    (HOST, PORT)
)


# Allow multiple clients to wait for connections.
server_socket.listen(5)


logger.info(
    "Server started on %s:%s",
    HOST,
    PORT
)


print("================================")
print("     Python Messaging Server")
print("================================")
print(
    f"Server listening on {HOST}:{PORT}"
)
print("Waiting for clients...")


# Continuously accept new clients.
while True:

    try:

        client_socket, client_address = (
            server_socket.accept()
        )

        # Create a separate thread for each client.
        client_thread = threading.Thread(
            target=handle_client,
            args=(
                client_socket,
                client_address
            )
        )

        client_thread.start()

        print(
            "Active client threads:",
            threading.active_count() - 1
        )

    except KeyboardInterrupt:

        print()
        print("Server shutting down...")

        logger.info(
            "Server stopped by administrator."
        )

        break

    except Exception as error:

        logger.exception(
            "Server accept error"
        )

        print(
            "Server error:",
            error
        )


# Close the server socket.
server_socket.close()

print("Server stopped.")