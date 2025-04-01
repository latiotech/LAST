from openai import OpenAI
from agents import Agent, Runner
from pydantic import BaseModel
import os
import sys
import requests
from github import Github
import subprocess
import argparse
import pathlib
import textwrap
import google.generativeai as genai
from IPython.display import display
from IPython.display import Markdown
import asyncio
try:
    from . import workers
except ImportError:
    import workers

def to_markdown(text):
    text = text.replace('•', '  *')
    return textwrap.indent(text, '> ', predicate=lambda _: True)

google_models = ['gemini-pro']

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
githubkey = os.environ.get('GITHUB_TOKEN')
googleapikey = os.environ.get('GEMINI_API_KEY')

genai.configure(api_key=googleapikey)

def get_changed_files_github(directory, base_ref, head_ref):
    """
    Returns a list of files that have been changed in the pull request, excluding deleted files.
    """
    changed_files = []
    try:
        os.chdir(directory)
        result = subprocess.check_output(["git", "diff", "--name-status", f"{base_ref}...{head_ref}"], text=True)
        lines = result.strip().split('\n')
        for line in lines:
            parts = line.split(None, 1)
            if len(parts) == 2:
                status, file_path = parts
                if status != 'D':
                    changed_files.append(file_path)
            else:
                raise ValueError(f"Unexpected format in git diff output: '{line}'")
    except subprocess.CalledProcessError as e:
        print(f"Error getting changed files: {e}")
    return changed_files


def get_changed_files(directory):
    """
    Returns a list of files that have been changed locally.
    """
    changed_files = []
    try:
        original_dir = os.getcwd()
        os.chdir(directory)
        print(f"Executing git commands in {os.getcwd()}")
        
        # Check if this is a git repository
        try:
            subprocess.check_output(["git", "rev-parse", "--is-inside-work-tree"], text=True)
        except subprocess.CalledProcessError:
            print(f"Error: {directory} is not a git repository")
            os.chdir(original_dir)
            return []
            
        try:
            # Get unstaged changes
            unstaged = subprocess.check_output(["git", "diff", "--name-only"], text=True).strip().split('\n')
            # Get staged changes
            staged = subprocess.check_output(["git", "diff", "--staged", "--name-only"], text=True).strip().split('\n')
            # Get untracked files
            untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], text=True).strip().split('\n')
            
            # Combine all changes, removing empty entries
            all_changes = [f for f in unstaged + staged + untracked if f]
            changed_files = list(set(all_changes))  # Remove duplicates
            
            print(f"Unstaged: {len([f for f in unstaged if f])}, Staged: {len([f for f in staged if f])}, Untracked: {len([f for f in untracked if f])}")
            
        except subprocess.CalledProcessError as e:
            print(f"Error executing git command: {e}")
                
        print(f"Detected {len(changed_files)} changed files")
        return changed_files
    except Exception as e:
        print(f"Unexpected error getting changed files: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if 'original_dir' in locals():
            os.chdir(original_dir)

def get_line_changes(directory, changed_files):
    """
    Returns a string containing colored line changes from the changed files.
    """
    original_dir = os.getcwd()
    line_changes = ""
    try:
        os.chdir(directory)
        print(f"Getting line changes in {os.getcwd()}")
        
        for file in changed_files:
            print(f"Processing file: {file}")
            
            # Track if we've found changes for this file
            found_changes = False
            
            # Try unstaged changes first
            try:
                result = subprocess.check_output(["git", "diff", "--", file], text=True)
                if result.strip():
                    print(f"Found unstaged changes for {file}")
                    line_changes += f"\nFile: {color_text(file, '34')}\n" 
                    for line in result.splitlines():
                        line_changes += color_diff_line(line) + "\n"
                    found_changes = True
            except subprocess.CalledProcessError as e:
                print(f"Error getting unstaged diff for {file}: {e}")
            
            # If no unstaged changes, try staged changes
            if not found_changes:
                try:
                    result = subprocess.check_output(["git", "diff", "--staged", "--", file], text=True)
                    if result.strip():
                        print(f"Found staged changes for {file}")
                        line_changes += f"\nFile: {color_text(file, '34')}\n" 
                        for line in result.splitlines():
                            line_changes += color_diff_line(line) + "\n"
                        found_changes = True
                except subprocess.CalledProcessError as e:
                    print(f"Error getting staged diff for {file}: {e}")
            
            # Check if this is an untracked file (new file)
            if not found_changes:
                try:
                    untracked_files = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], text=True).strip().split('\n')
                    if file in untracked_files:
                        print(f"{file} is an untracked file, including full content")
                        try:
                            with open(file, 'r') as f:
                                content = f.read()
                            
                            # Format as a diff for a new file
                            line_changes += f"\nFile: {color_text(file, '34')} (New File)\n"
                            line_changes += f"diff --git a/{file} b/{file}\n"
                            line_changes += f"new file mode 100644\n"
                            line_changes += f"--- /dev/null\n"
                            line_changes += f"+++ b/{file}\n"
                            
                            # Add each line with a + to indicate addition
                            for line in content.splitlines():
                                line_changes += color_diff_line("+" + line) + "\n"
                                
                            found_changes = True
                        except Exception as e:
                            print(f"Error reading untracked file {file}: {e}")
                except subprocess.CalledProcessError as e:
                    print(f"Error checking untracked files: {e}")
            
            # If still no changes found, this is unexpected
            if not found_changes:
                print(f"Warning: No changes found for {file} despite it being in the changed files list")
                try:
                    with open(file, 'r') as f:
                        content = f.read()
                    line_changes += f"\nFile: {color_text(file, '34')} (Full content - no diff available)\n"
                    for line in content.splitlines():
                        line_changes += line + "\n"
                except Exception as e:
                    print(f"Error reading file {file}: {e}")
    
    except Exception as e:
        print(f"Unexpected error in get_line_changes: {e}")
        import traceback
        traceback.print_exc()
    finally:
        os.chdir(original_dir)
        
    if not line_changes.strip():
        print("Warning: No line changes were detected for any files")
        
    return line_changes

