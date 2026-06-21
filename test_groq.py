"""One-shot test: confirm Groq API connection works."""
import os
from groq import Groq

client = Groq()  # reads GROQ_API_KEY from env automatically
response = client.chat.completions.create(
    model="llama-3.1-8b-instant",
    messages=[{"role": "user", "content": "Say hello in 5 words"}],
    temperature=0,
)
print(response.choices[0].message.content)
