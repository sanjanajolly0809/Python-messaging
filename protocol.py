import json
import struct


# Convert a Python dictionary into a framed JSON message.
def encode_message(message):

    # Convert the dictionary to JSON.
    json_data = json.dumps(message).encode("utf-8")

    # Create a 4-byte header containing the message length.
    header = struct.pack("!I", len(json_data))

    # Send header + JSON data.
    return header + json_data


# Receive exactly the requested number of bytes.
def recv_exact(sock, number_of_bytes):

    data = b""

    while len(data) < number_of_bytes:

        chunk = sock.recv(
            number_of_bytes - len(data)
        )

        if not chunk:
            return None

        data += chunk

    return data


# Receive one complete framed JSON message.
def receive_message(sock):

    # First receive the 4-byte length header.
    header = recv_exact(sock, 4)

    if header is None:
        return None

    # Convert the header back into an integer.
    message_length = struct.unpack(
        "!I",
        header
    )[0]

    # Receive the complete JSON message.
    json_data = recv_exact(
        sock,
        message_length
    )

    if json_data is None:
        return None

    # Convert JSON back into a Python dictionary.
    return json.loads(
        json_data.decode("utf-8")
    )


# Create a file-transfer message.
def create_file_message(
    sender,
    recipient,
    filename,
    file_data
):

    return {
        "type": "FILE",
        "sender": sender,
        "recipient": recipient,
        "filename": filename,
        "file_data": file_data
    }
