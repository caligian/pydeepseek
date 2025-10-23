import openai 
from termcolor import cprint

ChatCompletion = openai.types.chat.chat_completion.ChatCompletion

class Stream:
    def __init__(self, response: openai.Stream | ChatCompletion) -> None:
        self.response = response
        self.text: str | None = None
        self.sync = type(self.response) is ChatCompletion 

        if self.sync:
            self.text = self.response.choices
            if len(self.text) > 0:
                self.text = self.text[0].message.content

    def stream(self) -> str | None:
        if self.sync:
            return self.text

        if not self.response:
            return

        try:
            for event in self.response:
                if event.choices:
                    content = event.choices[0].delta.content
                    if content != "<think>" and content != "</think>":
                        yield content
        except Exception:
            yield

    def read(self, stdout: bool=False) -> str | None:
        if self.text:
            print(self.text)
            return self.text

        words = []

        try:
            for word in self.stream():
                if word is None:
                    break

                if stdout: 
                    cprint(word, 'green', end='')

                words.append(word)

            if stdout: 
                print()
        except (KeyboardInterrupt, EOFError):
            if words:
                self.text = ("").join(words)
                return ("").join(words)
            else:
                return

        self.text = ("").join(words)
        return self.text

    def print(self) -> str | None:
        return self.read(stdout=True)
