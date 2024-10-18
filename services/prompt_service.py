from utils.chatgpt import generate_response

class PromptService:
    async def handle_chatgpt_conversation(self, user_input, prompt_id):
        async for chunk in generate_response(user_input, prompt_id):
            yield chunk