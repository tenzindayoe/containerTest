import os 
import requests


def read_file(file_path):
    """
    Reads the content of a file and returns it as a string.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def fullRepoAnalysis(repoName):
    accepted_extensions = {'.js', '.py', '.cpp', '.c', '.java', '.rb', '.go', '.ts', '.php', '.cs', '.swift', '.rs', '.kt'}

    repo_path = os.path.join(os.getcwd(), repoName)  # Use current directory as base

    if not os.path.isdir(repo_path):
        print(f"Repository {repoName} not found!")
        return
    repo_analysis = {}
    # Walk through all files in the repo
    for dirpath, _, filenames in os.walk(repo_path):
        for filename in filenames:
            # Get the full file path
            file_path = os.path.join(dirpath, filename)

            # Check if the file has an accepted extension
            _, file_extension = os.path.splitext(file_path)
            if file_extension.lower() not in accepted_extensions:
                print(f"Skipping {file_path} (not a programming file)")
                continue
            
            # Read the file content
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_content = file.read()

                # Analyze the file
                print(f"Analyzing {file_path}...")

                data = {
                    'file_name': filename,
                    'file_path': file_path,
                    'file_content': file_content
                }

                # Send the request to the API ('localhost:3000/getAnalysis')
                response = requests.post('http://localhost:8000/analyze_repo_code', json=data)

                # Check the response status
                if response.status_code == 200:
                    analysis_result = response.json()
                else:
                    print(f"Failed to analyze {file_path}, Status Code: {response.status_code}")
                    analysis_result = None


                # Store the analysis result in the dictionary
                repo_analysis[file_path] = analysis_result

            except Exception as e:
                print(f"Error reading or analyzing file {file_path}: {e}")
    
    return repo_analysis

def analyzeRepositoryForContextAndReport(repoName, repo_analysis):
    relatedFiles = {}
    report = {}
    # Define the list of accepted programming language extensions
    accepted_extensions = {'.js', '.py', '.cpp', '.c', '.java', '.rb', '.go', '.ts', '.php', '.cs', '.swift', '.rs', '.kt'}
    repo_path = os.path.join(os.getcwd(), repoName)  # Use current directory as base
    if not os.path.isdir(repo_path):
        print(f"Repository {repoName} not found!")
        return

    count = 0
    # Walk through all files in the repo
    for dirpath, _, filenames in os.walk(repo_path):
        for filename in filenames:
            # Get the full file path
            file_path = os.path.join(dirpath, filename)

            # Check if the file has an accepted extension
            _, file_extension = os.path.splitext(file_path)
            if file_extension.lower() not in accepted_extensions:
                print(f"Skipping {file_path} (not a programming file)")
                continue
            
            # Read the file content
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_content = file.read()

                # Analyze the file
                print(f"Analyzing {file_path}...")

                #send a request to the API ('localhost:3000/getContext')
                data = {
                    'file_name': filename,
                    'file_content': file_content,
                    'fMap': repo_analysis
                }

                response = requests.post('http://localhost:8000/analyze_context', json=data)

                analysis_result = None
                # Check the response status
                if response.status_code == 200:
                    analysis_result = response.json()
                else:
                    print(f"Failed to analyze {file_path}, Status Code: {response.status_code}")
                    analysis_result = None

                # Store the analysis result in the dictionary
                relatedFiles[filename] = analysis_result

                # Prepare the codes for vulnerability analysis
                codes = "_____________________________________\n"
                codes += "Code File under analysis : \n"
                codes += filename + "\n" + file_content
                codes += "_____________________________________"
                codes += "\n Related / Dependant Code files \n"

                for rf in analysis_result:
                    codes += rf["relatedFileName"] + "\n"
                    codes += read_file(rf["relatedFilePath"]) 
                    codes += "\n"
                    codes += "_____________________________________\n"
                
                # Analyze vulnerabilities


                #send api request 
                data = {
                    'file_name': filename,
                    'file_content': codes
                }
                response = requests.post('http://localhost:8000/analyze_vulnerabilities', json=data)
                c_report = None
                # Check the response status
                if response.status_code == 200:
                    c_report = response.json()
                else:
                    print(f"Failed to analyze {file_path}, Status Code: {response.status_code}")
                    c_report = None
                print(c_report)
                report.append({"fileName": filename, "report": c_report})
                count += 1
                
            except Exception as e:
                print(f"Error reading or analyzing file {file_path}: {e}")
            
            if count > 5:
                break
        if count > 5:
            break
    
    return report