def full_sec_scan(application_summary, model):
    """
    This function sends a code snippet to OpenAI's API to check for security vulnerabilities.
    """
    if model in google_models:
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("You are an application security expert, skilled in explaining complex programming vulnerabilities with simplicity. You will receive the full code for an application. Your task is to review the code for security vulnerabilities and suggest improvements. Don't overly focus on one file, and instead provide the top security concerns based on what you think the entire application is doing. Here is the code: " + application_summary)
            message = to_markdown(response.text)
            return message
        except Exception as e:
            return f"Error occurred: {e}"
    else:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an application security expert."},
                    {"role": "user", "content": "Please review the following code for security vulnerabilities: " + application_summary}
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            message = response.choices[0].message.content.strip()
            return message
        except Exception as e:
            return f"Error occurred: {e}"

def full_health_scan(application_summary, model):
    """
    This function sends a code snippet to OpenAI's API to check for optimizations.
    """
    if model in google_models:
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("You are a world class 10x developer who gives kind suggestions for remediating code smells and optimizing for big O complexity. You will receive the full code for an application. Your task is to review the code for optimizations and improvements, calling out the major bottlenecks. Don't overly focus on one file, and instead provide the best optimizations based on what you think the entire application is doing. Here is the code: " + application_summary)
            message = to_markdown(response.text)
            return message
        except Exception as e:
            return f"Error occurred: {e}"
    else:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a world class 10x developer."},
                    {"role": "user", "content": "Please review the following code for optimizations: " + application_summary}
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            message = response.choices[0].message.content.strip()
            return message
        except Exception as e:
            return f"Error occurred: {e}"

