import re

from copy import copy
from typing import Callable
from collections import namedtuple
from termcolor import cprint

Result = namedtuple("Result", ("ok", 'msg', 'value'))
Value = str | int | bool | None
ValueDict = dict[str, Value]
ValueList = list[Value]
Tokens = list[str]
Validator = \
    list[str] |\
    str |\
    re.Pattern |\
    Callable[[str], Result] |\
    dict[str, Value]


def unlist(x: list[str]) -> str:
    if type(x) != list:
        return x
    elif len(x) == 0:
        return True
    else:
        return x[0]


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


def validate(
    args: str | list[str],
    validator: Validator,
    prefix: str=''
) -> Result:
    if type(args) == list and len(args) == 1:
        args = args[0]

    t_validator = type(validator)
    t_args = type(args)

    def make_msg(msg: str) -> str:
        if prefix == '':
            return msg
        else:
            return f'{prefix}: {msg}'

    def not_str() -> Result:
        return Result(False, make_msg(f"Expected string, got `{args}`"), args)

    if t_validator == str:
        if t_args != str:
            return not_str()
        elif not re.search(validator, args, re.I):
            return Result(
                False,
                make_msg(f"Could not match `{validator}` with `{args}`"),
                args
            )
        else:
            return Result(True, None, args)
    elif t_validator == list:
        if t_args != str:
            return not_str()
        elif args not in validator:
            values = (', ').join(validator)
            values = f'`{values}`'
            msg = make_msg(f"Expected value(s): {values}, got `{args}`")
            return Result(False, msg, None)
        else:
            return Result(True, None, args)
    elif t_validator == dict:
        if t_args != str:
            return not_str()
        elif value := validator.get(args):
            return Result(True, None, value)
        else:
            values = (', ').join(list(validator.keys()))
            values = f'`{values}`'
            msg = make_msg(f"Expected value(s): {values}, got `{args}`")
            return Result(False, msg, args)
    elif isinstance(validator, Callable):
        ok, msg, value = validator(args)
        if not ok:
            return Result(False, make_msg(f"Assertion error: {msg}"), args)
        else:
            return Result(True, None, value)
    else:
        return Result(True, None, args)

                
def check_nargs(
    tokens: int | bool | str | list[str],
    nargs: int | str,
    prefix: str=''
) -> list[str] | None:
    tokens = [tokens] if type(tokens) == str else tokens
    l = len(tokens)
    no_args = l == 0

    def make_msg(msg: str) -> str:
        if prefix == '':
            return msg
        else:
            return f'{prefix}: {msg}'

    match nargs:
        case '+':
            if no_args:
                return Result(False, make_msg("No arguments passed"), tokens)
            else:
                return Result(True, None, tokens)
        case '?':
            if l > 1:
                return Result(False, make_msg(f"Expected 0 or 1 argument, got {l}"), tokens)
            else:
                return Result(True, None, tokens)
        case _ if type(nargs) == int:
            if l != nargs:
                return Result(False, make_msg(f"Expected {nargs} arguments, got {l}"), tokens)
            else:
                return Result(True, None, tokens)

    return Result(True, None, tokens)


class Flag:
    def __init__(
        self,
        command: str,
        flag: str,
        nargs: str | int=0,
        validator: Validator=None,
        default: Value | None=None,
        aliases: list[str] | None=None,
        metavar: str | None=None,
        help: str | None=None,
    ) -> None:
        self.metavar = metavar
        self.aliases = aliases
        self.help = help
        self.command = command
        self.name = flag
        self.nargs = nargs
        self.validator = validator
        self.value: Value = None
        self.default = default

    def reset(self) -> None:
        self.value = None

    def check(self, value: str, prefix: str='') -> Result:
        if self.validator:
            return validate(value, self.validator, prefix)
        else:
            return Result(True, None, value)

    def make_msg(self, msg: str, prefix: str='') -> str:
        if len(prefix) > 0:
            return msg
        else:
            return f'{prefix}: {msg}'

    def toggle(self, prefix: str='') -> Result:
        if self.nargs != '?' and self.nargs != 0:
            return Result(
                False,
                self.make_msg('Can toggle flag only when nargs = ? | 0', prefix),
                self.nargs
            )

        if not self.value:
            self.value = True
        else:
            self.value = False

    def set_value(
        self,
        value: str | list[str] | None=None,
        prefix: str='',
    ) -> Result:
        if type(value) == list:
            l = len(value)
            if l > 1:
                return Result(
                    False,
                    self.make_msg("Expected at most 1 argument", prefix),
                    {'nargs': self.nargs, 'value': value}
                )
            elif l == 1:
                value = value[0]
            else:
                return self.set_value(prefix=prefix)

        if value != None:
            if self.nargs == 0:
                return Result(
                    False,
                    self.make_msg("Expected no arguments", prefix),
                    {'nargs': value, 'value': value}
                )

            res = self.check(value, prefix)
            if not res.ok: 
                return res
            else:
                self.value = res.value
        elif self.nargs == 1:
            return Result(
                False, 
                self.make_msg("Expected at least one argument", prefix),
                {'nargs': self.nargs, 'value': value}
            )
        else:
            self.value = True

        return Result(True, None, self.value)

    def inline_print(self, color: str='blue', end: str='', indent: int=6) -> None:
        indent = ' ' * indent
        metavar = format_metavar(self.nargs, self.metavar)
        msg = f"{indent}-{self.name} {metavar}"\
            if metavar != '' else f'{indent}-{self.name}'
        cprint(msg, color=color, end=end)

    def print(self, color: str='blue', indent: int=6, end: str='\n') -> None:
        self.inline_print(color=color, end=end, indent=indent)
        if self.help:
            indent = ' ' * (indent + 2) 
            cprint(f'{indent}{self.help}')



