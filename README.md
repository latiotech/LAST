<p align="center"><img src="https://raw.githubusercontent.com/latiotech/LAST/main/logo.png" width="150" ><br><h1 align="center">Latio Application Security Tester</h1></p>

![GitHub stars](https://img.shields.io/github/stars/latiotech/LAST?style=social)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/latiotech/LAST)
![GitHub issues](https://img.shields.io/github/issues/latiotech/LAST)
![GitHub pull requests](https://img.shields.io/github/issues-pr/latiotech/LAST)
![GitHub](https://img.shields.io/github/license/latiotech/LAST)
[![Discord](https://img.shields.io/discord/1119809850239614978)](https://discord.gg/k5aBQ55j5M)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/latio)](https://pypi.org/project/latio/)

<h3>Use OpenAI to scan your code for security issues from the CLI. Bring your own OpenAI token. Options to scan full code, code changes, or in pipeline.</h3></br>
<p align="center"><img src="https://raw.githubusercontent.com/latiotech/LAST/main/LAST.gif" width=75% ></p>
</br>
</br>

[About Latio](https://latio.tech)  
[Find Security Tools](https://list.latio.tech)  

- [Install](#Install)
- [How to Run Locally](#how-to-run-locally)
- [How to Run in Pipeline](#how-to-run-in-pipeline)
- [Command Line Options](#command-line-options)

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
5. You can specify `--model` with the [model name from open ai](https://platform.openai.com/docs/models) to experiment

# How to Run in Pipeline

This will run OpenAI in pipeline against only your changed files. [Here's an example](https://github.com/latiotech/insecure-kubernetes-deployments/actions/runs/7619084201/job/20845086343) of what it looks like, it uses GPT-3.5 to scan only changed files, so it's relatively cheap.

1. Get your OpenAI token from [here](https://platform.openai.com/api-keys)
2. In your repository, go to `github.com/org/repo/settings/secrets/actions` and add a new Repository Secret called `OPENAI_API_KEY` with the value from OpenAI
3. Copy and paste the `.github/workflows/actions-template-security.yml` (or `-health` for health scan) into your own `.github/workflows/` folder.

# Command Line Options

## `latio partial <directory> [--model <model_name>] [--health]`

Scans only the files that have been changed in the specified directory.

- `<directory>`: Path to the directory where your project is located.
- `--model <model_name>`: (Optional) Specifies the name of the OpenAI model to use for the scan. Defaults to `gpt-3.5-turbo`
- `--health`: (Optional) Runs a prompt focused on code optimization

Example:
```bash
latio partial /path/to/your/project --model gpt-3.5-turbo --health
```

## `latio full <directory> [--model <model_name>] [--health]`

Scans only the files that have been changed in the specified directory.

- `<directory>`: Path to the directory where your project is located.
- `--model <model_name>`: (Optional) Specifies the name of the OpenAI model to use for the scan. Defaults to `gpt-4-1106-preview`
- `--health`: (Optional) Runs a prompt focused on code optimization

Example:
```bash
latio full /path/to/your/project --model gpt-4-1106-preview --health
```