def full_scan(directory, model, health=False):
    """
    Scans all files in the specified directory holistically for security issues.
    """
    application_summary = ""
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    application_summary += f"\n\nFile: {file}\n"
                    application_summary += f.read()
            except UnicodeDecodeError:
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            application_summary += f"\n\nFile: {file}\n"
                            application_summary += f.read()
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
    if health:
        result = full_health_scan(application_summary, model)
    else:
        result = full_sec_scan(application_summary, model)
    return result

async def full_agent_scan(directory, model, health=False):
    """
    Scans files changed locally and includes detailed line changes for security issues.
    """
    file_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r') as f:
                    line_count = len(f.readlines())
                file_list.append(f"{file_path} ({line_count} lines)")
            except Exception as e:
                file_list.append(f"{file_path} (error reading file: {str(e)})")
    application_summary = "\n".join(file_list)

    prompt = "Here are all of the files in this application: " + application_summary
    try:
        # Try with proper error handling
        print("Sending to context agent...")
        security_tool = workers.security_agent.as_tool(
            tool_name="security_agent",
            tool_description="Specialist in evaluating code for security issues."
        ) 
        health_tool = workers.health_agent.as_tool(
            tool_name="health_agent",
            tool_description="Specialist in evaluating code for health issues."
        )
        full_context_code_gatherer = workers.full_context_agent_code.as_tool(
            tool_name="full_context_agent_code",
            tool_description="Specialist in evaluating code for security and health issues."
        )
        full_context_with_tools = workers.full_context_file_parser.clone(tools=[full_context_code_gatherer, security_tool, health_tool, workers.gather_full_code])
        result = await Runner.run(full_context_with_tools, prompt)
        result = result.final_output

        print("Received response from full context agent")
                
        return result
    except Exception as e:
        print(f"Error in context agent: {e}")
        import traceback
        traceback.print_exc()
        return color_text(f"Error during analysis: {str(e)}", "31")


def partial_sec_scan(application_summary, model):
    """
    This function sends a code snippet to OpenAI's API to check for security vulnerabilities.
    """
    if model in google_models:
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("You are an application security expert, skilled in explaining complex programming vulnerabilities with simplicity. You will receive changed code as part of a pull request, followed by the rest of the file. Your task is to review the code change for security vulnerabilities and suggest improvements. Pay attention to if the code is getting added or removed indicated by the + or - at the beginning of the line. Suggest specific code fixes where applicable. Focus the most on the code that is being changed, which starts with Detailed Line Changes, instead of Changed Files. Here is the code: " + application_summary)
            message = to_markdown(response.text)
            return message
        except Exception as e:
            return f"Error occurred: {e}"
    else:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an application security expert."},
                    {"role": "user", "content": "Please review the following code changes for security vulnerabilities: " + application_summary}
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            message = response.choices[0].message.content.strip()
            return message
        except Exception as e:
            return f"Error occurred: {e}"

def partial_health_scan(application_summary, model):
    """
    This function sends a code snippet to OpenAI's API to check for code optimizations.
    """
    if model in google_models:
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("You are a world class 10x developer who gives kind suggestions for remediating code smells and optimizing for big O complexity. You will receive changed code as part of a pull request, followed by the rest of the file. Your task is to review the changed code for optimizations and improvements, calling out any potential slowdowns. Pay attention to if the code is getting added or removed indicated by the + or - at the beginning of the line. Focus the most on the code that is being changed, which starts with Detailed Line Changes, instead of Changed Files. Here is the code: " + application_summary)
            message = to_markdown(response.text)
            return message
        except Exception as e:
            return f"Error occurred: {e}"
    else:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a world class 10x developer."},
                    {"role": "user", "content": "Please review the following code changes for optimizations: " + application_summary}
                ],
                max_tokens=1000,
                temperature=0.7,
            )
            message = response.choices[0].message.content.strip()
            return message
        except Exception as e:
            return f"Error occurred: {e}"

