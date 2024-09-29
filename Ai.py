#!/usr/bin/env python
# coding: utf-8

import os
import json


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


# Function to Analyze Repo Code using the Local Model
def analyze_repo_code(fileContent, fileName, filePath):
    
    prompt_template = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    Cutting Knowledge Date: December 2023
    Today Date: 23 July 2024

    You are a helpful assistant for code analysis. Your task is to analyze the following code file and provide a structured JSON containing:
    - file information
    - functionality description
    - functions defined
    - dependencies used

    You must respond only with the JSON structure, and end your response with the <|eot_id|> token.

    <|start_header_id|>user<|end_header_id|>
    Analyze the code below and return file information, functionality description, functions defined, dependencies used in a strict json format.

    Follow this strict json structure : 
    
    {{
      "file_info": {{
        "file_name": "name of the code file",
        "file_path": "file path of the code file"
      }},
      "functionality_description": {{
        "overview": "Provide a concise summary of the file's functionality.",
        "key_labels": ["Key actions like 'authentication', 'data processing'"],
        "functions_defined": ["List of function names defined in the code"]
      }},
      "dependencies": [
        {{
          "name": "Name of the dependency (library or file)",
          "type": "internal/external",
          "imported_elements": ["List of specific elements imported from the dependency"],
          "usage": "Description of how this dependency is used"
        }}
      ]
    }}
    
    Code file: {fileName}, located at {filePath}
    Content:
    {fileContent}<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """

    
    # Create the prompt template
    prompt = PromptTemplate(
        input_variables=["fileContent", "fileName", "filePath"],
        template=prompt_template
    )

    # Adjust the parser to use a more flexible JSON parsing (since LLaMA may not always generate perfect JSON)
    parser = JsonOutputParser()

    # Create LLMChain using the local LLaMA model
    
    chain = prompt |llm

    # Example run with 'invoke'
    
    # Execute the chain and get the structured response
    try:
        response = chain.invoke({"fileContent": fileContent, "fileName": fileName, "filePath": filePath})
        response += "<|eot_id|>"
        response = extract_from_llama_response(response)
        
    except Exception as e:
        print(f"Error generating response: {e}")
        response = None
    
    return response
# Function to Analyze the Whole Repository


def analyzeRepository(repoName):
    # Define the list of accepted programming language extensions
    accepted_extensions = {'.js', '.py', '.cpp', '.c', '.java', '.rb', '.go', '.ts', '.php', '.cs', '.swift', '.rs', '.kt'}

    repo_path = os.path.join(os.getcwd(), repoName)  # Use current directory as base

    if not os.path.isdir(repo_path):
        print(f"Repository {repoName} not found!")
        return
    
    # Dictionary to store analysis results for each file
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
                analysis_result = analyze_repo_code(file_content, filename, file_path)

                # Store the analysis result in the dictionary
                repo_analysis[file_path] = analysis_result

            except Exception as e:
                print(f"Error reading or analyzing file {file_path}: {e}")
    
    return repo_analysis

# Pretty Print the Analysis Results
def prettyAnalysisPrint(analysis):
    try:
        pretty_json = json.dumps(analysis, indent=4)
        print(pretty_json)
    except Exception as e:
        print(f"Error while pretty printing: {e}")

# Calculate Token Size Using Huggingface's Tokenizer
def calculate_token_size(analysis, tokenizer):
    """
    Calculate the token size for the whole analysis using Huggingface tokenizer.
    """
    try:
        # Convert the analysis dictionary to a string
        analysis_str = json.dumps(analysis)

        # Encode the analysis string using Huggingface tokenizer
        tokens = tokenizer.encode(analysis_str)
        token_count = len(tokens)
        
        print(f"Total token size for the analysis: {token_count} tokens")
        return token_count
    except Exception as e:
        print(f"Error while calculating token size: {e}")
        return None


# Example usage:
# repo_name = "implementation"  # Replace this with your repo folder
# repo_analysis = analyzeRepository(repo_name)
# ྄
# # Pretty print the results
# prettyAnalysisPrint(repo_analysis)

# # Calculate the token size
# calculate_token_size(repo_analysis, tokenizer)

def analyzeV(Codes, currentFile):
    prompt_template_short = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    Cutting Knowledge Date: December 2023
    Today Date: 23 July 2024

    You are a helpful assistant for code security analysis. Your task is to analyze the following code snippets and identify vulnerabilities:
    - Critical design issues
    - CVEs (Common Vulnerabilities and Exposures)
    - Insecure Code patterns, libraries etc.
    - Data compliance issues

    Only include vulnerabilities and issues from the current file because the others are being analyzed separately.

    The vulnerabilities and design issues you choose should be serious and important issues to fix, not small or irrevalant practices. The Vulnerabities must be big enough to be worth mentioning. If no vulneraties exist, you can return an empty report.

    You should respond strictly in the following JSON structure:
    [{{
      "codeSnippet": "Code section causing the issue",
      "issue": "Name of the vulnerability or design issue",
      "detailed_reason": "Reason behind why this is a security threat."
    }}]

    You must respond only with the JSON structure, and end your response with the <|eot_id|> token.

    <|start_header_id|>user<|end_header_id|>
    Analyze the following code snippets from {currentFile} and identify security vulnerabilities in strict JSON format.

    Code Snippets:
    {Codes}<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """
    
    # Create the prompt template with a placeholder for the code snippet
    prompt = PromptTemplate(
        input_variables=["Codes", "currentFile"],
        template=prompt_template_short
    )
    
    # Use the JSON parser for structured output
    parser = JsonOutputParser()

    # Create LLMChain using the local model
    
    
    chain = prompt |llm

    # Example run with 'invoke'
    
   
    # Get the structured response from the LLaMA model
    try:
        
        response = chain.invoke({"Codes": Codes, "currentFile":currentFile})
        
        response += "<|eot_id|>"
        response = extract_from_llama_response(response)
        print(response)
    except Exception as e:
        print(f"Error generating response: {e}")
        response = None
    
    return response
    
