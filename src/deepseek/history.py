import datetime
import os
import json as JSON
import re

from glob import glob
from termcolor import cprint
from .utils import fzf_select, tolist, print_msg
from pyperclip import copy as write_clip


class History:
    def __init__(
        self,
        history_dir: str = os.path.join(os.getenv("HOME"), ".deepseek", "history"),
        write_on_append: bool = True,
        client=None,
    ) -> None:
        self.client = client

        cprint(f"Setting history directory: {history_dir}", "cyan")
        self.dir = history_dir

        if not os.path.isdir(os.path.dirname(self.dir)):
            cprint("Creating history directory", "cyan")
            os.makedirs(self.dir)

        today = datetime.date.today()
        self.file = os.path.join(
            self.dir, f"{today.day}-{today.month}-{today.year}.json"
        )
        cprint(f"Current history file: {self.file}", "cyan")

        self.write_on_append = write_on_append
        self.history = {}
        self.read()

    def __getitem__(self, key: str) -> str | None:
        return self.history.get(key)

    def __setitem__(self, key: str, value: str) -> None:
        self.history[key] = value

    def __len__(self) -> int:
        return len(self.history)

    def items(self) -> list[tuple[str, str]]:
        return [(k, v) for k, v in self.history.items()]

    def keys(self) -> list[str]:
        return [k for k in self.history.keys()]

    def values(self) -> list[str]:
        return [k for k in self.history.values()]

    def select(
        self,
        query_pattern: str = ".+",
        response_pattern: str = ".+",
        fzf: bool = False,
        json: bool = False,
        clipboard: bool = False,
        stdout: bool = False,
    ) -> list[dict[str, str]]:
        def match_questions(
            pattern: str | None,
            search_key: bool = False,
            search_value: bool = False,
            items: list[tuple[str, str]] | None = None,
        ) -> list[tuple[str, str]]:
            pattern = pattern if pattern else '.+'
            items = items if items else self.history.items()

            if search_key:
                return [
                    x
                    for x in items 
                    if re.search(pattern, x[1], re.I)
                ]
            else:
                return [
                    x
                    for x in items
                    if re.search(pattern, x[0], re.I)
                ]

        def result(
            items: list[tuple[str, str]] | list[list[str]],
        ) -> list[dict[str, str]]:
            res = []
            for q, r in items:
                res.append(dict(query=q, response=r))
            return res

        def format_query(q: str, r: str) -> str:
            return ("").join(["Query>", q, "\n", "Response>", r])

        def print_query(q: str, r: str) -> None:
            cprint(f"Query> {q}", "red")
            cprint(f"Response> {r}", "green")

        def format_queries(res: list[dict[str, str]]) -> str:
            res = []
            for response in res:
                res.append(format_query(response["query"], response["response"]))
            return ("\n\n").join(res)

        def print_queries(res: list[dict[str, str]]) -> str:
            for response in res:
                print_query(response["query"], response["response"])

        found = match_questions(query_pattern, search_key=True)
        found = match_questions(response_pattern, search_value=True, items=found)
        queries = [x[0] for x in found]
        res: list[dict[str, str]] = []
        res_json: str = ""

        if len(found) == 0:
            return

        if fzf:
            queries = fzf_select([x.replace("\n", "$$$") for x in queries])
            queries = [x.replace("$$$", "\n") for x in queries]
            res = result([(q, self.history[q]) for q in queries])
        else:
            res = result(found)

        if clipboard and json:
            res_json = JSON.dumps(res)
            write_clip(res_json)
        elif clipboard:
            write_clip(format_queries(res))

        if stdout and json:
            print(res_json)
        elif stdout:
            print_queries(res)

        return res

    def print(
        self,
        query_pattern: str = ".+",
        response_pattern: str = ".+",
        fzf: bool = False,
        json: bool = False,
        clipboard: bool = False,
    ) -> None:
        self.select(
            query_pattern=query_pattern,
            response_pattern=response_pattern,
            fzf=fzf,
            json=json,
            clipboard=clipboard,
            stdout=True,
        )

    def read(self) -> None:
        print_msg(f"Loading all history files from {self.dir}")
        files = glob(f"{self.dir}/*.json")

        for file in files:
            with open(file) as fh:
                s = fh.read()
                for q, r in JSON.loads(s).items():
                    if r:
                        self.history[q] = r

    def append(self, question: str, response: str) -> None:
        self.history[question] = response
        if self.write_on_append:
            self.write()

    def write(self) -> None:
        with open(self.file, "w") as fh:
            fh.write(JSON.dumps(self.history))
