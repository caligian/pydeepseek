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
Result: tuple[bool, str | None, any] = namedtuple(
    "Result",
    ('ok', 'msg', 'value'),
    defaults=(True, None, None)
)
Validator =\
    str |\
    re.Pattern |\
    list[str] |\
    dict[str, any] |\
    Callable[[str], any]
Value = str | int | bool | None
ValueDict = dict[str, Value]
ValueList = list[Value]
Tokens = list[str]


def Context(**kwargs) -> dict[str, any]:
    return kwargs


def error(msg: str) -> None:
    cprint(msg, 'red')
    sys.exit(1)


def print_error(msg: str) -> None:
    cprint(msg, 'red')


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


def create_client(api_key_file: str) -> openai.OpenAI:
    api_key: str | None=None

    print_info(f"Reading API key from {api_key_file}")
    if not os.path.isfile(api_key_file):
        print_error("No API key provided")
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
) -> openai.OpenAI | ChatCompletion | None:
    reasoner = "deepseek-chat" if not reasoner else "deepseek-reasoner"
    max_tokens = 1500 if not max_tokens else max_tokens
    try:
        return client.chat.completions.create(
            model=reasoner,
            messages=[
                {"role": "system", "content": "Use markdown format. For tables use a csv format. Do not use any text formatting such as boldface, italics, etc"},
                {"role": "user", "content": question}
            ],
            stream=stream,
            max_tokens=max_tokens
        )
    except KeyboardInterrupt: 
        return
    except EOFError:
        return


def fzf_select(choices: list[str]) -> list[str]:
    return fzf_prompt(choices, "--multi --cycle")


def parse_int(s: str | list[str]) -> tuple[int | None, str | None]:
    s = s[0] if type(s) == list else s
    if re.search(r'^[0-9]+$', s):
        return Result(True, None, int(s))
    else:
        return Result(None, f'Expected an integer, got {s}', s)

def parse_int_in_range(start: int, end: int) -> Callable[[int], Result]:
    assert start >= 0
    assert end > 0

    def parse(x: str) -> Result:
        x = x[0] if type(x) == list else x
        x: Result = parse_int(x)

        if not x.ok:
            return x

        x = x.value
        if x < start or x >= end:
            return Result(False, f'Expected input to be in range {start}-{end}', dict(input=x))
        else:
            return x

    return parse


def parse_bool(s: str | list[str] | None=None) -> bool:
    s = s[0] if type(s) == list else s
    if not s:
        return Result(True, None, False)
    elif s == 'on' or s == 'True' or s == 'true' or s == '1':
        return Result(True, None, True)
    else:
        return Result(True, None, False)


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


def make_msg(msg: str, prefix: str='') -> str:  
    if prefix == '':
        return msg
    else:
        return f'{prefix}: {msg}'
 


def validate(
    value: str | list[str],
    validator: Validator,
    prefix: str=''
) -> Result:
    t_validator = type(validator)
    value = tolist(value)

    if validator == None:
        return Result(True, None, value)
    elif t_validator == str:
        if not re.search(validator, value[0], re.I):
            return Result(
                False, 
                make_msg(f'Could not match pattern `{validator}` with `{value}`', prefix),
                Context(value=value[0])
            )
        else:
            return Result(True, None, value[0])
    elif t_validator == list:
        if value[0] not in validator:
            return Result(
                False,
                make_msg(f'Value `{value[0]}` is not in `{validator}`', prefix),
                Context(value=value[0])
            )
        else:
            return Result(True, None, value)
    elif t_validator == dict:
        if value[0] not in validator:
            return Result(
                False,
                make_msg(f'Value `{value[0]}` is not in `{validator}`', prefix),
                Context(value=value[0])
            )
        else:
            return Result(True, None, validator[value[0]])
    else:
        res = validator(value)
        ok, msg, value = res

        if ok:
            return Result(True, None, value)
        else:
            return Result(False, msg, Context(value=value))


def validate_args(args: list[str], validator: Validator, prefix: str='') -> Result:
    for i in range(len(args)):
        a = args[i]
        res = validate(a, validator, prefix)

        if not res.ok:
            return Result(
                False,
                make_msg(res.msg, prefix + f'[{i}]'),
                Context(value=args, index=i, context=res.value)
            )
        else:
            args[i] = res.value

    return Result(True, None, args)


def check_nargs(args: list[str], nargs: int | str, prefix: str='') -> Result:
    is_num = type(nargs) == int
    l = len(args)

    if not is_num and nargs != '*' and nargs != '+' and nargs != '?':
        raise Exception(
            make_msg(f"Expected nargs to be a natural number or any of '+', '*', '?'", prefix)
        )
    elif nargs == '+':
        if l < 1:
            return Result(
                False,
                make_msg(f'Expected at least one argument, got {l}', prefix),
                Context(value=args, nargs=nargs)
            )
        else:
            return Result(True, None, args)
    elif nargs == '?':
        if l > 1:
            return Result(
                False,
                make_msg(f'Expected at most one argument, got {l}', prefix),
                Context(value=args, nargs=nargs)
            )
        else:
            return Result(True, None, args)
    elif is_num:
        if l != nargs:
            return Result(
                False,
                make_msg(f'Expected {nargs} arguments, got {l}', prefix),
                Context(value=args, nargs=nargs)
            )
        else:
            return Result(True, None, args)
    else:
        return Result(True, None, args)


def slice_args(args: list[str], nargs: str | int) -> Result:
    res = check_nargs(args, nargs)
    if not res.ok:
        return res

    if type(nargs) == int:
        return Result(True, None, args[:nargs])
    elif nargs == '+':
        return Result(True, None, args)
    elif nargs == '?':
        if len(args) > 0: return Result(True, None, args[0])
        return Result(True, None, args)
    else:
        return Result(True, None, args)


def write_clip(s: str) -> str:
    copy(s)
    return s


def get_flag_pos(args: list[str]) -> list[tuple[int, str]]:
    res = []

    for i, a in enumerate(args):
        if len(a) > 0 and a[0] == '-':
            res.append((i, a[1:]))

    return sorted(res, key=lambda x: x[0])


def check_flag_nargs(
    flag: str,
    nargs: str | int,
    args: list[str],
    command: str=''
) -> Result:
    res = check_nargs(args, nargs, command)
    if not res.ok:
        return res
    else:
        return Result(True, None, args)


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
