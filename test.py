import socketio

# Connect to the server
sio = socketio.Client()

# Define the event handler for connection
@sio.event
def connect():
    print("Connected to the server")
    # Send the checkFullSecurity event
    sio.emit('checkCommitSecurity', {
        'affectedFiles': ["file1.py", "file2.js"],
        'commitId': "abc123",
        'commitTime': "2024-09-28T10:00:00"
    })

# Define the event handler for disconnection
@sio.event
def disconnect():
    print("Disconnected from server")

# Define the event handler for processComplete event
@sio.on('processComplete')
def handle_process_complete(data):
    print(f"Process completed: {data}")

# Connect to the Socket.IO server
sio.connect('http://127.0.0.1:80')

# Wait for the event responses
sio.wait()
