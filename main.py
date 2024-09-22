from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
import time
from repoAnalysis import *
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Initialize WebSocket support with CORS handling

@app.route('/')
def home():
    return jsonify({"message": "Hello from Flask on Docker!"})





@socketio.on('setup')
def handleSetup(data):
    # (repo_url, clone_location, email, username, token) = data.values()
    # print(f"Received setup request for {repo_url}")
    # print("Clone location: ", clone_location)
    # print("Email: ", email)
    # print("Username: ", username)
    # print("Token: ", token)
    #setup(repo_url, clone_location, email, username, token)
    time.sleep(2)
    emit('processComplete', {'action': 'setup'})

@socketio.on('checkFullSecurity')
def handleFullSecurityCheck(data):
    print("Received full security check request")
    time.sleep(2)
    emit('processComplete', {'action': 'checkFullSecurity'})

@socketio.on('checkCommitSecurity')
def handleCommitSecurityCheck(data):
    print("Received commit security check request")
    time.sleep(2)
    emit('processComplete', {'action': 'checkCommitSecurity'})
@socketio.on('checkFullCompliance')
def handleFullComplianceCheck(data):
    print("Received full compliance check request")
    time.sleep(2)

    emit('processComplete', {'action': 'checkFullCompliance'})

@socketio.on('checkCommitCompliance')
def handleCommitComplianceCheck(data):
    print("Received commit compliance check request")
    time.sleep(2)  # Simulate a long-running process
    emit('processComplete', {'action': 'checkCommitCompliance'})





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

    # Notify the main server that the entire process is complete
    emit('processComplete', {'message': 'All processes finished'})

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80)  # Ensure Flask listens on all interfaces inside Docker
