from openai import OpenAI
import os
import sys
import requests
from github import Github
import subprocess

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
            status, file_path = line.split(maxsplit=1)
            if status != 'D':  # Exclude deleted files
                changed_files.append(file_path)
    except subprocess.CalledProcessError as e:
        print(f"Error getting changed files: {e}")
    return changed_files


def get_changed_files(directory):
    """
    Returns a list of files that have been changed in the pull request, excluding deleted files.
    """
    changed_files = []
    try:
        os.chdir(directory)
        result = subprocess.check_output(["git", "diff", "--name-status"], text=True)
        lines = result.strip().split('\n')
        for line in lines:
            status, file_path = line.split(maxsplit=1)
            if status != 'D':  # Exclude deleted files
                changed_files.append(file_path)
    except subprocess.CalledProcessError as e:
        print(f"Error getting changed files: {e}")
    return changed_files


def get_line_changes_github(directory, base_ref, head_ref):
    """
    Returns a string containing line changes between the base and head branches of a pull request.
    """
    line_changes = ""
    try:
        os.chdir(directory)
        # Getting line changes between the base and head branches of the PR
        result = subprocess.check_output(["git", "diff", f"{base_ref}...{head_ref}"], text=True)
        line_changes = result.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting line changes: {e}")
    return line_changes

def get_line_changes(directory):
    """
    Returns a string containing line changes from the latest commit.
    """
    line_changes = ""
    try:
        os.chdir(directory)
        # Getting line changes for the last commit
        result = subprocess.check_output(["git", "diff", "HEAD~1", "HEAD"], text=True)
        line_changes = result.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting line changes: {e}")
    return line_changes

def full_sec_scan(application_summary):
    """
    This function sends a code snippet to OpenAI's API to check for security vulnerabilities.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4-1106-preview",  # Choose the appropriate engine
            messages=[ 
                {"role": "system", "content": "You are an application security expert, skilled in explaining complex programming vulnerabilities with simplicity. You will receive the code for the application, or just the changed code. Your task is to review the code for security vulnerabilities and suggest improvements."},
                {"role": "user", "content": application_summary}
            ]
        )
        message = response.choices[0].message.content
        return message
    except Exception as e:
        return f"Error occurred: {e}"

def full_scan(directory):
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
    result = full_sec_scan(application_summary)
    return result

def partial_sec_scan(application_summary):
    """
    This function sends a code snippet to OpenAI's API to check for security vulnerabilities.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",  # Choose the appropriate engine
            messages=[ 
                {"role": "system", "content": "You are an application security expert, skilled in explaining complex programming vulnerabilities with simplicity. You will receive just the changed code and need to make assumptions about the rest of the application. Your task is to review the code for security vulnerabilities and suggest improvements."},
                {"role": "user", "content": application_summary}
            ]
        )
        message = response.choices[0].message.content
        return message
    except Exception as e:
        return f"Error occurred: {e}"

def github_scan(repo_name, pr_number, github_token):
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
    result = partial_sec_scan(changes_summary)
    return result

def partial_scan_github(directory, base_ref, head_ref):
    """
    Scans files changed locally and includes detailed line changes for security issues.
    """
    changed_files = get_changed_files_github(directory, base_ref, head_ref)
    line_changes = get_line_changes_github(directory, base_ref, head_ref)
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
            result = partial_sec_scan(changes_summary)
            return result
        else:
            return "No changed files to scan."
        return result
    else:
        return "No changed files to scan."

def partial_scan(directory):
    """
    Scans files changed locally and includes detailed line changes for security issues.
    """
    changed_files = get_changed_files(directory)
    line_changes = get_line_changes(directory)
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
        result = partial_sec_scan(changes_summary)
        return result
    else:
        return "No changed files to scan."

def main():
    """
    Main function to perform full or partial security scanning.
    """
    if len(sys.argv) < 2:
        print("Usage: python LAST.py.py <mode> [<directory>|<repo_name pr_number>]")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == 'full':
        if len(sys.argv) < 3:
            print("Usage for full scan: python LAST.py.py full <directory>")
            sys.exit(1)
        directory = sys.argv[2]
        print(full_scan(directory))

    elif mode == 'github':
        if len(sys.argv) < 4:
            print("Usage for partial scan: python LAST.py.py partial <repo_name> <pr_number>")
            sys.exit(1)
        repo_name = sys.argv[2]
        pr_number = int(sys.argv[3])
        github_token = os.environ.get('GITHUB_TOKEN')
        print(github_scan(repo_name, pr_number, github_token))

    elif mode == 'partial':
        if len(sys.argv) < 3:
            print("Usage for full scan: python LAST.py.py partial <directory>")
            sys.exit(1)
        directory = sys.argv[2]
        print(partial_scan(directory))

    elif mode == 'partial-github':
        if len(sys.argv) < 3:
            print("Usage for full scan: python LAST.py.py partial <directory>")
            sys.exit(1)
        directory = sys.argv[2]
        base_ref = sys.argv[3]
        head_ref = sys.argv[4]
        print(partial_scan_github(directory, base_ref, head_ref))

    else:
        print("Invalid mode. Use 'full' or 'partial'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
