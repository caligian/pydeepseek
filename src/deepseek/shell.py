import re
import readline

from typing import Callable
from termcolor import cprint
from .utils import *
from .client import Client 
from .config import Config
# from src.deepseek.utils import *
# from src.deepseek.client import Client
# from src.deepseek.config import Config

VARIABLES = {
    'stream': (['on', 'off'], 'on'),
    'max_tokens': (parse_int, 1000)
}

TR = {
    'on': True, 'off': False
}

COMMANDS = {
    'h': 0, 'help': 0,
    'q': 0, 'quit': 0,
    'gget': 1, 'get': 1,
    '?': "?", '??': "?", '???': '?',
    '#': "?", '##': "?", '###': '?', 
    'history': "?", 'fzf_history': "?", "menu_history": "?",
    'json_history': "?", 'fzf_json_history': "?", "menu_json_history": "?"
}

ALIAS = {
    'h': 'help',
    'q': 'quit',
    '?': 'history',
    '??': 'fzf_history',
    '???': 'menu_history',
    '#': 'json_history',
    '##': 'fzf_json_history',
    '###': 'menu_json_history',
}

HELP = '''`/{query}`
    Process query

`!/{query}`
    Process query with deep reasoner

`!@{query}`
    Same as above but also copy query results

`!@/{query}`
    Process query with deep reasoner and copy results

{command} [arguments, ...]
    Where {command} can be any of
    `quit`                 | `q`
        Close session and exit

    `help`                 | `h`
        Show this help

    `history`              | `?`   [pattern]
        Pretty print history

    'fzf_history'          | `??`  [pattern]
        Fzf select questions and print matched response  

    'menu_history'         | `###` [pattern]
        Menu select questions and print matched response  

    `json_history`         | `#`   [pattern]
        Print history in json format

    'fzf_json_history'     | `##`  [pattern]
        Fzf select questions and print matched response  

    'menu_json_history'    | `###` [pattern]
        Menu select questions and print matched response  

    `gset {variable} {value}`
        Set global variable where {variable} can be any of:
        `stream`
            Set streaming output for all queries
        `max_tokens`
            Default: 1000. Maximum tokens for all queries

    `set {variable} {value}` 
        Set variable for next query where {variable} can be any of:
        `stream`
            Set streaming output for next query
        `max_tokens`
            Maximum tokens for next query

'''

def parse_ask(s: str) -> dict[str, str | bool | None] | None:
    if s[0] == '/' or s[:2] == '!/' or s[:3] == '!@/' or s[:2] == '@/':
        reasoner = False
        clipboard = False

        if s[:2] == '!/' or s[:3] == '!@/':
            reasoner = True
            if s[:2] == '!/':
                s = s[2:]
            else:
                clipboard = True
                s = s[3:]
        elif s[:2] == '@/':
            clipboard = True
            s = s[2:]
        elif s[0] == '/':
            s = s[1:]

        s = s.strip()

        res = {
            'type': 'function', 
            'function': 'ask',
            'kwargs': {"reasoner": reasoner, "clipboard": clipboard},
            'args': [],
            'ok': False,
            'msg': None
        }

        if len(s) == 0:
            res['msg'] = 'Expected form: `/<question>`'
        else:
            res['args'] = [s]
            res['ok'] = True

        return res


def parse_set_var(s: str) -> dict[str, str | bool | None] | None:

    s = s.lstrip()

    if s[:3] != 'set' and s[:4] != 'gset':
        return

    res = {
        'type': 'variable', 'variable': None,
        'ok': False, 'msg': None,
        'value': None,
    }
    valid_vars = VARIABLES
    value_tr = TR
    gset = s[:4] == 'gset'
    s = s[3:] if s[:3] == 'set' else s[4:]
    s = re.split(r"\s+", s, maxsplit=2)
    s = [x for x in s if len(x) > 0]

    if len(s) == 0:
        res['msg'] = "Expected form: `set <variable> [value]`"
        return res

    var = s[0]
    value: str | None=None
    res['variable'] = var

    if gset:
        res['type'] = 'global_variable'

    if not valid_vars.get(var):
        res['msg'] = f"Invalid variable. Expected any of: {(', ').join(list(valid_vars.keys()))}"
        return res

    if len(s) > 1:
        value = s[1].strip()
        required, _ = valid_vars[var]

        if type(required) == list:
            if value not in required:
                res['msg'] = f'Invalid value: {value}. Expected any of: {(', ').join(required)}'
                return res
        elif type(required) == str:
            if not re.search(required, value, re.I):
                res['msg'] = f'Could not match pattern `{required}`'
                return res
        elif isinstance(required, Callable):
            value, msg = required(value)
            if not value:
                res['msg'] = f'{required}({value}) did not return True' if not msg else msg
                return res

        res['ok'] = True
        if value_tr.get(value) != None:
            res['value'] = value_tr[value]
        else:
            res['value'] = value

    return res


