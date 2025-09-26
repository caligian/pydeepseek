import datetime
import os
import json as JSON

from termcolor import cprint
from pyfzf import FzfPrompt
from typing import Iterable
from typing import Self
from .utils import *

fzf_prompt = FzfPrompt().prompt

class History:
    def __init__(self, history_dir: str, write_on_append: bool=True, client=None) -> None:
        self.client = client

        cprint(f"Setting history directory: {history_dir}", "cyan")
        self.dir = history_dir

        if not os.path.isdir(os.path.dirname(self.dir)):
            cprint("Creating history directory", "cyan")
            os.makedirs(self.dir)

        today = datetime.date.today()
        self.file = os.path.join(
            self.dir,
            f"{today.day}-{today.month}-{today.year}.json"
        )
        cprint(f"Using history file: {self.file}", "cyan")

        self.write_on_append = write_on_append
        self.history = {}
        self.read()

    def __getitem__(self, key: str) -> str | None:
        return self.history.get(key)

    def __setitem__(self, key: str, value: str) -> None:
        self.history[key] = value

    def items(self) -> list[tuple[str, str]]:
        return [(k, v) for k, v in self.history.items()]

    def keys(self) -> list[str]:
        return [k for k in self.history.keys()]

    def values(self) -> list[str]:
        return [k for k in self.history.values()]

    def select(
        self,
        pattern: str | None=None,
        menu: bool=False,
        fzf: bool=True,
        json: bool=False,
    ) -> list[str] | None:
        questions = list(self.history.items())
        found = questions

        if pattern:
            found = [
                x for x in questions
                if re.search(pattern, x[0], re.I)
            ]

        if len(found) == 0:
            return

        if menu:
            if found := menu_select([x[0] for x in found], client=self.client):
                found = [(x, self.history[x]) for x in found]
            else:
                found = None
        elif fzf:
            if found := fzf_select([x[0] for x in found]):
                found = [(x, self.history[x]) for x in found]
            else:
                found = None

        if not found or len(found) == 0:
            return
        elif json:
            return JSON.dumps(found)
        else:
            return found

    def print(
        self,
        all: bool=True,
        pattern: str | None=None,
        menu: bool=False,
        fzf: bool=False,
        json: bool=False,
    ) -> None:
        cols = os.get_terminal_size().columns
        print_sep = lambda: print("_" * (cols - 1))

        def print_response(q: str, resp: str) -> None:
            print_sep()
            print(f'Query: {q}')
            print_sep()
            print(f"Response: {resp}")
            print()

        if pattern or menu or fzf:
            all = False

        if all:
            if json:
                print(JSON.dumps(self.history)) 
            else:
                for q, r in self.history.items():
                    print_response(q, r)
        elif found := self.select(
            pattern=pattern,
            menu=menu,
            fzf=fzf,
            json=json
        ):
            if json:
                print(found)
            else:
                for q, r in found:
                    print_response(q, r)

    def read(self) -> None:
        if os.path.isfile(self.file):
            with open(self.file) as fh:
                s = fh.read()
                if not '{' in s:
                    self.history = {}
                else:
                    self.history = JSON.loads(s)

    def append(self, question: str, response: str) -> None:
        self.history[question] = response
        if self.write_on_append: self.write()

    def write(self) -> None:
        with open(self.file, 'w') as fh:
            fh.write(JSON.dumps(self.history))