# Function to Analyze Vulnerabilities in Code
# def analyzeV(Codes, currentFile):
#     prompt_template_short = """
#     Analyze the following related code snippets and identify and code security issues -commonly found in CVEs and also common unsecure code, also analyze for critical design issues that might lead to security vulnerabilities and also check for data compliance.
#     Only include vulnerabilities and issues from the current file because the others are being analyzed seperately. 
#     You should respond strictly in the following json structure. Only include important and necessary vulnerabilities, do not include small unharmful security recommendations. 
#     codeSnippet is the section of the code that is the issue, issue should be the name of vulnerability or design issue, the reason can be a short reasoning behind it being a security threat.
    
#     [{{  "codeSnippet": "", "issue": "","detailed reason" :"" }}]

#     currentFile:{currentFile}
    
#     Codes:
#     {Codes}
    
#     """
    
#     # Create the prompt template with a placeholder for the code snippet
#     prompt = PromptTemplate(
#         input_variables=["Codes", "currentFile"],
#         template=prompt_template_short
#     )
    
#     # Use the JSON parser for structured output
#     parser = JsonOutputParser()

#     # Create LLMChain using the local model
#     chain = LLMChain(llm=llm, prompt=prompt, output_parser=parser)

#     # Get the structured response from the LLaMA model
#     response = chain.run(Codes=Codes, currentFile=currentFile)
#     print(response)
#     return response

# Function to Retrieve Related Files for Contextual Analysis
# def analyzeContext(fileContent, fileName, fMap):
#     prompt_template_short = """
#     Analyze the following file content and the repo file dependence and functionality information. Identify which files from the repo should be analyzed
#     together with the current code files content to check for code vulnerabilities, design issues that might raise security issues, and data compliance issues. FMap represents the information, functionality and dependence of each file in the repository. Return the file paths of the related files in this strict json format:
    
#     [{{  "relatedFileName": "", "relatedFilePath": "","reason" :"" }}]

    
#     FMap: {fMap}
#     File Name : {fileName}
#     File Content:
#     {fileContent}
#     """
    
#     # Create the prompt template with a placeholder for the code snippet
#     prompt = PromptTemplate(
#         input_variables=["fileContent", "fileName", "fMap"],
#         template=prompt_template_short
#     )
    
#     # Use the JSON parser for structured output
#     parser = JsonOutputParser()

#     # Create LLMChain using the local model
#     chain = LLMChain(llm=llm, prompt=prompt, output_parser=parser)

#     # Get the structured response from the LLaMA model
#     response = chain.run(fileContent=fileContent, fileName=fileName, fMap=fMap)
#     return response

def analyzeContext(fileContent, fileName, fMap):
    prompt_template_short = """
    <|begin_of_text|><|start_header_id|>system<|end_header_id|>
    Cutting Knowledge Date: December 2023
    Today Date: 23 July 2024

    You are a helpful assistant for code context analysis. Your task is to analyze the following code content and its dependencies in the repository:
    - Identify related files from the repository.
    - Highlight files that need to be analyzed together with the current file to check for vulnerabilities and compliance issues.

    Respond strictly in the following JSON structure:
    [{{
      "relatedFileName": "Name of the related file",
      "relatedFilePath": "File path of the related file",
      "reason": "Reason why the file is relevant"
    }}]

    You must respond only with the JSON structure, and end your response with the <|eot_id|> token.

    <|start_header_id|>user<|end_header_id|>
    Analyze the file content and repository context for {fileName}, and return related files in the strict JSON format.

    File Content:
    {fileContent}

    Repo Map (FMap):
    {fMap}<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """
    
    # Create the prompt template with a placeholder for the file content and fMap
    prompt = PromptTemplate(
        input_variables=["fileContent", "fileName", "fMap"],
        template=prompt_template_short
    )
    
    # Use the JSON parser for structured output
    parser = JsonOutputParser()

    # Create LLMChain using the local model
    
    chain = prompt |llm


    # Example run with 'invoke'
    
        
        
    # Get the structured response from the LLaMA model
    try:
        
        response = chain.invoke({"fileContent": fileContent, "fileName": fileName, "fMap": fMap})
        
        
        response += "<|eot_id|>"
        response = extract_from_llama_response(response)
        print(response)
    except Exception as e:
        print(f"Error generating response: {e}")
        response = None
    
    return response
relatedFiles = {}
report = []

# Function to Analyze Repository for Context
def analyzeRepositoryForContext(repoName):
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
                analysis_result = analyzeContext(fileContent=file_content, fileName=filename, fMap=repo_analysis)

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
                c_report = analyzeV(codes, filename)
                print(c_report)
                report.append({"fileName": filename, "report": c_report})
                count += 1
                
            except Exception as e:
                print(f"Error reading or analyzing file {file_path}: {e}")
            
            if count > 5:
                break
        if count > 5:
            break
    
    return relatedFiles

# Run context analysis
# analyzeRepositoryForContext(repo_name)

# # Print the reports
# for i in report:
#     prettyAnalysisPrint(i)
