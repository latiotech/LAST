from agents import Agent, function_tool, Runner
from agents.extensions.visualization import draw_graph
from agents.extensions import handoff_filters
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import subprocess
import os
from typing import List, Dict, Set

@function_tool
def analyze_code_context(function_changes: List[str], changed_files: List[str]) -> dict[str, str]:
    """
    Takes in a list of files and line changes and returns any relevant file details and application context.
    """
    # Get the file contents
    print("Changed files:", changed_files)
    file_contents = {}
    
    # Get the absolute path of the workspace root
    workspace_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    print("Workspace root:", workspace_root)
    
    for file in changed_files:
        try:
            # Construct absolute path for the file
            file_path = os.path.join(workspace_root, file)
            print(f"Attempting to read file: {file_path}")
            with open(file_path, 'r') as f:
                file_contents[file] = f.read()
        except FileNotFoundError:
            print(f"Warning: File {file_path} not found")
        except Exception as e:
            print(f"Warning: Error reading file {file_path}: {str(e)}")
    
    # Get the codebase info by searching the codebase for any .md files
    codebase_info = ""
    try:
        for root, _, files in os.walk(workspace_root):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            codebase_info += f.read() + "\n"
                    except Exception as e:
                        print(f"Warning: Error reading markdown file {file_path}: {str(e)}")
    except Exception as e:
        print(f"Warning: Error walking directory: {str(e)}")

    app_context_agent = Agent(
        name="App Context Agent",
        ),
    context_info_prompt = "You are a developer with a deep understanding of the codebase and the latest best practices. You will receive information about a codebase, changed functions, and file details. Your job is to summarize the application context, including the overall purpose of the application, the overall architecture, and the overall codebase. Here is some information about the codebase and what it's doing: " + str(codebase_info) + "\n Here is the file contents: " + str(file_contents) + "\n Here is the function changes: " + str(function_changes)
    app_context = Runner.run(app_context_agent, context_info_prompt)
    return app_context

@function_tool
def gather_full_code(changed_files: List[str]):
    """
    Takes in a list of files and line changes and returns any relevant file details and application context.
    Each line in the returned file contents will be prefixed with its line number.
    """
    # Get the file contents
    print("Analyzing files:", changed_files)
    file_contents = {}
    
    # Get the absolute path of the workspace root
    workspace_root = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    print("Workspace root:", workspace_root)
    
    for file in changed_files:
        try:
            # Construct absolute path for the file
            file_path = os.path.join(workspace_root, file)
            with open(file_path, 'r') as f:
                # Read lines and add line numbers
                print(f"Reading file: {file_path}")
                lines = f.readlines()
                numbered_lines = [f"{i+1}: {line}" for i, line in enumerate(lines)]
                file_contents[file] = ''.join(numbered_lines)
        except FileNotFoundError:
            print(f"Warning: File {file_path} not found")
        except Exception as e:
            print(f"Warning: Error reading file {file_path}: {str(e)}")
    
    return file_contents

security_agent = Agent(
    name="Security Agent",
    handoff_description="Specialist in evaluating code for security issues.",
    instructions=(
    """
    {RECOMMENDED_PROMPT_PREFIX}
    You are a super friendly security expert with a deep understanding of the codebase and the latest security best practices.
    You will be given a list of files and code snippets to evaluate for security issues, as well as additional context about the codebase.
    Give the user a short summary of the security issues you found, the files they were found in, the lines of code that are affected, and some fix guidance with an example specific to the user's code.
    """
    ),
)

health_agent = Agent(
    name="Health Agent",
    handoff_description="Specialist in evaluating code for health issues.",
    instructions=(
    "You are a 10x developer with a deep understanding of the codebase and the latest health best practices."
    "You will be given a list of files and code snippets to evaluate for health issues, as well as additional context about the codebase    ."
    "Give the user a short summary of the health issues you found, the files they were found in, the lines of code that are affected, and some fix guidance with an example."
    ),
)

context_agent = Agent(
    name="Context Agent",
    handoff_description="Specialist in evaluating code for security and health issues.",
    instructions=(
    "You are a coding expert with a deep understanding of the codebase and the latest security and health best practices."
    "You will be given a list of files and lines of code that have been changed in a pull request. You will first find all relevant code and files related to the changes."
    "The analyze_code_context function takes in a list of function changes based on the line changes you're seeing, as well as their file paths, and returns a summary of the relevant code and files."
    "This will be a lot of information to process, so condense this information for the security and health agents: what the application is generally doing, what the files are doing in the context of the application, and what the function changes are doing in the context of the files."
    "Then, based on the relevant code you find, you will hand off to the security agent or the health agent. It is essential that the original code changes "
    "If there are potential security issues to investigate, handoff to the security agent."
    "If there are potential health issues to investigate, handoff to the health agent."
    "If there are no issues, return a message to the user that the pull request is good to go."
    ),
    handoffs=[security_agent, health_agent],
    tools=[analyze_code_context],
)

full_context_agent_code = Agent(
    name="Full Context Agent Code Gatherer",
    handoff_description="Specialist in evaluating code for security and health issues.",
    instructions=("""
    {RECOMMENDED_PROMPT_PREFIX}
    You are a coding expert with a deep understanding of the codebase and the latest security and health best practices."
    You will be given a list of files for analysis. You will first fetch all of the code for these files using the analyze_code_context function."
    This will be a lot of information to process, so condense this information for the security and health agents: what the application is generally doing, what the files are doing in the context of the application, and the specific lines of code that are most relevant for analysis."
    If there are potential security issues to investigate, handoff to the security agent with the most relevant code."
    If there are potential health issues to investigate, handoff to the health agent with the most relevant code."
    If there are no issues, return a message to the user that the code has no issues."
    """ 
    ),
    handoffs=[security_agent, health_agent],
    tools=[gather_full_code],
)

full_context_file_parser = Agent(
    name="Full Context Agent File Parser",
    handoff_description="Specialist in evaluating code for security and health issues.",
    instructions=(
    "You are a coding expert with a deep understanding of the codebase and the latest security and health best practices."
    "You are going to receive a list of files, return only the ones that seem the most relevant for security or health analysis."
    "Then, you will make sure to drop any files that seem they will be larger than your context window."
    "You will then hand off the relevant files to the full context agent code gatherer to analyze the code."
    ),
    handoffs=[full_context_agent_code],
)