import openai 
import sys
import os
import re
import readline

from pyfzf import FzfPrompt
from termcolor import cprint


fzf_prompt = FzfPrompt().prompt
ChatCompletion = openai.types.chat.chat_completion.ChatCompletion


def error(msg: str) -> None:
    cprint(msg, 'red')
    sys.exit(1)


def print_error(msg: str) -> None:
    cprint(msg, 'red')


def print_info(msg: str) -> None:
    cprint(msg, 'blue')


def print_warn(msg: str) -> None:
    cprint(msg, 'orange')


def print_msg(msg: str) -> None:
    cprint(msg, 'cyan')


def print_prompt(prompt: str) -> None:
    cprint(prompt, "fuschia", end='')


def print_ok(s: str) -> None:
    cprint(s, 'green')


def create_client(api_key_file: str) -> openai.OpenAI:
    api_key: str | None=None

    cprint(f"Reading API key from {api_key_file}", "green")
    if not os.path.isfile(api_key_file):
        cprint("No API key", "red")
        sys.exit(1)

    with open(api_key_file) as fh:
        api_key = fh.read().strip()

    return openai.OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

def create_response(
    client: openai.OpenAI,
    question: str,
    stream: bool=True,
    max_tokens: int | None=None,
    reasoner: bool=False,
) -> openai.OpenAI | ChatCompletion:
    reasoner = "deepseek-chat" if not reasoner else "deepseek-reasoner"
    max_tokens = 500 if not max_tokens else max_tokens
    return client.chat.completions.create(
        model=reasoner,
        messages=[
            {"role": "system", "content": "Try to use emacs org-mode format if possible otherwise, use markdown format"},
            {"role": "user", "content": question}
        ],
        stream=stream,
        max_tokens=max_tokens
    )

def read_input(prompt: str | None, client=None) -> str | None:
    if not prompt:
        prompt = '% '
    else:
        prompt = prompt + ' % '

    user = None

    try:
        print_prompt(prompt)
        user = input().strip()
    except KeyboardInterrupt:
        print()
        user = ''
    except EOFError:
        print()
        if client: client.close()
        sys.exit(1)

    if len(user) == 0:
        return
    else:
        return user

def menu_select(choices: list[str], client=None) -> list[str]:
    help_ = '''`/{pattern}`
    Narrow down choices with regex

`<int>, [int..]`
    Select by index

`q`
    Go back in history. When there is no history, return None'''

    def print_choices(choices: list[str]) -> None:
        for i, q in enumerate(choices):
            print(f"{i+1:<4}∣ {q}")

    def grep_choices(choices: list[str], pattern: str) -> list[str]:
        return [
            choice for choice in choices 
            if re.search(pattern, choice, re.I)
        ]

    def select_choice(choices: list[str], indices: str | list[str]) -> list[str]:
        found = []
        for index in indices:
            try:
                index = int(re.sub(r'\s+', '', index))
                index = index - 1
                found.append(choices[index])
            except IndexError:
                print_error(f"Invalid index: {index-1}")

        return found

    def parse_choice(choices: list[str], history: list[list[str]]) -> list[str]:
        press_enter = lambda: input("<Press enter to continue>")
        press_enter_help = lambda: input("<Press enter to continue (Type in `help` or `h` to show help)>")

        print_choices(choices)
        s = read_input("Select", client=client)

        if not s:
            print_warn("No input provided")
            press_enter()
            return parse_choice(choices, history)
        elif s[0] == '/':
            pattern = s[1:].lstrip()
            if len(pattern) == 0:
                print_warn("No regex pattern provided")
                return parse_choice(choices, history)

            found = grep_choices(choices, pattern)
            if len(pattern) == 0:
                print_warn("Query failed")
                return parse_choice(choices, history)
            else:
                history.append(choices)
                return parse_choice(found, history)
        elif s[0] == 'q':
            if len(history) == 1:
                return
            else:
                return parse_choice(history.pop(), history)
        elif re.search(r'[0-9]+', s):
            s = re.split(r'\s*,\s*', s)
            s = [x.strip() for x in s]
            found = select_choice(choices, s)

            if len(found) == 0:
                print_warn("Nothing selected")
                press_enter()
            else:
                return found
        elif re.search(r'help', s):
            print_ok(help_)
            press_enter()
            return parse_choice(choices, history)
        else:
            print_warn("Invalid input. Type in `help` to show help")
            press_enter()
            return parse_choice(choices, history)

    return parse_choice(choices, [choices])


def fzf_select(choices: list[str]) -> list[str]:
    return fzf_prompt(choices, "--multi --cycle")


def parse_int(s: str) -> tuple[int | None, str | None]:
    if re.search(r'^[0-9]+$', s):
        return (int(s), None)
    else:
        return (None, f'Expected an integer, got {s}')


