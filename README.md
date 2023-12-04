# Latio Application Security Tester
Just using OpenAI to scan your files for security issues because it does a better job than most of the paid ones. Bring your own OpenAI token.

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
3. Run `python LAST.py partial /path/to/directory` to scan only the changes on your branch. This uses the GPT-3.5-turbo model so it's cheap and fast
4. Run `python LAST.py full /path/to/directory` to do a full application scan. This uses the beta model of gpt-4 so it's extremely expensive. Scanning this application once for example took about $1. Additionally, you may need to split your app into smaller directories, because the model has a 128,000 token limit 

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
