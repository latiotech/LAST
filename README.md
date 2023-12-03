# LAST
Latio Application Security Tester

# How to Run it

1. Get your OpenAI token from [here](https://platform.openai.com/api-keys)
2. `export OPENAI_API_KEY={YOUR OPENAI KEY GOES HERE}`
3. Run `python LAST.py partial` to scan only the changes on your PR. This uses the GPT-3.5-turbo model so it's cheap and fast
4. Run `python LAST.py full {/path/to/directory}` to do a full application scan. This uses the beta model of gpt-4 so it's extremely expensive. Scanning this application once for example took about $1. Additionally, you may need to split your app into smaller directories, because the model has a 128,000 token limit 

# Future Improvements
1. For full directory scans, calculate number of tokens in advanced and split up the files
2. Same for Partial Scans
3. Finish Dockerfile and github scan option to allow running in pipeline as a GitHub action
