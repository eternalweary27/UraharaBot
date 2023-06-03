import openai
import random

openai.api_key = None

class ResponseMode:
    def __init__(self,name,response_style, probability):
        self.name = name
        self.response_style = response_style
        self.probability = probability

class CharacterSettings:
    def __init__(self, character_name, primary_traits, secondary_traits, response_modes):
        self.character_name = character_name
        self.primary_traits = primary_traits
        self.secondary_traits = secondary_traits
        self.response_modes = response_modes


class AICharacterResponseGenerator:
    def __init__(self,model, character_settings, max_response_size):
        self.model = model
        self.character_settings = character_settings
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
        all_response_modes = []
        for response_mode in self.character_settings.response_modes:
            all_response_modes += [response_mode] * int(response_mode.probability)
        return random.choice(all_response_modes)

    def getRandomPromptMessage(self, response_mode):
        prompt_message = "Respond to all following messages as if you were {}. {}. Keep the responses to a maximum of {} characters."
        response_style = None
        if response_mode.name == "Chat":
            response_style = f"Respond in a {random.choice(self.character_settings.primary_traits)} way with a {random.choice(self.character_settings.secondary_traits)} undertone"
        else:
            response_style = response_mode.response_style

        prompt_message = prompt_message.format(self.character_settings.character_name, response_style, self.max_response_size)
        return prompt_message
    
    def printResponseDetails(self, response_mode):
        print("RESPONSE MODE: " + response_mode.name)
        print("CHAT HISTORY:\n " + str(self.chat_history))

    def getResponse(self, user_text, chat_history = None):
        self.resetChatHistory()
        if chat_history != None and len(chat_history) > 0:
            self.chat_history += chat_history[0:-1]

        rand_response_mode = self.getRandomResponseMode()
        rand_prompt_message = self.getRandomPromptMessage(rand_response_mode)
        self.updateResponseMode(rand_prompt_message)
        user_message = {"role": "user", "content": user_text}
        self.chat_history.append(user_message)
        response = openai.ChatCompletion.create(model=self.model,messages=self.chat_history)
        self.printResponseDetails(rand_response_mode)
        return response
    