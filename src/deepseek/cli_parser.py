import re

from copy import copy
from typing import Callable
from collections import namedtuple
from termcolor import cprint
from .utils import *

NO_INPUT = "No input provided"

class CommandFlagParser:
    def __init__(
        self,
        command: str,
        name: str,
        nargs: str | int=0,
        validator: Validator=None,
        default: Value | None=None,
        aliases: list[str] | None=None,
        metavar: str | None=None,
        help: str | None=None,
    ) -> None:
        if nargs != '?' and nargs != '+' and nargs != '*' and type(nargs) != int:
            raise Exception(make_msg(
                f"Expected nargs to be a natural number or any of '+', '*', '?'",
                f'{command}.{name}'
            ))

        self.metavar = metavar
        self.aliases = aliases
        self.help = help
        self.command = command
        self.name = name
        self.nargs = nargs
        self.validator = validator
        self.default = default
        self.value: Value = default
        self.prefix = f'{self.command}.{self.name}'

    def reset(self) -> None:
        self.value = self.default

    def extract(self) -> str:
        value = self.value
        self.reset()

        return value

    def validate(self, value: str, put: bool=False) -> Result:
        res = Result(True, None, value)

        if self.validator:
            res = validate(value, self.validator, self.prefix)

        if not res.ok:
            return res

        res = check_nargs([value], self.nargs, self.prefix)
        if not res.ok:
            return res

        if put:
            print_msg(f'{self.prefix}: Setting value to `{value}`')
            self.value = res.value

        return res

    def toggle(self, prefix: str='') -> Result:
        if not self.value:
            self.value = True
        else:
            self.value = False

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


class CommandParser:
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
        self.flags: dict[str, CommandFlagParser] = {}
        self._flags_aliases: dict[str, ComamndFlagParser] = {}
        self._flags: dict[str, CommandFlagParser] = {}
        self.args: list[str] = []

    def reset(self) -> None:
        self.args = []
        for flag in self._flags.keys(): self.flags[flag].reset()

    def extract(self) -> tuple[str, list, dict[str, any]]:
        flags = {}

        for flag in self._flags.keys():
            flag: CommandFlag = self.flags[flag]
            flags[flag.name] = flag.extract()

        args = self.args
        self.args = []

        return (self.name, args, flags)

    def inline_print(self, color: str='green', indent: int=2) -> None:
        cprint(self.name, 'light_red', end='')

        if len(self._flags) > 0:
            cprint(' [', color, end='')
            flags = list(self._flags.values())
            l = len(flags)

            for i, flag in enumerate(flags):
                if i != l-1:
                    flag.inline_print(end=' ', indent=0, color='light_magenta')
                else:
                    flag.inline_print(end='', indent=0, color='light_magenta')

            cprint(']', color, end='')

        metavar = format_metavar(self.nargs)
        cprint(f' {metavar}', color)

    def print(self, color: str='green') -> None:
        self.inline_print(color, indent=0)
        p_aliases = False
        p_flags = False

        if len(self.aliases) > 0:
            cprint(f"  Aliases:\n    {(', ').join(self.aliases)}", 'blue')
            p_aliases = True

        if len(self._flags) > 0:
            if p_aliases: print()
            flags = list(self._flags.values())
            cprint("  Valid flags:", 'blue')
            for flag in flags: flag.print(indent=4)

        if self.help:
            if p_aliases or p_flags: print()
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
        self.flags[name] = CommandFlagParser(
            self.name,
            name,
            nargs,
            validator=validator,
            default=default,
            aliases=aliases,
            help=help
        )
        self._flags[name] = self.flags[name]

        if aliases:
            for a in aliases:
                self.flags[a] = self.flags[name]
                self._flags_aliases[a] = self.flags[a]

        return self._flags[name]

    def __getitem__(self, flag: str) -> CommandFlagParser | None:
        if flag := self.flags.get(flag):
            return flag

    def get_flag(self, flag: str) -> Result:
        obj = self[flag]
        if obj != None:
            return Result(True, None, obj)
        else:
            return Result(
                False,
                f"{self.name}.{flag}: No specification provided",
                Context(command=self)
            )

    def get_flag_value(self, flag: str) -> Result:
        res = self.get_flag(flag)
        if not res.ok:
            return res
        else:
            return res.value.value

    def set_flag_value(self, flag: str, value: str='', toggle: bool=False) -> Result:
        res = self.get_flag(flag)
        if not res.ok:
            return res

        flag: CommandFlag = res.value
        if len(value) == 0 and (flag.nargs == '?' or flags.nargs == 0):
            if toggle:
                flag.toggle()
            else:
                flag.value = True
        else:
            res = flag.validate(value, put=True)
            if not res.ok:
                return res

        return Result(True, None, flag)

    def query_flag(self, flag: str, attrib: str) -> Result: 
        res = self.get_flag(flag)
        if not res.ok:
            return res

        try:
            value = getattr(flag, attrib)
            return Result(True, None, value)
        except AttributeError:
            return Result(
                False,
                f'{self.name}.{flag}: No such flag attribute: {attrib}',
                Context(flag=flag, command=self)
            )

    def parse_args(self, args: list[str]) -> tuple[bool, str | None, Value]:
        args_ = args
        positional = []
        get_nargs = lambda flag: self.query_flag(flag, "nargs")
        pos = {}
        ctr = 0
        invert = {}
        toggle = {}
        flag_pos: list[tuple[int, str]]

        try:
            end_of_args = args.index('--')
            positional = args[end_of_args+1:]
            args = args[:end_of_args]
        except ValueError:
            pass

        # Check if flags are duplicate or have specification
        flag_pos = get_flag_pos(args)

        for ind, name in flag_pos:
            if '-' in name:
                name = name.replace("-", '_')

            if re.match(r'no_', name):
                name = name[3:]
                invert[name] = True
            elif re.match(r'toggle_', name):
                name = name[7:]
                toggle[name] = True

            res = self.get_flag(name)
            if not res.ok:
                return res
                
            flag = res.value
            if pos.get(name) != None:
                return Result(
                    False,
                    f"{self.name}.{name}: Duplicate flag", 
                    Context(args=args_, command=self, flag=flag)
                )
            elif ind > 0 and ctr == 0:
                return Result(
                    False,
                    f'{self.name}: Redundant arguments passed before flag .{name}', 
                    Context(args=args_, command=self, flag=flag)
                )
            else:
                pos[ind] = flag
                ctr += 1

        pos = list(pos.items())
        pos = sorted(pos, key=lambda x: x[0])

        if len(pos) == 0:
            self.args = [*args, *positional]
            return Result(True, None, self) 

        for i in range(len(pos)-1):
            current, next_ = pos[i], pos[i+1]
            current_ind, next_ind = current[0], next_[0]
            current, next_ = current[1], next_[1]
            _args = args[current_ind+1:next_ind-1]
            prefix = f'{self.name}.{current.name}'
            res = check_nargs(_args, current.nargs, prefix)

            if not res.ok:
                return res
            elif len(_args) == 0:
                if invert.get(current.name):
                    current.value = False
                elif toggle.get(current.name):
                    current.toggle()
                else:
                    current.value = True
            else:
                res = validate(_args[0], current.validator, prefix=prefix)
                if not res.ok:
                    return res
                else:
                    current.value = res.value

        last: CommandFlag = pos[-1][1]
        last_ind = pos[-1][0]
        last_args = args[last_ind+1:]
        prefix = f"{self.name}.{last.name}"

        if last.nargs == 0:
            positional.extend(last_args)
            if invert.get(last.name):
                last.value = False
            elif toggle.get(last.name):
                last.toggle()
            else:
                last.value = True

            self.args = positional
            return Result(True, None, self)
        elif len(last_args) > 0:
            positional.extend(last_args[1:])
            last_args = [last_args[0]]

        res = check_nargs(last_args, last.nargs, prefix=prefix)
        if not res.ok:
            return res

        res = last.validate(last_args[0], put=True)
        if not res.ok:
            return res

        self.args = positional
        return Result(True, None, self)
        
    def parse(
        self,
        args: list[str],
        join_args: str | None=None,
        maxsplit: int | None=None,
    ) -> Result:
        res = self.parse_args(args)
        if not res.ok:
            return res

        args = self.args
        res = check_nargs(args, self.nargs, self.name)

        if not res.ok:
            return res

        if join_args != None:
            self.args = [(join_args).join(args)]

        if self.validator:
            res = validate(args, self.validator, self.name)
            if not res.ok: return res

        return Result(True, None, self.extract())


