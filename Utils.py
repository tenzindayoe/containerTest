import os 
import requests
import logging
import redis
import hashlib
import json
import subprocess
import re


def generateSaastReport(file_path):
    # Check if the file has a .py extension
    if not file_path.endswith(".py"):
        print("Error: The specified file is not a Python file.")
        return None
    
    # Verify if the file exists
    if not os.path.isfile(file_path):
        print("Error: The specified file does not exist.")
        return None

    try:
        # Run Bandit on the specified file and capture output
        result = subprocess.run(
            ["bandit", file_path],
            capture_output=True,
            text=True
        )
        
        # Extract issues from the stdout output
        output_lines = result.stdout.splitlines()
        issues = []
        current_issue = {}

        for line in output_lines:
            # Detect each new issue
            if line.startswith(">> Issue:"):
                # Save the previous issue if populated
                if current_issue:
                    # Retrieve code snippet if line number is available
                    if 'line_number' in current_issue:
                        line_num = current_issue['line_number']
                        current_issue['code_snippet'] = get_code_snippet(file_path, line_num)
                    issues.append(current_issue)
                # Start a new issue
                current_issue = {"issue": line.split(":", 1)[1].strip()}
            elif "Severity:" in line and "Confidence:" in line:
                # Extract severity and confidence
                severity_match = re.search(r"Severity:\s(\w+)", line)
                confidence_match = re.search(r"Confidence:\s(\w+)", line)
                if severity_match and confidence_match:
                    current_issue["severity"] = severity_match.group(1)
                    current_issue["confidence"] = confidence_match.group(1)
            elif "CWE:" in line:
                # Extract CWE information
                cwe_match = re.search(r"CWE:\s([\w-]+)\s\((https[^\)]+)\)", line)
                if cwe_match:
                    current_issue["cwe"] = cwe_match.group(1)
                    current_issue["cwe_url"] = cwe_match.group(2)
            elif "More Info:" in line:
                # Extract more info URL
                more_info_url = line.split(":", 1)[1].strip()
                current_issue["more_info"] = more_info_url
            elif "Location:" in line:
                # Extract file location and line numbers
                location_info = line.split(":", 1)[1].strip()
                current_issue["location"] = location_info
                # Extract line number from location info
                location_match = re.search(r":(\d+):", location_info)
                if location_match:
                    current_issue["line_number"] = int(location_match.group(1))
            elif line.startswith("Code scanned:"):
                # Save the last issue if it's populated
                if current_issue:
                    # Retrieve code snippet if line number is available
                    if 'line_number' in current_issue:
                        line_num = current_issue['line_number']
                        current_issue['code_snippet'] = get_code_snippet(file_path, line_num)
                    issues.append(current_issue)
                break  # Exit parsing as we’ve reached the end of issues

        return issues

    except FileNotFoundError:
        print("Error: Bandit is not installed. Install it with `pip install bandit`.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_code_snippet(file_path, line_number, context_lines=2):
    """
    Extracts a code snippet around a given line number from the file.
    Includes a few lines above and below the issue line for context.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            start = max(line_number - context_lines - 1, 0)
            end = min(line_number + context_lines, len(lines))
            return ''.join(lines[start:end]).strip()
    except Exception as e:
        print(f"Error reading file {file_path} for code snippet: {e}")
        return None



redis_host = os.getenv('REDIS_HOST', 'redis_server')
redis_port = os.getenv('REDIS_PORT', 6379)
redis_client = redis.Redis(host=redis_host, port=redis_port)

def test_redis_connection():
    try:
        # Attempt to set and get a test key
        redis_client.set("test_key", "test_value")
        value = redis_client.get("test_key")
        if value == b"test_value":
            print("Redis connection successful!")
        else:
            print("Redis connection failed: Unexpected value")
    except redis.ConnectionError as e:
        print(f"Redis connection failed: {e}")

test_redis_connection()



def string_to_sha256(input_string):
    input_bytes = input_string.encode('utf-8')
    sha256_hash = hashlib.sha256()
    sha256_hash.update(input_bytes)
    return sha256_hash.hexdigest()

# Configure logging to output to stdout with the INFO level
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def read_file(file_path):
    """
    Reads the content of a file and returns it as a string.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return None


def fullRepoAnalysis(repoPath):
    """
    Analyzes all relevant files in the repository.

    Parameters:
    - repoPath (str): The path to the repository.

    Returns:
    - repo_analysis (dict): A dictionary with file paths as keys and analysis results as values.
    """
    accepted_extensions = {'.js', '.py', '.cpp', '.c', '.java', '.rb', '.go', '.ts', '.php', '.cs', '.swift', '.rs', '.kt'}

    repo_path = repoPath  # repoPath is the absolute path to the repository

    if not os.path.isdir(repo_path):
        logger.error(f"Repository {repoPath} not found!")
        return {}

    repo_analysis = {}
    # Walk through all files in the repo
    for dirpath, _, filenames in os.walk(repo_path):
        for filename in filenames:
            # Get the full file path
            file_path = os.path.join(dirpath, filename)

            # Check if the file has an accepted extension
            _, file_extension = os.path.splitext(filename)
            if file_extension.lower() not in accepted_extensions:
                logger.info(f"Skipping {file_path} (not a programming file)")
                continue
            
            # Read the file content
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_content = file.read()
                # Analyze the file
                logger.info(f"Analyzing {file_path}...")
                logger.debug(f"File content: {file_content}")    
                data = {
                    'fileName': filename,
                    'filePath': file_path,
                    'fileContent': file_content
                }

                searchQuery = "repoAnalysis:" + file_content
                cached_analysis = redis_client.get(searchQuery)
                analysis_result = None
                if cached_analysis:
                    # If found in Redis, use the cached result
                    analysis_result = json.loads(cached_analysis)
                    print(f"Cache hit for {file_path}")
                else:
                    # Send the request to the API
                    try:
                        response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_repo_code', json=data)
                        response.raise_for_status()
                    except requests.RequestException as e:
                        logger.error(f"Error sending request to the API for {file_path}: {e}")
                        continue
    
                    # Parse the response
                    analysis_result = response.json() if response.status_code == 200 else None
                    if analysis_result != None:
                        redis_client.set(searchQuery, json.dumps(analysis_result))

                if analysis_result is None:
                    logger.warning(f"Failed to analyze {file_path}, Status Code: {response.status_code}")
                    continue

                # Store the analysis result in the dictionary
                repo_analysis[file_path] = analysis_result

            except Exception as e:
                logger.error(f"Error reading or analyzing file {file_path}: {e}")
    
    return repo_analysis


def analyzeRepositoryForContextAndReport(repoPath, repo_analysis):
    """
    Analyzes the repository for context and generates a vulnerability report.

    Parameters:
    - repoPath (str): The path to the repository.
    - repo_analysis (dict): Analysis data from fullRepoAnalysis.

    Returns:
    - report (list): A list of dictionaries containing file names and their vulnerability reports.
    """
    relatedFiles = {}
    report = []
    accepted_extensions = {'.js', '.py', '.cpp', '.c', '.java', '.rb', '.go', '.ts', '.php', '.cs', '.swift', '.rs', '.kt'}
    repo_path = repoPath  # repoPath is the absolute path to the repository

    if not os.path.isdir(repo_path):
        logger.error(f"Repository {repoPath} not found!")
        return report

    
    # Walk through all files in the repo
    for dirpath, _, filenames in os.walk(repo_path):
        for filename in filenames:
            # Get the full file path
            file_path = os.path.join(dirpath, filename)

            # Check if the file has an accepted extension
            _, file_extension = os.path.splitext(filename)
            if file_extension.lower() not in accepted_extensions:
                logger.info(f"Skipping {file_path} (not a programming file)")
                continue
            
            # Read the file content
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_content = file.read()

                logger.info(f"Analyzing {file_path} for context...")

                # Send a request to the API for context analysis
                data = {
                    'fileName': filename,
                    'fileContent': file_content,
                    'fMap': repo_analysis
                }
                context_search_query = "context:" + string_to_sha256(file_content)
                vulnerability_search_query = "vulnerability:" + string_to_sha256(file_content)

                cached_context_analysis = redis_client.get(context_search_query)
                analysis_result = None
                
                if cached_context_analysis:
                    analysis_result = json.loads(cached_context_analysis)
                else:
                    try:
                        response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_context', json=data)
                        response.raise_for_status()
                    except requests.RequestException as e:
                        logger.error(f"Error sending context request to the API for {file_path}: {e}")
                        continue
    
                    # Parse the context analysis response
                    analysis_result = response.json() if response.status_code == 200 else None
                    if analysis_result != None:
                        redis_client.set(context_search_query, json.dumps(analysis_result))

                if analysis_result is None:
                    logger.warning(f"Failed to analyze context for {file_path}, Status Code: {response.status_code}")
                    continue

                # Store the analysis result in the dictionary
                relatedFiles[filename] = analysis_result

                # Prepare the codes for vulnerability analysis
                codes = "_____________________________________\n"
                codes += "Code File under analysis : \n"
                codes += f"{filename}\n{file_content}"
                saast_report = generateSaastReport(file_path)
                if saast_report:
                    codes += "\n_____________________________________\n"
                    codes += "Static Application Security Testing (SAST) report : \n"
                    codes += json.dumps(saast_report, indent=2)
                codes += "_____________________________________"
                codes += "\n Related / Dependant Code files \n"

                for rf in analysis_result:
                    related_file_name = rf.get("relatedFileName")
                    related_file_path = rf.get("relatedFilePath")

                    if not related_file_name or not related_file_path:
                        logger.warning(f"Invalid related file info for {file_path}: {rf}")
                        continue

                    related_full_path = related_file_path
                    logger.info(f"Using absolute path for related file: {related_full_path}")
          
                    # Read the related file content
                    related_content = read_file(related_full_path)
                    
                    if related_content:
                        codes += f"{related_file_name}\n{related_content}\n"
                        codes += "_____________________________________\n"
                    else:
                        logger.warning(f"Could not read related file: {related_full_path}")
                
                # Analyze vulnerabilities
                vulnerability_data = {
                    'fileName': filename,
                    'fileContent': codes
                }

                cached_vulnerability_report = redis_client.get(vulnerability_search_query)
                c_report = None
                if cached_vulnerability_report:
                    c_report = json.loads(cached_vulnerability_report)
                    print(f"Vulnerability cache hit for {file_path}")
                else:
                    try:
                        vulnerability_response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_vulnerabilities', json=vulnerability_data)
                        vulnerability_response.raise_for_status()
                    except requests.RequestException as e:
                        logger.error(f"Error sending vulnerability request to the API for {file_path}: {e}")
                        continue
    
                    # Parse the vulnerability analysis response
                    c_report = vulnerability_response.json() if vulnerability_response.status_code == 200 else None
                    if c_report !=None : 
                        redis_client.set(vulnerability_search_query, json.dumps(c_report))
                        
                    if c_report is None:
                        logger.warning(f"Failed to analyze vulnerabilities for {file_path}, Status Code: {vulnerability_response.status_code}")
                        continue

                logger.info(f"Vulnerability Report for {file_path}: {c_report}")
                report.append({"fileName": filename, "report": c_report})
               
                
            except Exception as e:
                logger.error(f"Error reading or analyzing file {file_path}: {e}")
            
            
     
    
    return report


def analyzeASetOfFilesForContextAndReport(repoPath, filepathsArr, repo_analysis):
    """
    Analyzes a specific set of files within a repository for context and generates vulnerability reports.

    Parameters:
    - repoPath (str): The path to the repository.
    - filepathsArr (list): List of file paths to analyze within the repository.
    - repo_analysis (dict): Analysis data from fullRepoAnalysis.

    Returns:
    - report (list): A list of dictionaries containing file names and their vulnerability reports.
    """
    report = []
    accepted_extensions = {'.js', '.py', '.cpp', '.c', '.java', '.rb', '.go', '.ts', '.php', '.cs', '.swift', '.rs', '.kt'}
    repo_path = repoPath  # repoPath is the absolute path to the repository

    if not os.path.isdir(repo_path):
        logger.error(f"Repository {repoPath} not found!")
        return report

    for file_relative_path in filepathsArr:
        # Construct the absolute file path
        file_path = os.path.join(repo_path, file_relative_path)

        # Check if the file exists
        if not os.path.isfile(file_path):
            logger.warning(f"File {file_path} does not exist. Skipping.")
            continue

        # Check if the file has an accepted extension
        _, file_extension = os.path.splitext(file_path)
        if file_extension.lower() not in accepted_extensions:
            logger.info(f"Skipping {file_path} (not a programming file)")
            continue

        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()

            logger.info(f"Analyzing {file_path} for context...")

            # Send a request to the context analysis API
            context_data = {
                'fileName': os.path.basename(file_path),
                'fileContent': file_content,
                'fMap': repo_analysis
            }
            context_search_query = "context:" + string_to_sha256(file_content)
            vulnerability_search_query = "vulnerability:" + string_to_sha256(file_content)

            cached_context_analysis = redis_client.get(context_search_query)
            
            context_analysis = None
            if cached_context_analysis:
                context_analysis = json.loads(cached_context_analysis)
                print(f"Context cache hit for {file_path}")
            else:
                try:
                    context_response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_context', json=context_data)
                    context_response.raise_for_status()
                except requests.RequestException as e:
                    logger.error(f"Error sending context request to the API for {file_path}: {e}")
                    continue
    
                # Parse the context analysis response
                context_analysis = context_response.json() if context_response.status_code == 200 else None

                if context_analysis != None : 
                    redis_client.set(context_search_query, json.dumps(context_analysis))
    
                if context_analysis is None:
                    logger.warning(f"Failed to analyze context for {file_path}, Status Code: {context_response.status_code}")
                    continue

            # Prepare the combined code for vulnerability analysis
            combined_code = "_____________________________________\n"
            combined_code += "Code File under analysis : \n"
            combined_code += f"{os.path.basename(file_path)}\n{file_content}"
            saast_report = generateSaastReport(file_path)
            if saast_report:
                combined_code += "\n_____________________________________\n"
                combined_code += "Static Application Security Testing (SAST) report : \n"
                combined_code += json.dumps(saast_report, indent = 2)
            combined_code += "_____________________________________\n"
            combined_code += "Related / Dependant Code files \n"

            for related_file in context_analysis:
                related_file_name = related_file.get("relatedFileName")
                related_file_path = related_file.get("relatedFilePath")
                
                if not related_file_name or not related_file_path:
                    logger.warning(f"Invalid related file info for {file_path}: {related_file}")
                    continue

                # Construct the absolute path to the related file
           
                related_full_path = related_file_path
                logger.info(f"Using absolute path for related file: {related_full_path}")
               
                
                related_content = read_file(related_full_path)
                
                if related_content:
                    combined_code += f"{related_file_name}\n{related_content}\n"
                    combined_code += "_____________________________________\n"
                else:
                    logger.warning(f"Could not read related file: {related_full_path}")

            # Send the combined code to the vulnerability analysis API
            vulnerability_data = {
                'fileName': os.path.basename(file_path),
                'fileContent': combined_code
            }

            cached_vulnerability_report = redis_client.get(vulnerability_search_query)
            vulnerability_report = None
            if cached_vulnerability_report:
                vulnerability_report = json.loads(cached_vulnerability_report)
                print(f"Vulnerability cache hit for {file_path}")
            else:
                try:
                    vulnerability_response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_vulnerabilities', json=vulnerability_data)
                    vulnerability_response.raise_for_status()
                except requests.RequestException as e:
                    logger.error(f"Error sending vulnerability request to the API for {file_path}: {e}")
                    continue
    
                # Parse the vulnerability analysis response
                vulnerability_report = vulnerability_response.json() if vulnerability_response.status_code == 200 else None
                if vulnerability_report !=None : 
                    redis_client.set(vulnerability_search_query, json.dumps(vulnerability_report))
                if vulnerability_report is None:
                    logger.warning(f"Failed to analyze vulnerabilities for {file_path}, Status Code: {vulnerability_response.status_code}")
                    continue

            logger.info(f"Vulnerability Report for {file_path}: {vulnerability_report}")

            report.append({
                "fileName": os.path.basename(file_path),
                "report": vulnerability_report
            })

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")

    return report



def analyzeRepositoryForContextAndComplianceReport(repoPath, repo_analysis, userCompText):
    """
    Analyzes the repository for context and generates a vulnerability report.

    Parameters:
    - repoPath (str): The path to the repository.
    - repo_analysis (dict): Analysis data from fullRepoAnalysis.

    Returns:
    - report (list): A list of dictionaries containing file names and their vulnerability reports.
    """
    relatedFiles = {}
    report = []
    accepted_extensions = {'.js', '.py', '.cpp', '.c', '.java', '.rb', '.go', '.ts', '.php', '.cs', '.swift', '.rs', '.kt'}
    repo_path = repoPath  # repoPath is the absolute path to the repository

    if not os.path.isdir(repo_path):
        logger.error(f"Repository {repoPath} not found!")
        return report

   
    # Walk through all files in the repo
    for dirpath, _, filenames in os.walk(repo_path):
        for filename in filenames:
            # Get the full file path
            file_path = os.path.join(dirpath, filename)

            # Check if the file has an accepted extension
            _, file_extension = os.path.splitext(filename)
            if file_extension.lower() not in accepted_extensions:
                logger.info(f"Skipping {file_path} (not a programming file)")
                continue
            
            # Read the file content
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    file_content = file.read()

                logger.info(f"Analyzing {file_path} for context...")

                # Send a request to the API for context analysis
                data = {
                    'fileName': filename,
                    'fileContent': file_content,
                    'fMap': repo_analysis
                }
                context_search_query = "context:" + string_to_sha256(file_content)
                compliance_search_query = "compliance:" + string_to_sha256(file_content)

                cached_context_analysis = redis_client.get(context_search_query)
                analysis_result = None

                if cached_context_analysis:
                    analysis_result = json.loads(cached_context_analysis)
                    print(f"Context cache hit for {file_path}")
                else:
                    try:
                        response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_context', json=data)
                        response.raise_for_status()
                    except requests.RequestException as e:
                        logger.error(f"Error sending context request to the API for {file_path}: {e}")
                        continue
    
                    # Parse the context analysis response
                    analysis_result = response.json() if response.status_code == 200 else None
                    if analysis_result != None:
                        redis_client.set(context_search_query, json.dumps(analysis_result))
                    if analysis_result is None:
                        logger.warning(f"Failed to analyze context for {file_path}, Status Code: {response.status_code}")
                        continue

                # Store the analysis result in the dictionary
                relatedFiles[filename] = analysis_result

                # Prepare the codes for vulnerability analysis
                codes = "_____________________________________\n"
                codes += "Code File under analysis : \n"
                codes += f"{filename}\n{file_content}"
                codes += "_____________________________________"
                codes += "\n Related / Dependant Code files \n"

                for rf in analysis_result:
                    related_file_name = rf.get("relatedFileName")
                    related_file_path = rf.get("relatedFilePath")

                    if not related_file_name or not related_file_path:
                        logger.warning(f"Invalid related file info for {file_path}: {rf}")
                        continue

                    # Construct the absolute path to the related file
                    related_full_path = related_file_path

                    # Read the related file content
                    related_content = read_file(related_full_path)
                    
                    if related_content:
                        codes += f"{related_file_name}\n{related_content}\n"
                        codes += "_____________________________________\n"
                    else:
                        logger.warning(f"Could not read related file: {related_full_path}")
                
   

                vulnerability_data = {
                    'fileName': filename,
                    'fileContent': codes,
                    'userDefinedPolicies': userCompText
                }
                cached_compliance_analysis = redis_client.get(compliance_search_query)

                c_report = None
                if cached_compliance_analysis:
                    c_report = json.loads(cached_compliance_analysis)
                    print(f"Compliance cache hit for {file_path}")
                else:
                    try:
                        vulnerability_response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_compliance', json=vulnerability_data)
                        vulnerability_response.raise_for_status()
                    except requests.RequestException as e:
                        logger.error(f"Error sending vulnerability request to the API for {file_path}: {e}")
                        continue
    
                    # Parse the vulnerability analysis response
                    c_report = vulnerability_response.json() if vulnerability_response.status_code == 200 else None
                    if c_report != None : 
                        redis_client.set(compliance_search_query, json.dumps(c_report))
                    if c_report is None:
                        logger.warning(f"Failed to analyze vulnerabilities for {file_path}, Status Code: {vulnerability_response.status_code}")
                        continue

                logger.info(f"Vulnerability Report for {file_path}: {c_report}")
                report.append({"fileName": filename, "report": c_report})
             
                
            except Exception as e:
                logger.error(f"Error reading or analyzing file {file_path}: {e}")
            

    
    return report



def analyzeASetOfFilesForContextAndComplianceReport(repoPath, filepathsArr, repo_analysis,userCompText):
    """
    Analyzes a specific set of files within a repository for context and generates vulnerability reports.

    Parameters:
    - repoPath (str): The path to the repository.
    - filepathsArr (list): List of file paths to analyze within the repository.
    - repo_analysis (dict): Analysis data from fullRepoAnalysis.

    Returns:
    - report (list): A list of dictionaries containing file names and their vulnerability reports.
    """
    report = []
    accepted_extensions = {'.js', '.py', '.cpp', '.c', '.java', '.rb', '.go', '.ts', '.php', '.cs', '.swift', '.rs', '.kt'}
    repo_path = repoPath  # repoPath is the absolute path to the repository

    if not os.path.isdir(repo_path):
        logger.error(f"Repository {repoPath} not found!")
        return report

    for file_relative_path in filepathsArr:
        # Construct the absolute file path
        file_path = os.path.join(repo_path, file_relative_path)

        # Check if the file exists
        if not os.path.isfile(file_path):
            logger.warning(f"File {file_path} does not exist. Skipping.")
            continue

        # Check if the file has an accepted extension
        _, file_extension = os.path.splitext(file_path)
        if file_extension.lower() not in accepted_extensions:
            logger.info(f"Skipping {file_path} (not a programming file)")
            continue

        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as file:
                file_content = file.read()

            logger.info(f"Analyzing {file_path} for context...")

            # Send a request to the context analysis API
            context_data = {
                'fileName': os.path.basename(file_path),
                'fileContent': file_content,
                'fMap': repo_analysis
            }

            context_search_query = "context:" + string_to_sha256(file_content)
            compliance_search_query = "compliance:" + string_to_sha256(file_content)

            cached_context_analysis = redis_client.get(context_search_query)
            context_analysis = None

            if cached_context_analysis:
                context_analysis = json.loads(cached_context_analysis)
                print(f"Context cache hit for {file_path}")
            else:
                try:
                    context_response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_context', json=context_data)
                    context_response.raise_for_status()
                except requests.RequestException as e:
                    logger.error(f"Error sending context request to the API for {file_path}: {e}")
                    continue
    
                # Parse the context analysis response
                context_analysis = context_response.json() if context_response.status_code == 200 else None
                if context_analysis != None: 
                    redis_client.set(context_search_query, json.dumps(context_analysis))
                    
                if context_analysis is None:
                    logger.warning(f"Failed to analyze context for {file_path}, Status Code: {context_response.status_code}")
                    continue

            # Prepare the combined code for vulnerability analysis
            combined_code = "_____________________________________\n"
            combined_code += "Code File under analysis : \n"
            combined_code += f"{os.path.basename(file_path)}\n{file_content}"
            combined_code += "_____________________________________\n"
            combined_code += "Related / Dependant Code files \n"

            for related_file in context_analysis:
                related_file_name = related_file.get("relatedFileName")
                related_file_path = related_file.get("relatedFilePath")
                
                if not related_file_name or not related_file_path:
                    logger.warning(f"Invalid related file info for {file_path}: {related_file}")
                    continue

                # Construct the absolute path to the related file
                related_full_path =related_file_path
                related_content = read_file(related_full_path)
                
                if related_content:
                    combined_code += f"{related_file_name}\n{related_content}\n"
                    combined_code += "_____________________________________\n"
                else:
                    logger.warning(f"Could not read related file: {related_full_path}")

            # Send the combined code to the vulnerability analysis API
            vulnerability_data = {
                'fileName': os.path.basename(file_path),
                'fileContent': combined_code,
                'userDefinedPolicies': userCompText
            }
            cached_compliance_analysis = redis_client.get(compliance_search_query)

            vulnerability_report = None
            if cached_compliance_analysis:
                vulnerability_report = json.loads(cached_compliance_analysis)
                print(f"Compliance cache hit for {file_path}")
            else:
                try:
                    vulnerability_response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_compliance', json=vulnerability_data)
                    vulnerability_response.raise_for_status()
                except requests.RequestException as e:
                    logger.error(f"Error sending vulnerability request to the API for {file_path}: {e}")
                    continue
    
                # Parse the vulnerability analysis response
                vulnerability_report = vulnerability_response.json() if vulnerability_response.status_code == 200 else None
                if vulnerability_report != None : 
                    redis_client.set(compliance_search_query, json.dumps(vulnerability_report))
                    
                if vulnerability_report is None:
                    logger.warning(f"Failed to analyze vulnerabilities for {file_path}, Status Code: {vulnerability_response.status_code}")
                    continue

            logger.info(f"Vulnerability Report for {file_path}: {vulnerability_report}")

            report.append({
                "fileName": os.path.basename(file_path),
                "report": vulnerability_report
            })

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")

    return report

