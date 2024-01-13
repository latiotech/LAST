# Latio Application Security Tester
Use OpenAI to scan your code for security issues from the CLI. Bring your own OpenAI token.

![GitHub release (latest by date)](https://img.shields.io/github/v/release/latiotech/LAST)
![GitHub issues](https://img.shields.io/github/issues/latiotech/LAST)
![GitHub pull requests](https://img.shields.io/github/issues-pr/latiotech/LAST)
![GitHub](https://img.shields.io/github/license/latiotech/LAST)
![GitHub stars](https://img.shields.io/github/stars/latiotech/LAST?style=social)

[About Latio](https://latio.tech)  
[Find Security Tools](https://latio.tech)  
[Discord](https://discord.gg/k5aBQ55j5M)

- [Install](#Install)
- [How to Run Locally](#how-to-run-locally)
- [How to Run in Pipeline](#how-to-run-in-pipeline)

# Install

```bash
pip install latio

OPENAI_API_KEY=xxx latio partial ./ 
```

# How to Run Locally

1. Get your OpenAI key from [here](https://platform.openai.com/api-keys)
2. `export OPENAI_API_KEY=<OpenAPI Key>`
3. Scan only your changed files before merging with `python latio partial /path/to/directory`. This uses the GPT-3.5-turbo model so it's cheap and fast.
4. Scan your full application with `python latio full /path/to/directory`. This uses the beta model of gpt-4 so it's extremely expensive. Scanning this application once for example took about $1. Additionally, you may need to split your app into smaller directories, because the model has a 128,000 token limit 

# How to Run in Pipeline

This will run OpenAI in pipeline against only your changed files. [Here's an example](https://github.com/latiotech/insecure-kubernetes-deployments/actions/runs/7081197080/job/19270126283?pr=6) of what it looks like, it uses GPT-3.5 to scan only changed files, so it's relatively cheap.

1. Get your OpenAI token from [here](https://platform.openai.com/api-keys)
2. In your repository, go to `github.com/org/repo/settings/secrets/actions` and add a new Repository Secret called `OPENAI_API_KEY` with the value from OpenAI
3. Copy and paste the `.github/workflows/actions-template.yml` into your own `.github/workflows/` folder

