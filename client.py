
import socket
import threading
import base64
import os
from protocol import encode_message, receive_message
from config import HOST, PORT



# Receive messages from the server.
def receive_messages():

    while True:

        try:

            # Receive one complete framed message.
            message_data = receive_message(client_socket)

            if message_data is None:
                break

            message_type = message_data.get("type")


            # Receive a private message.
            if message_type == "PRIVATE_MESSAGE":

                print(
                    f"\n[Private message from "
                    f"{message_data['sender']}]: "
                    f"{message_data['text']}"
                )


            # Receive a normal message.
            elif message_type == "message":

                print(
                    f"\n[{message_data['sender']}]: "
                    f"{message_data['text']}"
                )


            # Receive an error.
            elif message_type == "ERROR":

                print(
                    f"\n[ERROR]: "
                    f"{message_data['text']}"
                )


            # Receive contact response.
            elif message_type == "ADD_CONTACT_RESPONSE":

                print(
                    f"\n[Contact]: "
                    f"{message_data['text']}"
                )


            # Receive contact list.
            elif message_type == "CONTACTS_RESPONSE":

                contacts = message_data.get(
                    "contacts",
                    []
                )

                print("\n========== Contacts ==========")

                if contacts:

                    for contact in contacts:

                        print("-", contact)

                else:

                    print("No contacts yet.")

                print("===============================")


            # Receive confirmation that a file was sent.
            elif message_type == "FILE_RESPONSE":

                print(
                    f"\n[File]: "
                    f"{message_data['text']}"
                )


            # Receive a file.
            elif message_type == "FILE":

                sender = message_data.get("sender")
                filename = message_data.get("filename")
                file_data = message_data.get("file_data")


                try:

                    # Decode the Base64 file data.
                    decoded_data = base64.b64decode(
                        file_data
                    )


                    # Create a received_files folder.
                    os.makedirs(
                        "received_files",
                        exist_ok=True
                    )


                    # Create the output path.
                    output_path = os.path.join(
                        "received_files",
                        filename
                    )


                    # Save the file.
                    with open(
                        output_path,
                        "wb"
                    ) as file:

                        file.write(decoded_data)


                    print(
                        f"\n[File received from "
                        f"{sender}]: {filename}"
                    )

                    print(
                        f"Saved to: {output_path}"
                    )


                except Exception as error:

                    print(
                        f"\n[File error]: {error}"
                    )


            print(
                "You: ",
                end="",
                flush=True
            )


        except Exception as error:

            print(
                "Receive error:",
                error
            )

            break


# Create a TCP socket.
client_socket = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)


print("Connecting to server...")

client_socket.connect(
    (HOST, PORT)
)

print("Connected to server!")


# Ask whether the user wants to register or login.
choice = input(
    "Type 'register' or 'login': "
)

username = input("Username: ")
password = input("Password: ")


# Handle registration.
if choice.lower() == "register":

    message_data = {
        "type": "REGISTER",
        "username": username,
        "password": password
    }

    client_socket.sendall(
        encode_message(message_data)
    )

    response = receive_message(client_socket)

    if response:

        print(response["text"])

    client_socket.close()

    print("Connection closed.")


# Handle login.
elif choice.lower() == "login":

    message_data = {
        "type": "LOGIN",
        "username": username,
        "password": password
    }

    client_socket.sendall(
        encode_message(message_data)
    )

    response = receive_message(client_socket)

    if response is None:

        print("Server disconnected.")

        client_socket.close()

        raise SystemExit


    print(response["text"])


    # Only continue if login was successful.
    if response.get("success"):

        print()
        print("================================")
        print("       Chat started")
        print("================================")
        print("Normal message: type your message")
        print("Private message: @username message")
        print("Add contact: add username")
        print("View contacts: contacts")
        print(
            "Send file: "
            "sendfile username filename"
        )
        print("Type 'quit' to disconnect.")
        print()


        # Start the receiving thread.
        receive_thread = threading.Thread(
            target=receive_messages
        )

        receive_thread.daemon = True
        receive_thread.start()


        # Keep sending messages.
        while True:

            try:

                message = input("You: ")


            except (EOFError, KeyboardInterrupt):

                print()

                break


            # Disconnect.
            if message.lower() == "quit":

                break


            # Add a contact.
            if message.lower().startswith("add "):

                contact_username = message[4:].strip()

                if contact_username:

                    add_contact_message = {
                        "type": "ADD_CONTACT",
                        "contact_username": contact_username
                    }

                    client_socket.sendall(
                        encode_message(
                            add_contact_message
                        )
                    )

                else:

                    print(
                        "Usage: add username"
                    )

                continue


            # Get contact list.
            if message.lower() == "contacts":

                get_contacts_message = {
                    "type": "GET_CONTACTS"
                }

                client_socket.sendall(
                    encode_message(
                        get_contacts_message
                    )
                )

                continue


            # Send a file.
            if message.lower().startswith("sendfile "):

                parts = message.split(" ", 2)

                if len(parts) != 3:

                    print(
                        "Usage: "
                        "sendfile username filename"
                    )

                    continue


                recipient = parts[1]
                filename = parts[2]


                # Check whether the file exists.
                if not os.path.isfile(filename):

                    print(
                        "File not found:",
                        filename
                    )

                    continue


                try:

                    # Read the file.
                    with open(
                        filename,
                        "rb"
                    ) as file:

                        file_bytes = file.read()


                    # Convert binary data to Base64 text.
                    file_data = base64.b64encode(
                        file_bytes
                    ).decode("utf-8")


                    # Create the file message.
                    file_message = {
                        "type": "FILE",
                        "recipient": recipient,
                        "filename": os.path.basename(
                            filename
                        ),
                        "file_data": file_data
                    }


                    # Send the file message.
                    client_socket.sendall(
                        encode_message(
                            file_message
                        )
                    )


                    print(
                        "Sending file..."
                    )


                except Exception as error:

                    print(
                        "File error:",
                        error
                    )

                continue


            # Check for a private message.
            if message.startswith("@"):

                parts = message.split(" ", 1)

                if len(parts) == 2:

                    recipient = parts[0][1:]
                    text = parts[1]

                    private_message = {
                        "type": "PRIVATE_MESSAGE",
                        "recipient": recipient,
                        "text": text
                    }

                    client_socket.sendall(
                        encode_message(
                            private_message
                        )
                    )

                else:

                    print(
                        "Use private messages like:"
                    )

                    print(
                        "@bob Hello Bob!"
                    )


            else:

                # Normal broadcast message.
                normal_message = {
                    "type": "message",
                    "sender": username,
                    "text": message
                }

                client_socket.sendall(
                    encode_message(
                        normal_message
                    )
                )


    else:

        print("Login failed.")


else:

    print("Invalid choice.")


# Close the connection.
try:

    client_socket.shutdown(
        socket.SHUT_RDWR
    )

except OSError:

    pass


client_socket.close()

print("Connection closed.")

