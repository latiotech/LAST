# Latio Application Security Tester
Use OpenAI to scan your code for security issues from the CLI. Bring your own OpenAI token.

Example input: [Insecure Deployments Repo](https://github.com/latiotech/insecure-kubernetes-deployments) `python LAST.py full ~/git/insecure-kubernetes-deployments/`
Example output:
```
## Security Review Summary

### Environment File Exposure
- `.env` file is present. This file is commonly used for storing environment variables which might include secrets and credentials. Ensure that sensitive information is not present in this file or it is appropriately secured.

### CODEOWNERS Utilization
- `CODEOWNERS` file found. It specifies `* @confusedcrib`, meaning all changes require review from `confusedcrib`. This is a good practice to maintain oversight over codebase changes.

### Kubernetes Deployment Configurations
Files like `busybox.yaml`, `workload-security-evaluator.yaml`, and `insecure-app.yaml` provide insight into how the applications are deployed within Kubernetes, including image sources, replica counts, and labels. Several potential issues are noted:
- Privileged containers and the mounting of the Docker socket suggest elevated privileges that could be a security risk if the containers are compromised.
- AWS credentials are hardcoded within the `workload-security-evaluator.yaml` and `insecure-app.yaml` files, which is a significant security risk, as anyone with access to these files can misuse these credentials.
- Services are exposed on SSH ports within Kubernetes configurations (`NodePort` for SSH), which could potentially expose the services to unwanted network access if not properly secured.

### Python Script for Ransomware (ransomware.py)
The script `ransomware.py` presents a severe security risk. The code encrypts files on the target system using cryptography, signals of attempting to change the desktop wallpaper, interact with DLLs, and request ransom in Bitcoin. While this may be a proof-of-concept or for educational purposes, having this stored in an application repository is hazardous.

### Dockerfile
The `Dockerfile` seems to install necessary packages and setups for running an application. It does not show direct signs of security issues, but it is always recommended to use trusted base images and to keep the images minimal for what is needed.

### Application Python Script (app.py)
The script `app.py` allows for running commands directly from web input, which is a critical security vulnerability known as an injection attack. The file upload function must also be carefully managed to avoid arbitrary file upload vulnerabilities.

### Various Kubernetes Related Secure Practices
- `.gitignore` identifies certain files and directories to be ignored by version control which can be both a good security practice as well as a potential risk if sensitive files are not correctly identified to be excluded.
- Sample files for git hooks (`*.sample`) are default templates. They provide examples of what can be achieved through hooks; any active hook scripts should be reviewed for security implications.

### Possible Exposed Secrets
Files such as `COMMIT_EDITMSG`, `index`, and other Git-related metadata files contain references or traceability elements which do not present a direct vulnerability but can provide intel if the repository is public.

### Continuous Integration and Deployment (CI/CD) Configuration
The `publish-insecure.yml` file for GitHub Actions details automated Docker image building and pushing to Docker Hub upon new releases. Credentials are secured using GitHub secrets, following best practices. However, vulnerabilities within the application or the Dockerfile could lead to weaknesses in the published container.

### Miscellaneous Concerns
- The `LAST.yml` potentially triggers the cited "LAST" Python utility. It’s running with the environment variable `OPENAI_API_KEY` from GitHub secrets. Any security risks would depend on the logic within the `LAST.py` script.
- The Git hook samples are committed as `.sample`. They should be reviewed and modified if they are used to enforce security policies.
- The presence of what seems to be a UUID or token in `packed-refs` and some other files may require examination.

### Recommendations:
- Securely handle and rotate any exposed credentials immediately and ensure they are stored using secured methods like a secret management system.
- Review and remediate the Python ransomware script appropriately.
- Validate the input and secure the file upload feature in the `app.py` to protect against remote code execution and file upload vulnerabilities.
- Secure Docker images by ensuring base images are trusted and kept minimal.
- Ensure Kubernetes deployments follow the principle of least privilege and are securely configured.
- Use Git hooks effectively for security but ensure their scripts enforce the intended security policies.
- Continuously monitor and audit CI/CD workflows to ensure they are secure and can't be exploited.

```

In marketing terms:
LAST is the worlds first end to end AI application scanning solution, covering:

1. ASPM
2. SAST
3. IaC
4. Container
5. SDLC 

# How to Run Locally

1. Get your OpenAI key from [here](https://platform.openai.com/api-keys)
2. `export OPENAI_API_KEY=<OpenAPI Key>`
3. Scan only your changed files before merging with `python LAST.py partial /path/to/directory`. This uses the GPT-3.5-turbo model so it's cheap and fast.
4. Scan your full application with `python LAST.py full /path/to/directory`. This uses the beta model of gpt-4 so it's extremely expensive. Scanning this application once for example took about $1. Additionally, you may need to split your app into smaller directories, because the model has a 128,000 token limit 

# How to Run in Pipeline

This will run OpenAI in pipeline against only your changed files. [Here's an example](https://github.com/latiotech/insecure-kubernetes-deployments/actions/runs/7081197080/job/19270126283?pr=6) of what it looks like, it uses GPT-3.5 to scan only changed files, so it's relatively cheap.

1. Get your OpenAI token from [here](https://platform.openai.com/api-keys)
2. In your repository, go to `github.com/org/repo/settings/secrets/actions` and add a new Repository Secret called `OPENAI_API_KEY` with the value from OpenAI
3. Copy and paste the `.github/workflows/actions-template.yml` into your own `.github/workflows/` folder

# Future Improvements
1. For full directory scans, calculate number of tokens in advanced and split up the files
2. Same for Partial Scans
3. Finish Dockerfile for more elegant pipeline scanning
4. Make export data in more common format
