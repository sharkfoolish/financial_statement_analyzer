import os
from dotenv import load_dotenv
from openai import OpenAI

class OpenAIClient:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("API_KEY")
        base_url = "https://openrouter.ai/api/v1"
        # Initialize the client with API key and base URL
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def get_response(self, data, question):

        # Format the question as per the requirement
        question = f'請根據這些數據「{data}」回答「{question}」'

        try:
            # Make the API call to get the response
            response = self.client.chat.completions.create(
                model="meta-llama/llama-3.1-70b-instruct:free",
                messages=[{"role": "user", "content": f"{question}\n"}],
                stream=False
            )

            if response and response.choices:
                # Return the content of the first choice
                return response.choices[0].message.content
            else:
                return "錯誤：未收到有效的回應或選項。"
        except Exception as e:
            # Return error if any occurs
            return f"發生錯誤: {e}"