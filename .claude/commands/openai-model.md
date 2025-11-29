When working with OpenAI API in this project, you MUST follow these rules:

1. **Only use `gpt-5.1`** - Do NOT use gpt-4o, gpt-4, or any other model
2. **No max_tokens parameter** - The gpt-5.1 model does not support this parameter
3. **Use centralized config** - Import the model name from `backend/settings/constants.py` as `OPENAI_MODEL`
4. **Never hardcode** - Always reference the constant, never hardcode "gpt-5.1" directly in API calls

If you find any code using a different model, update it to use the `OPENAI_MODEL` constant from `backend/settings/constants.py`.
