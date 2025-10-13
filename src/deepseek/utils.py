import openai 
import sys
import os
import re

from prompt_toolkit import prompt as get_input, PromptSession
from prompt_toolkit.history import FileHistory
from typing import Callable
from collections import namedtuple
from pyfzf import FzfPrompt
from termcolor import cprint
from pyperclip import copy



fzf_prompt = FzfPrompt().prompt
ChatCompletion = openai.types.chat.chat_completion.ChatCompletion
PROMPT_SESSION = PromptSession()
PROMPT_HISTORY = FileHistory(
    os.path.join(os.getenv("HOME"), ".deepseek", 'prompt-history.txt')
)
Value = str | int | bool | None
ValueDict = dict[str, Value]
ValueList = list[Value]
Tokens = list[str]


def error(msg: str) -> None:
    cprint(msg, 'red')
    sys.exit(1)


def print_error(msg: str) -> None:
    cprint(msg, 'red')


def print_exception(e: Exception) -> None:
    print_error(e.args[0])


def print_info(msg: str) -> None:
    cprint(msg, 'blue')


def print_warn(msg: str) -> None:
    cprint(msg, 'yellow')


def print_msg(msg: str) -> None:
    cprint(msg, 'cyan')


def print_prompt(prompt: str) -> None:
    cprint(prompt, "green", end='')


def print_ok(s: str) -> None:
    cprint(s, 'green')


def fzf_select(choices: list[str]) -> list[str]:
    return fzf_prompt(choices, "--multi --cycle")


def unlist(x: list) -> any:
    if type(x) == list:
        return x[0]
    else:
        return x


def tolist(x: any, force: bool=False) -> list:
    if force:
        return [x]
    elif type(x) != list:
        return [x]
    else:
        return x


def write_clip(s: str) -> str:
    copy(s)
    return s


def get_flag_pos(args: list[str]) -> list[tuple[int, str]]:
    res = []

    for i, a in enumerate(args):
        if len(a) > 0 and a[0] == '-':
            res.append((i, a[1:]))

    return sorted(res, key=lambda x: x[0])


def format_metavar(nargs: str | int, metavar: str | None=None) -> str:
    if type(nargs) == int:
        if metavar:
            res = ['{' + metavar + '}' for _ in range(nargs)]
            res = (" ").join(res) if len(res) > 0 else ""
            return res
        else:
            res = ['{arg' + str(i) + '}' for i in range(nargs)]
            if len(res) == 0:
                return ""
            else:
                return (' ').join(res)
    elif nargs == '+':
        if metavar:
            return '{' + metavar + '}, ...' 
        else:
            return '{arg1} {arg2}, ...'
    elif nargs == '*':
        if metavar:
            return '[' + metavar + '], ...' 
        else:
            return '[arg1] [arg2], ...'
    elif nargs == '?':
        if metavar:
            return '[' + metavar + ']' 
        else:
            return '[arg]'


def split(s: str, pattern: str=r' +', maxsplit: int | None=None) -> None | list[str]:
    words: list[str] 

    if maxsplit:
        words = re.split(pattern, s, maxsplit=maxsplit) 
    else:
        words = re.split(pattern, s)

    words = [x.strip() for x in words if len(x) > 0]

    if len(words) == 0:
        return
    else:
        return words
