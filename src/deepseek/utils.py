import openai
import sys
import re

from pyfzf import FzfPrompt
from termcolor import cprint as colored_print
from pyperclip import copy


fzf_prompt = FzfPrompt().prompt
ChatCompletion = openai.types.chat.chat_completion.ChatCompletion
Value = str | int | bool | None
ValueDict = dict[str, Value]
ValueList = list[Value]
Tokens = list[str]


def make_msg(s: str, prefix: str = "") -> str:
    if prefix == "":
        return s
    else:
        return f"{prefix}: {s}"


def cprint(msg: str, color: str = "white", indent=0, **kwargs) -> None:
    indent: str = " " * indent
    msg = msg.split("\n")
    msg = [indent + x for x in msg]
    msg = ("\n").join(msg)
    colored_print(msg, color, **kwargs)



def print_error(msg: str | Exception) -> None:
    msg = msg.args[0] if isinstance(msg, Exception) else msg
    cprint(msg, "red")


def print_exception(e: Exception) -> None:
    print_error(e.args[0])


def print_info(msg: str) -> None:
    cprint(msg, "blue")


def print_warn(msg: str) -> None:
    cprint(msg, "yellow")


def print_msg(msg: str) -> None:
    cprint(msg, "cyan")


def print_prompt(prompt: str) -> None:
    cprint(prompt, "green", end="")


def print_ok(s: str) -> None:
    cprint(s, "green")


def fzf_select(choices: list[str]) -> list[str]:
    return fzf_prompt(choices, "--multi --cycle")


def unlist(x: list) -> any:
    if type(x) is list:
        return x[0]
    else:
        return x


def tolist(x: any, force: bool = False) -> list:
    if force:
        return [x]
    elif type(x) is not list:
        return [x]
    else:
        return x


def write_clip(s: str) -> str:
    copy(s)
    return s


def format_metavar(nargs: str | int, metavar: str | None = None) -> str:
    if type(nargs) is int:
        if metavar:
            res = ["{" + metavar + "}" for _ in range(nargs)]
            res = (" ").join(res) if len(res) > 0 else ""
            return res
        else:
            res = ["{arg" + str(i) + "}" for i in range(nargs)]
            if len(res) == 0:
                return ""
            else:
                return (" ").join(res)
    elif nargs == "+":
        if metavar:
            return "{" + metavar + "}, ..."
        else:
            return "{arg1} {arg2}, ..."
    elif nargs == "*":
        if metavar:
            return "[" + metavar + "], ..."
        else:
            return "[arg1] [arg2], ..."
    elif nargs == "?":
        if metavar:
            return "[" + metavar + "]"
        else:
            return "[arg]"


def split(
    s: str, pattern: str = r" +", maxsplit: int | None = None
) -> None | list[str]:
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


def split2(s: str, pattern: str = r" +") -> None | list[str]:
    return split(s, pattern, 2)