class Parser:
    def __init__(self) -> None:
        self.commands: dict[str, CommandParser] = {}
        self._commands: dict[str, CommandParser] = {}
        self._commands_aliases: dict[str, CommandParser] = {}

    def reset(self) -> None:
        for cmd in self.commands.values(): cmd.reset()

    def __getitem__(self, command: str) -> None | CommandParser:
        return self.commands.get(command)

    def get_command(self, command: str) -> Result:
        cmd = self[command]
        if not cmd:
            return Result(False, f'{command}: No such command exists', Context(command=command))
        else:
            return Result(True, None, cmd)

    def get_cmd(self, command: str) -> Result:
        return self.get_command(command)

    def add_command(
        self,
        name: str,
        nargs: str | int=0,
        validator: Validator | None=None,
        aliases: list[str] | None=None,
        help: str | None=None,
    ) -> CommandParser:
        self.commands[name] = CommandParser(name, nargs, validator, aliases=aliases, help=help)
        self._commands[name] = self.commands[name]

        if aliases:
            for a in aliases:
                self.commands[a] = self.commands[name]
                self._commands_aliases[a] = self.commands[name]

        return self.commands[name]

    def add_cmd(
        self,
        name: str,
        nargs: str | int=0,
        validator: Validator | None=None,
        aliases: list[str] | None=None,
        help: str | None=None
    ) -> CommandParser:
        return self.add_command(name, nargs, validator, aliases=aliases, help=help)

    def print(self) -> None:
        for name, cmd in self.commands.items():
            if not self._commands_aliases.get(name):
                cmd.print(color='light_grey')
                print()

    def parse(self, line: str) -> Result:
        tokens = split(line)
        if len(tokens) == 0:
            return Result(False, "No input provided", line)

        cmd = tokens[0]
        cmds = self.commands

        res = self.get_cmd(cmd)
        if not res.ok:
            return res
        else:
            cmd = cmds[cmd]
            return cmd.parse(tokens[1:])