def split(s: str, pattern: str=r' +', maxsplit: int | None=None) -> list[str]:
    words: list[str] 

    if maxsplit:
        words = re.split(pattern, s, maxsplit=maxsplit) 
    else:
        words = re.split(pattern, s)

    words = [x.strip() for x in words if len(x) > 0]

    if len(words) == 0:
        return Result(False, "No command or argument(s) given", None)
    else:
        return Result(True, None, words)


class Command:
    def __init__(
        self,
        name: str,
        nargs: int | str=0,
        validator: Validator | None=None,
        aliases: list[str] | None=None,
        help: str | None=None,
    ) -> None:
        self.aliases = aliases
        self.help = help
        self.name = name
        self.nargs = nargs
        self.validator = validator
        self.flags: dict[str, Flag] = {}
        self.args: list[str] = []
        self._flags_aliases = {}

    def reset(self) -> None:
        self.args = []
        for flag, flag_obj in self.flags.items():
            if self._flags_aliases.get(flag):
                continue
            else:
                flag_obj.reset()
                setattr(self, flag, flag_obj.default)

    def inline_print(self, color: str='green', indent: int=2) -> None:
        cprint(self.name, 'light_red', end='')

        if len(self.flags) > 0:
            cprint(' [', color, end='')
            flags = [
                flag for name, flag in self.flags.items() 
                if name not in self._flags_aliases
            ]
            l = len(flags)

            for i, flag in enumerate(flags):
                if i != l-1:
                    flag.inline_print(end=' ', indent=0, color='light_magenta')
                else:
                    flag.inline_print(end='', indent=0, color='light_magenta')

            cprint(']', color, end='')

        metavar = format_metavar(self.nargs)
        cprint(f' {metavar}', color)

    def print(self, color: str='green', indent: int=2) -> None:
        self.inline_print(color, indent=0)

        if len(self.flags) > 0:
            flags = [
                flag for name, flag in self.flags.items() 
                if name not in self._flags_aliases
            ]
            cprint("  Valid flags:", 'blue')
            for flag in flags: flag.print(indent=4)

        if self.help:
            if len(self.flags) > 0:
                print()

            help = self.help.split("\n")
            help = [x for x in help if len(x) > 0]
            help = [f"  {x}" for x in help]
            print(("\n").join(help))

    def add_flag(
        self,
        name: str,
        nargs: int | str=0,
        validator: Validator | None=None,
        default: Value | None=None,
        aliases: list[str] | None=None,
        help: str | None=None
    ) -> Result:
        if not (nargs == 0 or nargs == 1 or nargs == '?'):
            raise Exception(f'{self.name}.{name}: Flags can only have 0 or 1 argument: `? | 0 | 1`')

        self.flags[name] = Flag(
            self.name,
            name,
            nargs,
            validator=validator,
            default=default,
            aliases=aliases,
            help=help
        )
        setattr(self, name, self.flags[name].default)

        if aliases:
            for a in aliases:
                self.flags[a] = self.flags[name]
                self._flags_aliases[a] = True

        return self.flags[name]

    def __getitem__(self, flag: str) -> Flag | None:
        if flag := self.flags.get(flag):
            return flag.value

    def get_flag(self, flag: str) -> Result:
        if self.flags.get(flag) != None:
            flag = self.flags[flag]
            return Result(True, None, flag)
        else:
            return Result(
                False,
                f"{self.name}.{flag}: No specification provided",
                {'command': self.name}
            )

    def query_flag(self, flag: str, attrib: str) -> Result:
        res = self.get_flag(flag)
        if res.ok:
            return Result(True, None, getattr(res.value, attrib))
        else:
            return res

    def parse_line(self, args: list[str]) -> tuple[bool, str | None, Value]:
        args_ = args
        positional = []
        get_nargs = lambda flag: self.query_flag(flag, "nargs")
        flags = {}
        pos = {}
        ctr = 0

        try:
            end_of_args = args.index('--')
            positional = args[end_of_args+1:]
            args = args[:end_of_args]
        except ValueError:
            pass

        for i, word in enumerate(args):
            if word[0] == '-':
                word = word[1:]
                flag = self.flags.get(word)

                if not flag:
                    return Result(False, f"{self.name}.{word}: No specification provided", args_)
                elif pos.get(word) != None:
                    return Result(False, f"{self.name}.{word}: Duplicate flag", args_)
                else:
                    if i > 0 and ctr == 0:
                        return Result(False, f'{self.name}: Redundant arguments passed before flag .{word}', args_)
                    else:
                        pos[i] = flag.name
                        ctr += 1

        pos = list(pos.items())
        pos = sorted(pos, key=lambda x: x[0])

        for i in range(len(pos)-1):
            a = pos[i]; b = pos[i+1]
            a_ind = a[0]; b_ind = b[0]
            a_flag = a[1]
            l = b_ind - a_ind - 1
            nargs = get_nargs(a_flag)

            if not nargs.ok:
                return nargs

            fargs = args[a_ind+1:b_ind]
            prefix = f'{self.name}.{a_flag}'
            res = obj.set_value(fargs, prefix)
            
            if not res.ok:
                return res
            else:
                flag = res.value
                flags[a_flag] = flag.value

        if len(pos) > 0:
            last = pos[-1]
            last_ind = last[0]
            last_args = args[last_ind+1:]
            last_flag = last[1]
            nargs = get_nargs(last_flag)
            prefix = f"{self.name}.{last_flag}"

            if not nargs.ok:
                return nargs
            else:
                nargs = nargs.value

            if len(last_args) > 0:
                if nargs == 0:
                    positional.extend(last_args)
                    last_args = []
                else:
                    positional.extend(last_args[1:])
                    last_args = [last_args[0]]

            last_obj = self.flags[last_flag]
            res = last_obj.set_value(last_args, prefix)

            if not res.ok :
                return res
            else:
                flags[last_flag] = last_obj.value
        else:
            positional = [*args, *positional]

        res = check_nargs(positional, self.nargs, self.name)
        if not res.ok:
            return res
        else:
            return Result(True, None, (positional, flags))
        
    def parse_args(
        self,
        args: list[str],
        join_args: str | None=None,
        maxsplit: int | None=None,
    ) -> Result:
        nargs = self.nargs
        cmd = self.name
        res = self.parse_line(args)

        if not res.ok:
            return Result(False, res.msg, args)

        args, kwargs = res.value
        if join_args != None:
            args = (join_args).join(args)

        if self.validator:
            res = validate(args, self.validator, cmd + ' (arguments)')
            if not res.ok:
                return Result(False, res.msg, args)

        self.args = args
        for flag, value in kwargs.items():
            t_value = type(value)
            is_list = t_value == list
            is_str = t_value == str
            l = len(value)
            flag_obj = self.flags[flag]

            if flag in self._flags_aliases:
                continue

            if nargs == '?':
                flag_obj.value = value[0] if l > 0 else True
            elif nargs == 1:
                flag_obj.value = value[0]
            elif nargs == 0:
                flag_obj.value = True
            
            setattr(self, flag, flag_obj.value)

        return Result(True, None, self)


