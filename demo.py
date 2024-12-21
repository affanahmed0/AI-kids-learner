import openai

# Set up your OpenAI API key
openai.api_key = 'your-api-key-here'

def ask_chatgpt(prompt):
    # Call OpenAI's GPT-3 API
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150,
        temperature=0.5
    )
    
    # Extract the response text
    result = response.choices[0].text.strip()
    return result
    