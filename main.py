from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
import time
import os 
from Utils import * 
from git import Repo
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Initialize WebSocket support with CORS handling




def clone_private_repo(repo_url, clone_location, username, token, branch='main'):
    # Prepare the authenticated URL
    if repo_url.startswith('https://github.com/'):
        repo_part = repo_url[len('https://github.com/'):]
    else:
        raise ValueError('Unsupported URL format')
    
    auth_repo_url = f'https://{username}:{token}@github.com/{repo_part}'

    # Ensure the clone location's parent directory exists
    parent_dir = os.path.dirname(clone_location)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    # Clone the repository with the specified branch
    try:
        Repo.clone_from(auth_repo_url, clone_location, branch=branch)
        print(f"Repository cloned to {clone_location} on branch '{branch}'")
    except Exception as e:
        print(f"Error cloning repository: {e}")
        emit('error', {'message': 'Failed to clone repository'})


def pull_latest_commit(clone_location, username, token, branch='main'):
    if not os.path.exists(clone_location):
        print(f"The directory {clone_location} does not exist.")
        emit('error', {'message': 'Repository directory does not exist'})
        return

    try:
        # Open the repository
        repo = Repo(clone_location)

        # Update the remote URL with authentication
        origin = repo.remote(name='origin')
        repo_url = origin.url

        # Extract repository part from the URL
        if 'github.com/' in repo_url:
            repo_part = repo_url.split('github.com/')[1]
        else:
            raise ValueError('Unsupported URL format in existing remote')

        # Set authenticated URL
        auth_repo_url = f'https://{username}:{token}@github.com/{repo_part}'
        origin.set_url(auth_repo_url)

        # Fetch the latest commits for the specified branch
        origin.fetch(branch)

        # Check out the specified branch
        repo.git.checkout(branch)

        # Pull the latest commits
        origin.pull(branch)
        print(f"Repository at {clone_location} updated with the latest commits on branch '{branch}'.")
    except Exception as e:
        print(f"Error pulling latest commits: {e}")
        emit('error', {'message': 'Failed to pull latest commits'})


def create_directory(path):
    """
    Creates a directory at the given path. 
    If the directory (or any parent directories) do not exist, they will be created.
    
    :param path: The path where the directory should be created.
    :return: None
    """
    try:
        # os.makedirs creates all intermediate-level directories if they do not exist.
        os.makedirs(path, exist_ok=True)
        print(f"Directory '{path}' created successfully.")
    except Exception as e:
        print(f"Error creating directory '{path}': {e}")
        raise


@app.route('/')
def home():
    return jsonify({"message": "Hello from Flask on Docker!"})


@socketio.on('setup')
def handleSetup(data):

    (repo_url, containerId,clone_location, username, token, branch) = data.values()

    print("Repository URL:", repo_url)
    print("Clone Location:", clone_location)
    print("Username:", username)
    print("Token:", token)
    print("Branch:", branch)
    print("Container ID:", containerId)
    
    create_directory(clone_location)


    # Clone the repository
    clone_private_repo(repo_url, clone_location, username, token, branch)
    emit('processUpdate', {'message': 'Repository cloned'})
    emit('processComplete', {'action': 'setup'})

@socketio.on('checkFullSecurity')
def handleFullSecurityCheck(data):
    repoName = data.get('repoName')
    repo_analysis = fullRepoAnalysis(repoName)
    emit('processUpdate', {'message': 'Repo analysis complete'})
    report = analyzeRepositoryForContextAndReport(repoName, repo_analysis)
    print(report)
    emit('processUpdate', {'message': 'Context analysis complete'})
    print("Received full security check request")
    time.sleep(2)
    emit('processComplete', {'action': 'checkFullSecurity'})

@socketio.on('checkCommitSecurity')
def handleCommitSecurityCheck(data):
    affected_files = data.get('affectedFiles')  
    commit_id = data.get('commitId')
    commit_time = data.get('commitTime')

    print("Affected files: ", affected_files)
    print("Commit ID: ", commit_id)
    print("Commit time: ", commit_time)
    
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
