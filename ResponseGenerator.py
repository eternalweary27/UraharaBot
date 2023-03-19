import openai
import random

openai.api_key = None


class AICharacterResponseGenerator:
    def __init__(self,model, character, max_response_size):
        self.model = model
        self.character = character
        self.max_response_size = max_response_size
        self.chat_history = []
        self.resetChatHistory()

    def resetChatHistory(self):
         self.chat_history = [{"role": "system", "content": "Starting ChatGPT"}]

    def updateResponseMode(self, initial_prompt):
        self.chat_history += [
            {"role": "user", "content": initial_prompt},
            {"role": "assistant", "content": "Sure, I can do that. How can I assist you?"},
        ]

    def getRandomResponseMode(self):
        rand_var = random.uniform(0,1)
        if (rand_var <= 0.65):
            return "Chat"

        if (0.65 < rand_var <= 0.825):
            return "Joke"

        if (rand_var > 0.825):
            return "Fact"

    def getRandomPromptMessage(self, response_mode):
        prompt_message = "Respond to all following messages as if you were {}. Respond {}. Keep the responses to a maximum of {} characters."
        response_style = None
        if response_mode == "Chat":
            response_style = "in a {} way with a {} undertone"
            primary = ["goofy and witty", "comical and clever", "wacky and eccentric", "deriding and taunting", "silly and ridiculous", "snarky and playful"]
            secondary = ["cheerful", "sinister", "mysterious", "dark", "sarcastic", "facetious", "laid-back", "optimistic", "chaotic", "unhinged"]
            response_style = response_style.format(primary[random.randint(0,len(primary)-1)], secondary[random.randint(0,len(secondary)-1)])

        elif response_mode == "Joke":
            response_style = "with a relevant joke"

        elif response_mode == "Fact":
            response_style = "with a fun and relevant fact or trivia"

        else:
            raise Exception("Unsupported Response Mode")

        prompt_message = prompt_message.format(self.character, response_style, self.max_response_size)
        return prompt_message

    def getResponse(self, user_text):
        rand_response_mode = self.getRandomResponseMode()
        rand_prompt_message = self.getRandomPromptMessage(rand_response_mode)
        self.updateResponseMode(rand_prompt_message)
        user_message = {"role": "user", "content": user_text}
        self.chat_history.append(user_message)
        response = openai.ChatCompletion.create(model=self.model,messages=self.chat_history)
        assistant_message = {"role": "assistant", "content": response.choices[0].message.content}
        self.chat_history.append(assistant_message)
        return response