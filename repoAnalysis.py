import os
import git
from datetime import datetime
from git import Repo as GitRepo
from git.exc import GitCommandErrord
class Repo:
    def __init__(self, url, cloneLocation):
        self.url = url
        self.cloneLocation = os.path.abspath(cloneLocation)
        self.jsonDirStructure = {}
        self.latestCommitVersion = ""
        self.latestCommitTime = None
        self.repo = None

    def gitAccountSetup(self, email, username, token):
        """
        Set up Git credentials using the provided email, username, and personal access token.
        """
        try:
            # Set global Git config for user email
            os.system(f"git config --global user.email '{email}'")
            os.system(f"git config --global --add safe.directory {self.cloneLocation}")
            # Store credentials securely for the session
            os.environ['GIT_ASKPASS'] = 'echo'
            os.environ['GIT_USERNAME'] = username
            os.environ['GIT_PASSWORD'] = token

            print("Git account setup complete.")
        except Exception as e:
            print(f"Error setting up Git account: {e}")

    def clone(self):
        """
        Clone the repository to the specified cloneLocation, using credentials.
        """
        try:
            # Use the credentials for the cloning process
            url_with_credentials = f"https://{os.getenv('GIT_USERNAME')}:{os.getenv('GIT_PASSWORD')}@github.com/{self.url.split('https://github.com/')[-1]}"
            
            # Clone the repository with credentials
            self.repo = GitRepo.clone_from(url_with_credentials, self.cloneLocation)
            print(f"Repository cloned to {self.cloneLocation}")
            
            # Mark the directory as safe to avoid any ownership issues
            

        except GitCommandError as e:
            print(f"Error cloning repository: {e}")

    def setGit(self):
        """
        Initialize the Git repository object if not already set.
        """
        if not self.repo:
            self.repo = GitRepo(self.cloneLocation)
        print("Git repo object set.")

    def getLatestCommitInfo(self):
        """
        Get information about the latest commit (commit hash, commit time, affected files).
        """
        try:
            self.setGit()  # Ensure the Git repository is set
            
            latest_commit = self.repo.head.commit

            # Extract commit details
            self.latestCommitVersion = latest_commit.hexsha
            self.latestCommitTime = datetime.fromtimestamp(latest_commit.committed_date)
            affected_files = latest_commit.stats.files

            # Print commit info
            print(f"Latest commit hash: {self.latestCommitVersion}")
            print(f"Commit time: {self.latestCommitTime}")
            print(f"Affected files: {list(affected_files.keys())}")
            return list(affected_files.keys())

        except Exception as e:
            print(f"Error fetching latest commit info: {e}")
            return []



def setup(repo_url, clone_location, email, username, token):
    # Create a Repo instance
    my_repo = Repo(repo_url, clone_location)
    # Set up Git credentials (use a valid personal access token)
    my_repo.gitAccountSetup(email, username, token)
    # Clone the repository
    my_repo.clone()
    # Get the latest commit and its affected files
    my_repo.getLatestCommitInfo()


def checkFullSecurity():
    print()

def checkCommitSecurity():
    print()

def checkFullCompliance():

    print()

def checkCommitCompliance():
    print()

