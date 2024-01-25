from openai import OpenAI
import os
import sys
import requests
from github import Github
import subprocess
import argparse

openaikey = os.environ.get('OPENAI_API_KEY')
githubkey = os.environ.get('GITHUB_TOKEN')

client = OpenAI(api_key=openaikey)

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
        os.chdir(directory)
        result = subprocess.check_output(["git", "diff", "--name-status"], text=True)
        if not result.strip():
            return None  # Indicate no changes
        lines = result.strip().split('\n')
        for line in lines:
            if line:  # Check if the line is not empty
                status, file_path = line.split(maxsplit=1)
                if status != 'D':  # Exclude deleted files
                    changed_files.append(file_path)
    except subprocess.CalledProcessError as e:
        print(f"Error getting changed files: {e}")
    return changed_files

def get_line_changes(directory, changed_files):
    """
    Returns a string containing colored line changes from the changed files.
    """
    line_changes = ""
    try:
        os.chdir(directory)
        for file in changed_files:
            result = subprocess.check_output(["git", "diff", "--", file], text=True)
            if result.strip():
                line_changes += f"\nFile: {color_text(file, '34')}\n" 
                for line in result.splitlines():
                    line_changes += color_diff_line(line) + "\n"
    except subprocess.CalledProcessError as e:
        print(f"Error getting line changes: {e}")
    return line_changes

def full_sec_scan(application_summary, model):
    """
    This function sends a code snippet to OpenAI's API to check for security vulnerabilities.
    """
    try:
        response = client.chat.completions.create(
            model=model,  # Choose the appropriate engine
            messages=[ 
                {"role": "system", "content": "You are an application security expert, skilled in explaining complex programming vulnerabilities with simplicity. You will receive the full code for an application. Your task is to review the code for security vulnerabilities and suggest improvements. Don't overly focus on one file, and instead provide the top security concerns based on what you think the entire application is doing."},
                {"role": "user", "content": application_summary}
            ]
        )
        message = response.choices[0].message.content
        return message
    except Exception as e:
        return f"Error occurred: {e}"
    
def full_health_scan(application_summary, model):
    """
    This function sends a code snippet to OpenAI's API to check for optimizations.
    """
    try:
        response = client.chat.completions.create(
            model=model,  # Choose the appropriate engine
            messages=[ 
                {"role": "system", "content": "You are a world class 10x developer who gives kind suggestions for remediating code smells and optimizing for big O complexity. You will receive the full code for an application. Your task is to review the code for optimizations and improvements, calling out the major bottlenecks. Don't overly focus on one file, and instead provide the best optimizations based on what you think the entire application is doing."},
                {"role": "user", "content": application_summary}
            ]
        )
        message = response.choices[0].message.content
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

import time

def partial_sec_scan(application_summary, model):
    """
    This function sends a code snippet to OpenAI's API to check for security vulnerabilities.
    """
    try:
        print("Waiting for response from AI...")
        # Send the request
        response = client.chat.completions.create(
            model=model,  # Choose the appropriate engine
            messages=[ 
                {"role": "system", "content": "You are an application security expert, skilled in explaining complex programming vulnerabilities with simplicity. You will receive changed code as part of a pull request, followed by the rest of the file. Your task is to review the code change for security vulnerabilities and suggest improvements. Pay attention to if the code is getting added or removed indicated by the + or - at the beginning of the line. Suggest specific code fixes where applicable. Focus the most on the code that is being changed, which starts with Detailed Line Changes, instead of Changed Files."},
                {"role": "user", "content": application_summary}
            ]
        )
        message = response.choices[0].message.content
        return message
    except Exception as e:
        return f"Error occurred: {e}"
    
def partial_health_scan(application_summary, model):
    """
    This function sends a code snippet to OpenAI's API to check for code optimizations.
    """
    try:
        print("Waiting for response from AI...")
        # Send the request
        response = client.chat.completions.create(
            model=model,  # Choose the appropriate engine
            messages=[ 
                {"role": "system", "content": "You are a world class 10x developer who gives kind suggestions for remediating code smells and optimizing for big O complexity. You will receive changed code as part of a pull request, followed by the rest of the file. Your task is to review the changed code for optimizations and improvements, calling out any potential slowdowns. Pay attention to if the code is getting added or removed indicated by the + or - at the beginning of the line. Focus the most on the code that is being changed, which starts with Detailed Line Changes, instead of Changed Files."},
                {"role": "user", "content": application_summary}
            ]
        )
        message = response.choices[0].message.content
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
    default_model = 'gpt-4-1106-preview' if mode == 'full' else 'gpt-3.5-turbo'

    # Set up argparse for the --model argument with the conditional default
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--model', type=str, default=default_model, help='Name of the OpenAI model to use, must match exactly from https://platform.openai.com/docs/models/')
    parser.add_argument('--health', action='store_true', help='Focus on health and optimization instead of security')
    args, remaining_argv = parser.parse_known_args(sys.argv[2:])

    # Remaining arguments and main logic
    if mode == 'full':
        if len(remaining_argv) < 1:
            print("Usage for full scan: latio full <directory>")
            sys.exit(1)
        directory = remaining_argv[0]
        print(full_scan(directory, model=args.model, health=args.health))

    elif mode == 'github':
        if len(remaining_argv) < 2:
            print("Usage for partial scan: latio partial <repo_name> <pr_number>")
            sys.exit(1)
        repo_name = remaining_argv[0]
        pr_number = int(remaining_argv[1])
        github_token = os.environ.get('GITHUB_TOKEN')
        print(github_scan(repo_name, pr_number, github_token, model=args.model, health=args.health))

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