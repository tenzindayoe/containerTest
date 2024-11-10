import os 
import requests
import logging
import redis
import hashlib
import json

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

    count = 0
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
                codes += "_____________________________________"
                codes += "\n Related / Dependant Code files \n"

                for rf in analysis_result:
                    related_file_name = rf.get("relatedFileName")
                    related_file_path = rf.get("relatedFilePath")

                    if not related_file_name or not related_file_path:
                        logger.warning(f"Invalid related file info for {file_path}: {rf}")
                        continue

                    # Construct the absolute path to the related file
                    related_full_path = os.path.join(repo_path, related_file_path)

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
                count += 1
                
            except Exception as e:
                logger.error(f"Error reading or analyzing file {file_path}: {e}")
            
            if count >= 5:
                break
        if count >= 5:
            break
    
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
            analysis_result = None
            
            if cached_context_analysis:
                analysis_result = json.loads(cached_context_analysis)
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
                    redis
    
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
                related_full_path = os.path.join(repo_path, related_file_path)
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

    count = 0
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

                try:
                    response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_context', json=data)
                    response.raise_for_status()
                except requests.RequestException as e:
                    logger.error(f"Error sending context request to the API for {file_path}: {e}")
                    continue

                # Parse the context analysis response
                analysis_result = response.json() if response.status_code == 200 else None

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
                    related_full_path = os.path.join(repo_path, related_file_path)

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

                try:
                    vulnerability_response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_compliance', json=vulnerability_data)
                    vulnerability_response.raise_for_status()
                except requests.RequestException as e:
                    logger.error(f"Error sending vulnerability request to the API for {file_path}: {e}")
                    continue

                # Parse the vulnerability analysis response
                c_report = vulnerability_response.json() if vulnerability_response.status_code == 200 else None

                if c_report is None:
                    logger.warning(f"Failed to analyze vulnerabilities for {file_path}, Status Code: {vulnerability_response.status_code}")
                    continue

                logger.info(f"Vulnerability Report for {file_path}: {c_report}")
                report.append({"fileName": filename, "report": c_report})
                count += 1
                
            except Exception as e:
                logger.error(f"Error reading or analyzing file {file_path}: {e}")
            
            if count >= 5:
                break
        if count >= 5:
            break
    
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

            try:
                context_response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_context', json=context_data)
                context_response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Error sending context request to the API for {file_path}: {e}")
                continue

            # Parse the context analysis response
            context_analysis = context_response.json() if context_response.status_code == 200 else None

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
                related_full_path = os.path.join(repo_path, related_file_path)
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

            try:
                vulnerability_response = requests.post('http://llama3_1CodeSecu_service:8000/analyze_compliance', json=vulnerability_data)
                vulnerability_response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Error sending vulnerability request to the API for {file_path}: {e}")
                continue

            # Parse the vulnerability analysis response
            vulnerability_report = vulnerability_response.json() if vulnerability_response.status_code == 200 else None

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

