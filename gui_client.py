import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import socket
import threading
import queue
import base64
import os

from protocol import encode_message, receive_message
from config import HOST, PORT, RECEIVED_FILES_FOLDER


client_socket = None
username = None
message_queue = queue.Queue()
running = True


# Connect to server
def connect_to_server():
    global client_socket

    try:
        client_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        client_socket.connect(
            (HOST, PORT)
        )

        return True

    except Exception as error:
        messagebox.showerror(
            "Connection Error",
            str(error)
        )
        return False


# Receive messages from server
def receive_messages():

    while running:

        try:
            message = receive_message(
                client_socket
            )

            if message is None:
                break

            message_queue.put(message)

        except Exception:
            break


# Check received messages
def check_messages():

    while not message_queue.empty():

        message = message_queue.get()
        message_type = message.get("type")

        if message_type == "message":

            add_chat_message(
                f"{message.get('sender')}: "
                f"{message.get('text')}"
            )

        elif message_type == "PRIVATE_MESSAGE":

            add_chat_message(
                f"[Private] {message.get('sender')}: "
                f"{message.get('text')}"
            )

        elif message_type == "ERROR":

            add_chat_message(
                f"[ERROR] {message.get('text')}"
            )

        elif message_type == "FILE_RESPONSE":

            add_chat_message(
                f"[File] {message.get('text')}"
            )

        elif message_type == "FILE":

            receive_file(message)

        elif message_type == "ADD_CONTACT_RESPONSE":

            add_chat_message(
                f"[Contacts] {message.get('text')}"
            )

        elif message_type == "CONTACTS_RESPONSE":

            show_contacts(
                message.get("contacts", [])
            )

    window.after(
        100,
        check_messages
    )


# Display a message
def add_chat_message(text):

    chat_display.config(
        state="normal"
    )

    chat_display.insert(
        tk.END,
        text + "\n"
    )

    chat_display.see(
        tk.END
    )

    chat_display.config(
        state="disabled"
    )


# Send normal or private message
def send_message():

    text = message_entry.get().strip()

    if not text:
        return

    try:

        # Private message
        if text.startswith("@"):

            parts = text.split(
                " ",
                1
            )

            if len(parts) != 2:

                add_chat_message(
                    "Use: @username message"
                )

                return

            recipient = parts[0][1:]
            private_text = parts[1]

            message = {
                "type": "PRIVATE_MESSAGE",
                "recipient": recipient,
                "text": private_text
            }

            client_socket.sendall(
                encode_message(message)
            )

            add_chat_message(
                f"[Private to {recipient}]: "
                f"{private_text}"
            )

        # Normal message
        else:

            message = {
                "type": "message",
                "sender": username,
                "text": text
            }

            client_socket.sendall(
                encode_message(message)
            )

            add_chat_message(
                f"You: {text}"
            )

        message_entry.delete(
            0,
            tk.END
        )

    except Exception as error:

        messagebox.showerror(
            "Send Error",
            str(error)
        )


# Send file
def send_file():

    filename = filedialog.askopenfilename()

    if not filename:
        return

    recipient = simpledialog.askstring(
        "Send File",
        "Enter recipient username:"
    )

    if not recipient:
        return

    try:

        with open(
            filename,
            "rb"
        ) as file:

            data = file.read()

        file_data = base64.b64encode(
            data
        ).decode("utf-8")

        message = {
            "type": "FILE",
            "recipient": recipient,
            "filename": os.path.basename(filename),
            "file_data": file_data
        }

        client_socket.sendall(
            encode_message(message)
        )

        add_chat_message(
            f"[File] Sending "
            f"{os.path.basename(filename)} "
            f"to {recipient}"
        )

    except Exception as error:

        messagebox.showerror(
            "File Error",
            str(error)
        )


# Receive file
def receive_file(message):

    try:

        filename = message.get(
            "filename"
        )

        file_data = message.get(
            "file_data"
        )

        sender = message.get(
            "sender"
        )

        data = base64.b64decode(
            file_data
        )

        # Create folder if it does not exist
        os.makedirs(
            RECEIVED_FILES_FOLDER,
            exist_ok=True
        )

        save_name = os.path.join(
            RECEIVED_FILES_FOLDER,
            "received_" + filename
        )

        with open(
            save_name,
            "wb"
        ) as file:

            file.write(data)

        add_chat_message(
            f"[File] Received {filename} "
            f"from {sender}"
        )

        add_chat_message(
            f"[File] Saved in {save_name}"
        )

    except Exception as error:

        add_chat_message(
            f"[File Error] {error}"
        )


# Add contact
def add_contact():

    contact = simpledialog.askstring(
        "Add Contact",
        "Enter username:"
    )

    if not contact:
        return

    if contact == username:

        messagebox.showwarning(
            "Invalid Contact",
            "You cannot add yourself."
        )

        return

    message = {
        "type": "ADD_CONTACT",
        "contact_username": contact
    }

    client_socket.sendall(
        encode_message(message)
    )


# Get contacts
def get_contacts():

    message = {
        "type": "GET_CONTACTS"
    }

    client_socket.sendall(
        encode_message(message)
    )


