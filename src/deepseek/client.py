from openai import OpenAI
from termcolor import cprint
from pyperclip import copy as write_clip

import sys
import os

from .config import Config
from .utils import *
from .stream import Stream
from .history import History

class Client:
    def __init__(self, config: Config) -> None:
        self.client = create_client(config.api_key_file)
        self.config = config

    def ask(
        self,
        question: str,
        stdout: bool=False,
        stdout_only: bool=False,
        stream: bool=True,
        reasoner: bool=False,
        max_tokens: int | None=None,
        clipboard: bool=False
    ) -> str | None:
        stream = create_response(
            self.client,
            question,
            stream=stream,
            max_tokens=max_tokens,
            reasoner=reasoner
        )

        if not stream:
            return

        stream = Stream(stream)
        out = None

        if stdout_only:
            stream.print()
        elif stdout:
            out = stream.print(capture=True)
        else:
            out = stream.read()

        if clipboard:
            write_clip(out)

        if not stdout_only:
            self.history.append(question, out)

        return out

    def close(self) -> None:
        if not self.client.is_closed():
            self.client.close()
