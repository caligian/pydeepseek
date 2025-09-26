import openai 
import sys

ChatCompletion = openai.types.chat.chat_completion.ChatCompletion

class Stream:
    def __init__(self, response: openai.Stream | ChatCompletion) -> None:
        self.response = response
        self.text: str | None = None
        self.sync = type(self.response) == ChatCompletion 

        if self.sync:
            self.text = self.response.choices
            if len(self.text) > 0:
                self.text = self.text[0].message.content

    def stream(self) -> str | None:
        if self.sync:
            return self.text

        for event in self.response:
            if event.choices:
                content = event.choices[0].delta.content
                if content != "<think>" and content != "</think>":
                    yield content

    def read(
        self,
        stdout: bool=False,
        stdout_only: bool=False
    ) -> str | None:
        if stdout_only:
            stdout = True

        if self.text:
            if stdout_only:
                print(self.text)
                return
            elif stdout:
                print(self.text)

            return stdout

        words = [] if not stdout_only else None

        try:
            for word in self.stream():
                if word == None: break
                if stdout: print(word, end='')
                if not stdout_only: words.append(word)
            if stdout or stdout_only: print()
        except KeyboardInterrupt:
            if words:
                self.text = ("").join(words)
                return ("").join(words)
            else:
                return

        if not stdout_only:
            self.text = ("").join(words)
            return self.text

    def print(self, capture: bool=False) -> str | None:
        return self.read(stdout=True, stdout_only=not capture)