def parse_command(s: str) -> dict[str, str | bool | None]:
    res = {
        'type': 'command', 'command': None,
        'ok': False, 'msg': None,
        'args': None,
    }

    if\
            len(s) == 0 or\
            s[:3] == 'set' or\
            s[:4] == 'gset' or\
            s[0] == '/' or\
            s[:2] == '!/' or\
            s[:3] == '!@/' or\
            s[:2] == '@/':
        res['msg'] = "Not a command"
        return res

    s = re.split(r'\s+', s, maxsplit=2)
    s = [x for x in s if len(x) > 0]

    if len(s) == 0:
        res['msg'] = 'No command passed'
        return res

    if a := alias.get(s[0]):
        res['command'] = a
    else:
        res['command'] = s[0]

    valid_commands = COMMANDS
    if valid_commands.get(res['command']) == None:
        res['msg'] = f'Expected any of {(", ").join(list(valid_commands.keys()))}'
        return res

    if len(s) > 1:
        res['args'] = s[1]

    nargs = valid_commands[res['command']]
    if type(nargs) == int:
        args = [res['args']] if type(res['args']) == str else res['args']
        if\
                (nargs != 0 and not args) or\
                (args and len(args) != nargs):
            if not args:
                res['msg'] = f'Expected {nargs} argument(s), got nothing'
            else:
                res['msg'] = f'Expected {nargs} argument(s), got {len(res["args"])}'
            return res

    res['ok'] = True
    return res


def parse(s: str) -> dict[str, str | bool | None]:
    if len(s) == 0:
        return { 'ok': False, 'msg': "No input given" }

    res = parse_ask(s)
    if not res:
        res = parse_set_var(s)

    if not res:
        res = parse_command(s)

    if not res.get('type'):
        return {
            'ok': False,
            'msg': "Invalid input. Type in `h` or `help` for help"
        }
    else:
        return res

def shell(client: Client) -> None:
    variables = {}

    def get_value(var: str) -> bool | str | None:
        value = None

        if variables.get(var) == None:
            value = VARIABLES[var][1]
        else:
            value = variables[var]
            variables[var] = None

        if TR.get(value):
            return TR[value]
        else:
            return value

    def make_kwargs(kwargs: dict) -> None:
        for k in VARIABLES.keys():
            if kwargs.get(k) == None:
                kwargs[k] = get_value(k)

    print("Type in `help` to display help. Ctrl-D will close the session")
    print()

    while True:
        cprint("deepseek % ", "cyan", end='')
        inp = None
        
        try:
            inp = input('')
        except KeyboardInterrupt:
            print()
            continue
        except EOFError:
            print()
            client.close()
            sys.exit(1)

        inp = inp.strip()
        inp = None if len(inp) == 0 else inp

        if not inp:
            continue

        cmd = parse(inp)

        if not cmd['ok']:
            cprint(cmd['msg'], 'red')
            continue

        match cmd['type']:
            case 'function':
                if cmd['function'] == 'ask':
                    kwargs = cmd['kwargs'].copy()
                    print('gotten:', kwargs)
                    make_kwargs(kwargs)
                    kwargs['stdout_only'] = False
                    kwargs['stdout'] = True
                    print(kwargs)
                    client.ask(*cmd['args'], **kwargs)
            case 'global_variable':
                validator, value = VARIABLES[cmd['variable']]
                VARIABLES[cmd['variable']] = (validator, cmd['value'])
            case 'variable':
                variables[cmd['variable']] = cmd['value']
            case 'command':
                match cmd['command']:
                    case 'quit':
                        client.close()
                        return
                    case 'help':
                        print(HELP)
                    case 'get':
                        value = variables.get(cmd['args'])
                        if value != None: print(value)
                    case 'gget':
                        value = global_variables.get(cmd['args'])
                        if value != None: print(value)
                    case 'json_history':
                        client.history.print(
                            pattern=cmd['args'],
                            json=True
                        )
                    case 'fzf_json_history':
                        client.history.print(
                            pattern=cmd['args'],
                            fzf=True,
                            json=True
                        )
                    case 'menu_json_history':
                        client.history.print(
                            pattern=cmd['args'],
                            menu=True,
                            json=True
                        )
                    case 'history':
                        client.history.print(pattern=cmd['args'])
                    case 'fzf_history':
                        client.history.print(pattern=cmd['args'], fzf=True)
                    case 'menu_history':
                        client.history.print(pattern=cmd['args'], menu=True)

config = Config()
client = Client(config)
shell(client)