# Show contacts
def show_contacts(contacts):

    contact_window = tk.Toplevel(
        window
    )

    contact_window.title(
        "My Contacts"
    )

    contact_window.geometry(
        "300x300"
    )

    tk.Label(
        contact_window,
        text="My Contacts",
        font=("Arial", 18, "bold")
    ).pack(
        pady=15
    )

    contact_list = tk.Listbox(
        contact_window,
        width=30,
        height=10
    )

    contact_list.pack(
        pady=10
    )

    for contact in contacts:

        contact_list.insert(
            tk.END,
            contact
        )

    if not contacts:

        contact_list.insert(
            tk.END,
            "No contacts yet."
        )

    tk.Button(
        contact_window,
        text="Close",
        command=contact_window.destroy
    ).pack(
        pady=10
    )


# Press Enter
def enter_pressed(event):

    send_message()


# Open chat window
def open_chat_window():

    for widget in window.winfo_children():

        widget.destroy()

    window.title(
        f"Python Messenger - {username}"
    )

    window.geometry(
        "750x600"
    )

    tk.Label(
        window,
        text=f"Welcome, {username}",
        font=("Arial", 20, "bold")
    ).pack(
        pady=10
    )

    global chat_display

    chat_display = tk.Text(
        window,
        state="disabled",
        wrap="word"
    )

    chat_display.pack(
        padx=15,
        pady=10,
        fill="both",
        expand=True
    )

    message_frame = tk.Frame(
        window
    )

    message_frame.pack(
        fill="x",
        padx=15,
        pady=10
    )

    global message_entry

    message_entry = tk.Entry(
        message_frame,
        font=("Arial", 12)
    )

    message_entry.pack(
        side="left",
        fill="x",
        expand=True,
        padx=(0, 10)
    )

    tk.Button(
        message_frame,
        text="Send",
        width=10,
        command=send_message
    ).pack(
        side="right"
    )

    message_entry.bind(
        "<Return>",
        enter_pressed
    )

    button_frame = tk.Frame(
        window
    )

    button_frame.pack(
        pady=5
    )

    tk.Button(
        button_frame,
        text="Add Contact",
        width=14,
        command=add_contact
    ).pack(
        side="left",
        padx=5
    )

    tk.Button(
        button_frame,
        text="View Contacts",
        width=14,
        command=get_contacts
    ).pack(
        side="left",
        padx=5
    )

    tk.Button(
        button_frame,
        text="Send File",
        width=14,
        command=send_file
    ).pack(
        side="left",
        padx=5
    )

    tk.Button(
        window,
        text="Logout",
        width=10,
        command=logout
    ).pack(
        pady=10
    )

    threading.Thread(
        target=receive_messages,
        daemon=True
    ).start()

    window.after(
        100,
        check_messages
    )

    message_entry.focus()


# Logout
def logout():

    global running

    running = False

    try:

        client_socket.shutdown(
            socket.SHUT_RDWR
        )

    except OSError:
        pass

    try:

        client_socket.close()

    except OSError:
        pass

    window.destroy()


# Login
def login():

    global username
    global running

    username = username_entry.get().strip()
    password = password_entry.get()

    if not username or not password:

        messagebox.showwarning(
            "Login",
            "Enter username and password."
        )

        return

    running = True

    if not connect_to_server():

        return

    message = {
        "type": "LOGIN",
        "username": username,
        "password": password
    }

    try:

        client_socket.sendall(
            encode_message(message)
        )

        response = receive_message(
            client_socket
        )

        if response and response.get("success"):

            open_chat_window()

        else:

            messagebox.showerror(
                "Login Failed",
                response.get(
                    "text",
                    "Login failed."
                )
            )

            client_socket.close()

    except Exception as error:

        messagebox.showerror(
            "Login Error",
            str(error)
        )


# Register
def register():

    new_username = simpledialog.askstring(
        "Register",
        "Enter username:"
    )

    if not new_username:
        return

    new_password = simpledialog.askstring(
        "Register",
        "Enter password:",
        show="*"
    )

    if not new_password:
        return

    try:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        sock.connect(
            (HOST, PORT)
        )

        message = {
            "type": "REGISTER",
            "username": new_username,
            "password": new_password
        }

        sock.sendall(
            encode_message(message)
        )

        response = receive_message(
            sock
        )

        sock.close()

        if response and response.get("success"):

            messagebox.showinfo(
                "Registration",
                "Registration successful!"
            )

        else:

            messagebox.showerror(
                "Registration Failed",
                response.get(
                    "text",
                    "Registration failed."
                )
            )

    except Exception as error:

        messagebox.showerror(
            "Registration Error",
            str(error)
        )


# Login window
window = tk.Tk()

window.title(
    "Python Messenger"
)

window.geometry(
    "500x400"
)

window.resizable(
    False,
    False
)


tk.Label(
    window,
    text="Python Messenger",
    font=("Arial", 24, "bold")
).pack(
    pady=30
)


tk.Label(
    window,
    text="Username"
).pack()


username_entry = tk.Entry(
    window,
    width=30
)

username_entry.pack(
    pady=5
)


tk.Label(
    window,
    text="Password"
).pack()


password_entry = tk.Entry(
    window,
    width=30,
    show="*"
)

password_entry.pack(
    pady=5
)


tk.Button(
    window,
    text="Login",
    width=20,
    command=login
).pack(
    pady=20
)


tk.Button(
    window,
    text="Register",
    width=20,
    command=register
).pack()


window.mainloop()