class Parser:
    def __init__(self) -> None:
        self.commands = {}
        self._commands_aliases: dict[str, bool] = {}

    def reset(self) -> None:
        for cmd in self.commands.values():
            cmd.reset()

    def add_command(
        self,
        name: str,
        nargs: str | int=0,
        validator: Validator | None=None,
        aliases: list[str] | None=None,
        help: str | None=None,
    ) -> Command:
        self.commands[name] = Command(name, nargs, validator, aliases=aliases, help=help)
        setattr(self, name, self.commands[name])

        if aliases:
            for a in aliases:
                self.commands[a] = self.commands[name]
                self._commands_aliases[a] = True

        return self.commands[name]

    def add_cmd(
        self,
        name: str,
        nargs: str | int=0,
        validator: Validator | None=None,
        aliases: list[str] | None=None,
        help: str | None=None
    ) -> Command:
        return self.add_command(name, nargs, validator, aliases=aliases, help=help)

    def __getitem__(self, cmd: str) -> Command | None:
        return self.commands.get(cmd)

    def print(self) -> None:
        for name, cmd in self.commands.items():
            if not self._commands_aliases.get(name):
                cmd.print(color='light_grey')
                print()

    def parse(self, line: str) -> Result | None:
        tokens = split(line)
        if len(tokens) == 0:
            return Result(False, "No input provided", line)

        tokens = tokens.value
        cmd = tokens[0]
        cmds = self.commands

        if not cmds.get(cmd):
            return Result(
                False,
                f"Invalid command provided. Expected any of {(', ').join(list(cmds.keys()))}",
                line
            )
        else:
            cmd = cmds[cmd]
            return cmd.parse_args(tokens[1:])
