import datetime
import os
import json as JSON

from glob import glob
from termcolor import cprint
from pyfzf import FzfPrompt
from typing import Iterable
from typing import Self
from .utils import *

fzf_prompt = FzfPrompt().prompt

class History:
    def __init__(
        self,
        history_dir: str,
        write_on_append: bool=True,
        client=None
    ) -> None:
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

    def write_clip(
        self,
        query: str | list[str] | None=None,
        response: str | list[str] | None=None,
        json: bool=False,
    ) -> bool | None:
        query = tolist(query)
        response = tolist(response)
        create_dict = lambda q, r: dict(query=q, response=r)

        if query and response:
            assert len(query) == len(response)
        
        if json:
            if query and response:
                res = [
                    create_dict(q, response[i])
                    for i, q in enumerate(query)
                ]
                write_clip(JSON.dumps(res))
            elif query:
                write_clip(JSON.dumps([
                    create_dict(q, None) for q in tolist(query)
                ]))
            elif response:
                write_clip(JSON.dumps([
                    create_dict(None, r) for r in tolist(response)
                ]))
        elif query and response:
            for i, q in enumerate(query):
                r = response[i]
                write_clip(f'Query> {q}\nResponse> {r}\n\n')
        elif query:
            res = []
            for q in query:
                res.append(f"Query> {q}")
                res.append('')
            write_clip(("\n").join(res))
        elif response:
            res = []
            for r in response:
                res.append(f"Response> {q}")
                res.append('')
            write_clip(("\n").join(res))

        return True

    def select(
        self,
        pattern: str | None=None,
        fzf: bool=False,
        json: bool=False,
        clipboard: bool=False,
        response_only: bool=False,
        query_only: bool=False
    ) -> list[str] | list[dict[str, str]] | str | None:
        create_dict = lambda q, r: dict(query=q, response=r)
        make_found = lambda found: [
            dict(query=x, response=self.history[x])
            for x in found
        ]
        questions = list(self.history.items())
        found = questions

        if pattern:
            if response_only:
                found = [
                    x for x in self.history.values()
                    if re.search(pattern, x, re.I)
                ]
            else:
                found = [
                    x for x in self.history.keys()
                    if re.search(pattern, x, re.I)
                ]

        if len(found) == 0:
            return

        if fzf:
            if res := fzf_select([x.replace("\n", '$$$') for x in found]):
                found = res
                found = [x.replace("$$$", "\n") for x in found]
            else:
                found = None
        if not found or len(found) == 0:
            return

        def queries():
            return list(
                map(lambda x: x[0] if type(x) == list else x, found)
            )

        def responses():
            if response_only:
                return list(
                    map(lambda x: x[1] if type(x) == list else x, found)
                )
            else:
                return list(map(
                    lambda x: self.history[x[1]] if type(x) == list else self.history[x], 
                    found
                ))

        queries_check_json = lambda:\
            JSON.dumps(queries()) if json else queries()
        responses_check_json = lambda:\
            JSON.dumps(responses()) if json else responses()

        if clipboard:
            if query_only:
                qs = queries()
                if self.write_clip(query=qs, json=json): return qs
            elif response_only:
                rs = responses()
                if self.write_clip(response=rs, json=json): return rs
            else:
                if self.write_clip(
                    query=queries(),
                    response=responses(),
                    json=json
                ):
                    qs = queries()
                    rs = responses()
                    res = [
                        create_dict(qs[i], rs[i]) for i in range(len(qs))
                    ]
                    return res
        elif not query_only and not response_only:
            found = [create_dict(q, self.history[q]) for q in found]
            if json:
                return JSON.dumps(found)
            else:
                return found
        elif query_only:
            return queries_check_json()
        elif response_only:
            return responses_check_json()

    def print(
        self,
        pattern: str | None=None,
        fzf: bool=False,
        json: bool=False,
        clipboard: bool=False,
        query_only: bool=False,
        response_only: bool=False
    ) -> None:
        def print_response(q: str, r: str) -> None:
            cprint(f'Query> {q}', 'red')
            cprint(f"Response> {r}", 'white')

        found = self.select(
            pattern=pattern,
            fzf=fzf,
            json=json,
            clipboard=clipboard,
            query_only=query_only,
            response_only=response_only
        )

        if not found or len(found) == 0:
            return
        elif json:
            print(found)
        elif type(found[0]) == str:
            prefix = 'Query> ' if query_only else 'Response> '
            for f in found:
                cprint(prefix, 'yellow', end='')
                cprint(f, 'red')
                print()
        else:
            for res in found:
                print_response(res['query'], res['response'])
                print()

    def read(self) -> None:
        print_msg(f'Loading all history files from {self.dir}')
        files = glob(f'{self.dir}/*.json')

        for file in files:
            with open(file) as fh:
                s = fh.read()
                for q, r in JSON.loads(s).items(): 
                    if r: self.history[q] = r

    def append(self, question: str, response: str) -> None:
        self.history[question] = response
        if self.write_on_append: self.write()

    def write(self) -> None:
        with open(self.file, 'w') as fh:
            fh.write(JSON.dumps(self.history))