def github_scan(repo_name, pr_number, github_token, model, health=False):
    """
    Scans files changed in the specified GitHub pull request holistically.
    """
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    files = pr.get_files()

    changes_summary = ""
    for file in files:
        changes_summary += f"\n\nFile: {file.filename}\n"
        url = file.raw_url
        response = requests.get(url)
        if response.status_code == 200:
            changes_summary += response.text
        else:
            print(f"Failed to fetch {file.filename}")
    if health:
        result = partial_health_scan(changes_summary, model)
    else:
        result = partial_sec_scan(changes_summary, model)
    return result

def partial_scan_github(directory, base_ref, head_ref, model, health=False):
    """
    Scans files changed locally and includes detailed line changes for security issues.
    """
    changed_files = get_changed_files_github(directory, base_ref, head_ref)
    line_changes = get_line_changes(directory, changed_files)
    changes_summary = "Detailed Line Changes:\n" + line_changes + "\n\nChanged Files:\n"

    for file_path in changed_files:
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    changes_summary += f"\nFile: {file_path}\n"
                    changes_summary += f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        changes_summary += f"\nFile: {file_path}\n"
                        changes_summary += f.read()
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
        else:
            print("No changed files to scan.")
            return
        if changes_summary:
            if health:
                result = partial_health_scan(changes_summary, model)
            else:
                result = partial_sec_scan(changes_summary, model)
            return result
        else:
            return "No changed files to scan."
        return result
    else:
        return "No changed files to scan."

def color_text(text, color_code):
    """
    Returns the text wrapped in ANSI color codes.
    """
    return f"\033[{color_code}m{text}\033[0m"

def color_diff_line(line):
    """
    Returns the line wrapped in ANSI color codes based on diff output.
    """
    if line.startswith('+'):
        return color_text(line, "32") 
    elif line.startswith('-'):
        return color_text(line, "31") 
    return line

async def partial_agent_scan(directory, model, health=False):
    """
    Scans files changed locally and includes detailed line changes for security issues.
    """
    # Retrieve names of changed files
    changed_files = get_changed_files(directory)
    if changed_files is None or not changed_files:
        print("Debug: get_changed_files returned:", changed_files)
        return color_text("You haven't made any changes to test.", "31") 

    # Print names of changed files in blue
    print(color_text("Changed Files:", "34"))
    for file_path in changed_files:
        print(color_text(file_path, "34"))

    # Retrieve and print changed lines of code in green
    line_changes = get_line_changes(directory, changed_files)
    if not line_changes:
        return color_text("No changed lines to scan.", "31")  # Red text for errors
    print(color_text("\nChanged Code for Analysis:\n", "32") + line_changes)  # Don't double-color the lines

    # Prepare the summary for scanning
    changes_summary = "Detailed Line Changes:\n" + line_changes + "\n\nChanged Files:\n" + "\n".join(changed_files)
    print("Starting partial scan...")
    
    # Fix: Add space between prompt and content
    prompt = "Please analyze these code changes: \n\n" + changes_summary
    
    try:
        # Try with proper error handling
        print("Sending to context agent...")
        security_tool = workers.security_agent.as_tool(
            tool_name="security_agent",
            tool_description="Specialist in evaluating code for security issues."
        ) 
        health_tool = workers.health_agent.as_tool(
            tool_name="health_agent",
            tool_description="Specialist in evaluating code for health issues."
        )
        context_with_tools = workers.context_agent.clone(tools=[security_tool, health_tool, workers.analyze_code_context])
        result = await Runner.run(context_with_tools, prompt)
        result = result.final_output
        print("Received response from context agent")
                
        return result
    except Exception as e:
        print(f"Error in context agent: {e}")
        import traceback
        traceback.print_exc()
        return color_text(f"Error during analysis: {str(e)}", "31")

