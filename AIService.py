from flask import Flask, request, jsonify
import os
import json
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, BitsAndBytesConfig
from langchain_huggingface import HuggingFacePipeline
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.output_parsers import JsonOutputParser
import torch

torch.cuda.empty_cache()

app = Flask(__name__)

# Load the model and tokenizer
model_name = "NousResearch/Hermes-2-Pro-Llama-3-8B"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto",
)

terminators = [
    tokenizer.eos_token_id,
    tokenizer.convert_tokens_to_ids("<|eot_id|>")
]

pipe = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=5000,
    do_sample=True,
    temperature=0.1,
    top_p=0.85,
    top_k=50,
    eos_token_id=terminators,
    pad_token_id=tokenizer.eos_token_id,
)

llm = HuggingFacePipeline(pipeline=pipe)


def extract_from_llama_response(output_text):
    try:
        start_token = "<|start_header_id|>assistant<|end_header_id|>"
        end_token = "<|eot_id|>"

        if start_token in output_text and end_token in output_text:
            start_index = output_text.index(start_token) + len(start_token)
            end_index = output_text.index(end_token, start_index)
            assistant_response = output_text[start_index:end_index].strip()

            try:
                json_data = json.loads(assistant_response)
                return json_data
            except json.JSONDecodeError:
                return assistant_response
        else:
            return None
    except Exception as e:
        return {"error": str(e)}


@app.route('/analyze_repo_code', methods=['POST'])
def analyze_repo_code_api():
    data = request.get_json()
    file_content = data.get('fileContent')
    file_name = data.get('fileName')
    file_path = data.get('filePath')

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

    Code file: {fileName}, located at {filePath}
    Content:
    {fileContent}<|eot_id|>
    <|start_header_id|>assistant<|end_header_id|>
    """
    
    prompt = PromptTemplate(input_variables=["fileContent", "fileName", "filePath"], template=prompt_template)
    
    chain = prompt | llm
    try:
        response = chain.invoke({"fileContent": file_content, "fileName": file_name, "filePath": file_path})
        response += "<|eot_id|>"
        structured_response = extract_from_llama_response(response)
        return jsonify(structured_response)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/analyze_context', methods=['POST'])
def analyze_context_api():
    data = request.get_json()
    file_content = data.get('fileContent')
    file_name = data.get('fileName')
    fMap = data.get('fMap')

    prompt_template = """
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
    
    prompt = PromptTemplate(input_variables=["fileContent", "fileName", "fMap"], template=prompt_template)
    
    chain = prompt | llm
    try:
        response = chain.invoke({"fileContent": file_content, "fileName": file_name, "fMap": fMap})
        response += "<|eot_id|>"
        structured_response = extract_from_llama_response(response)
        return jsonify(structured_response)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/analyze_vulnerabilities', methods=['POST'])
def analyze_vulnerabilities_api():
    data = request.get_json()
    code_snippets = data.get('Codes')
    current_file = data.get('currentFile')

    prompt_template = """
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
    
    prompt = PromptTemplate(input_variables=["Codes", "currentFile"], template=prompt_template)
    
    chain = prompt | llm
    try:
        response = chain.invoke({"Codes": code_snippets, "currentFile": current_file})
        response += "<|eot_id|>"
        structured_response = extract_from_llama_response(response)
        return jsonify(structured_response)
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == '__main__':
    app.run(debug=True)
