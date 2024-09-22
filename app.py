from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
import time

app = Flask(__name__)
socketio = SocketIO(app)  # Initialize WebSocket support

@app.route('/')
def home():
    return jsonify({"message": "Hello from Flask on Docker!"})

# WebSocket route to handle process start
@socketio.on('startProcess')
def handle_process_start(data):
    print("Received process start request")

    # Emit updates for each process
    emit('processUpdate', {'message': 'Process 1 started'})
    time.sleep(2)  # Simulate process 1
    emit('processUpdate', {'message': 'Process 1 finished'})

    emit('processUpdate', {'message': 'Process 2 started'})
    time.sleep(2)  # Simulate process 2
    emit('processUpdate', {'message': 'Process 2 finished'})

    emit('processUpdate', {'message': 'Process 3 started'})
    time.sleep(2)  # Simulate process 3
    emit('processUpdate', {'message': 'Process 3 finished'})

    # Notify the client that all processes are complete
    emit('processComplete', {'message': 'All processes finished'})

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80)