def partial_scan(directory, model, health=False):
    """
    Scans files changed locally and includes detailed line changes for security issues.
    """
    # Retrieve names of changed files
    changed_files = get_changed_files(directory)
    if changed_files is None:
        return color_text("You haven't made any changes to test.", "31") 

    # Print names of changed files in blue
    print(color_text("Changed Files:", "34"))
    for file_path in changed_files:
        print(color_text(file_path, "34"))

    # Retrieve and print changed lines of code in green
    line_changes = get_line_changes(directory, changed_files)
    if not line_changes:
        return color_text("No changed lines to scan.", "31")  # Red text for errors
    print(color_text("\nChanged Code for Analysis:\n", "32") + color_text(line_changes, "32"))  # Green text

    # Prepare the summary for scanning
    changes_summary = "Detailed Line Changes:\n" + line_changes + "\n\nChanged Files:\n" + "\n".join(changed_files)

    # Send the summary for scanning
    if health:
        result = partial_health_scan(changes_summary, model)
    else:
        result = partial_sec_scan(changes_summary, model)
    return result

def main():
    """
    Main function to perform full or partial security scanning.
    """
    # First, parse only the mode argument using sys.argv
    if len(sys.argv) < 2:
        print("Usage: latio <mode> [<directory>|<repo_name pr_number>]")
        sys.exit(1)

    mode = sys.argv[1]

    # Set the default model based on the mode
    default_model = 'gpt-4o' if mode == 'full' else 'gpt-4o'
    print("Running in mode:", mode, "with model:", default_model)

    # Set up argparse for the --model argument with the conditional default
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--model', type=str, default=default_model, help='Name of the model to use, must match exactly from https://platform.openai.com/docs/models/ or for Google Gemini use gemini-pro')
    parser.add_argument('--health', action='store_true', help='Focus on health and optimization instead of security')
    args, remaining_argv = parser.parse_known_args(sys.argv[2:])

    # Remaining arguments and main logic
    if mode == 'full':
        if len(remaining_argv) < 1:
            print("Usage for full scan: latio full <directory>")
            sys.exit(1)
        directory = remaining_argv[0]
        print(full_scan(directory, model=args.model, health=args.health))

    elif mode == 'full-agentic':
        if len(remaining_argv) < 1:
            print("Usage for full scan: latio full-agentic <directory>")
            sys.exit(1)
        directory = remaining_argv[0]
        try:
            result = asyncio.run(full_agent_scan(directory, model=args.model, health=args.health))
            print(result)
        except Exception as e:
            print(f"Error during partial scan: {e}")
            import traceback
            traceback.print_exc()

    elif mode == 'github':
        if len(remaining_argv) < 2:
            print("Usage for partial scan: latio partial <repo_name> <pr_number>")
            sys.exit(1)
        repo_name = remaining_argv[0]
        pr_number = int(remaining_argv[1])
        github_token = os.environ.get('GITHUB_TOKEN')
        print(github_scan(repo_name, pr_number, github_token, model=args.model, health=args.health))

    elif mode == 'partial-agentic':
        if len(remaining_argv) < 1:
            print("Usage for full scan: latio partial <directory>")
            sys.exit(1)
        directory = remaining_argv[0]
        # Use asyncio.run to execute the async function
        try:
            result = asyncio.run(partial_agent_scan(directory, model=args.model, health=args.health))
            print(result)
        except Exception as e:
            print(f"Error during partial scan: {e}")
            import traceback
            traceback.print_exc()

    elif mode == 'partial':
        if len(remaining_argv) < 1:
            print("Usage for full scan: latio partial <directory>")
            sys.exit(1)
        directory = remaining_argv[0]
        print(partial_scan(directory, model=args.model, health=args.health))

    elif mode == 'partial-github':
        if len(remaining_argv) < 3:
            print("Usage for github scan: latio partial-github <directory> <base_ref> <head_ref>")
            sys.exit(1)
        directory = remaining_argv[0]
        base_ref = remaining_argv[1]
        head_ref = remaining_argv[2]
        print(partial_scan_github(directory, base_ref, head_ref, model=args.model, health=args.health))

    else:
        print("Invalid mode. Use 'full' or 'partial'.")
        sys.exit(1)


if __name__ == "__main__":
    main()