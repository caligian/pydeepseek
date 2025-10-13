import re

from copy import copy
from typing import Callable
from collections import namedtuple
from termcolor import cprint
from dataclasses import field, dataclass
from .utils import *
from .validate import *

ValidatorCallable = Callable[[any], any]

NO_INPUT = "No input provided"
check_nargs = VALIDATORS['has_nargs'].parse

__all__ = [
    'NO_INPUT',
    'VALIDATORS',
    'CommandFlagParser',
    'CommandParser',
    'Parser',
    'ValidatorCallable',
]

class CommandFlagParser:
    def __init__(
        self,
        command: str,
        name: str,
        nargs: str | int=0,
        validator: ValidatorCallable | str | Validator | None=None,
        default: Value | None=None,
        aliases: list[str] | None=None,
        metavar: str | None=None,
        help: str | None=None,
    ) -> None:
        name = name.replace('-', '_')

        if nargs != '?' and nargs != '+' and nargs != '*' and type(nargs) != int:
            raise ValueError(make_msg(
                f"Expected nargs to be a natural number or any of '+', '*', '?'",
                f'{command}.{name}'
            ))
        elif type(nargs) == int and nargs < 0:
            raise Exception(make_msg(
                f"Cannot use negative numbers as nargs: {nargs}",
                f'{command}.{name}'
            ))

        if validator:
            if type(validator) == str:
                validator = VALIDATORS[validator].parse
            elif type(validator) == Validator:
                validator = validator.parse

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
        self.value = None

    def extract(self) -> str:
        value = self.value
        self.value = None

        return value

    def validate(self, value: str, put: bool=False) -> any:
        check_nargs([value], self.nargs, prefix=prefix)

        if self.validator:
            value = self.validator(value)

        if put:
            self.value = value

        return value

    def set(self, value: str) -> any:
        return self.validate(value, put=True)

    def toggle(self, prefix: str='') -> bool:
        if not self.value:
            self.value = True
        else:
            self.value = False

        return self.value

    def inline_print(self, color: str='blue', end: str='', indent: int=6) -> None:
        indent = ' ' * indent
        metavar = format_metavar(self.nargs, self.metavar)
        msg = f"{indent}-{self.name.replace('_', '-')} {metavar}"\
            if metavar != '' else f'{indent}-{self.name.replace('_', '-')}'
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
        validator: ValidatorCallable | Validator | str | None=None,
        aliases: list[str] | None=None,
        help: str | None=None,
        should_parse_args: bool=True,
        variable: bool=False,
        metavar: str | None=None,
        default: Value | None=None
    ) -> None:
        if validator:
            if type(validator) == str:
                validator = VALIDATORS[validator].parse
            elif type(validator) == Validator:
                validator = validator.parse

        self.metavar=metavar
        self.default = default
        self.variable = variable
        self.aliases = aliases
        self.help = help
        self.name = name
        self.nargs = nargs
        self.validator = validator
        self.flags: dict[str, CommandFlagParser] = {}
        self._flags_aliases: dict[str, ComamndFlagParser] = {}
        self._flags: dict[str, CommandFlagParser] = {}
        self.args: list[str] = []
        self.should_parse_args = should_parse_args
        self.value: Value | None=None

        if variable:
            self.should_parse_args = False
            self.nargs = 1

    def print_value(self) -> None:
        cprint(f'{self.name} = {self.value}', 'yellow')

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
        cprint(self.name.replace("_", '-'), 'light_red', end='')

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

        metavar = format_metavar(self.nargs, self.metavar)
        cprint(f' {metavar}', color)

    def print(self, color: str='green') -> None:
        self.inline_print(color, indent=0)
        p_aliases = False
        p_flags = False
        p_flags_aliases = False
        p_var = False

        if self.aliases and len(self.aliases) > 0:
            cprint('  Aliases:', 'green')
            cprint('    ' + (', ').join(self.aliases), 'yellow')
            p_aliases = True

        if self.variable:
            if p_aliases:
                print()

            cprint(f"  Current value: {self.value}", 'yellow')
            cprint(f'  Default value: {self.default}', 'green')
            p_var = True

        if len(self._flags_aliases) > 0:
            if p_aliases or p_var:
                print()

            p_flags_aliases = True
            cprint("  Flag aliases:", 'green')

            for flag in self._flags.values():
                if len(self._flags_aliases) > 0:
                    cprint(f'    -{flag.name:<15}= ', 'blue', end='')
                    if '_' in flag.name:
                        cprint(f'-{flag.name.replace("_", "-")}, {(", ").join(["-" + x for x in flag.aliases])}', 'yellow')
                    else:
                        cprint(f'{(", ").join(["-" + x for x in flag.aliases])}', 'yellow')


        if len(self._flags) > 0:
            if p_aliases or p_flags_aliases or p_var:
                print()

            p_flags = True
            flags = list(self._flags.values())
            cprint("  Valid flags:", 'green')

            for flag in flags:
                flag.print(indent=4)

        if self.help:
            if p_aliases or p_flags or p_flags_aliases or p_var:
                print()

            help = self.help.split("\n")
            help = [x for x in help if len(x) > 0]
            help = [f"  {x}" for x in help]
            print(("\n").join(help))

    def add_flag(
        self,
        name: str,
        nargs: int | str=0,
        validator: ValidatorCallable | None=None,
        default: Value | None=None,
        aliases: list[str] | None=None,
        help: str | None=None
    ) -> CommandFlagParser:
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

    def __getitem__(self, flag: str) -> CommandFlagParser:
        if flag := self.flags.get(flag):
            return flag
        else:
            raise ValueError(f"{self.command}.{self.name}: No specification defined")


    def parse_args(self, args: list[str]) -> None:
        args_ = args
        positional = []
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
        flag_pos = get_flag_pos(args) if self.should_parse_args else []

        for ind, name in flag_pos:
            if '-' in name:
                name = name.replace("-", '_')

            if re.match(r'no_', name):
                name = name[3:]
                invert[name] = True
            elif re.match(r'toggle_', name):
                name = name[7:]
                toggle[name] = True

            flag = self[name]
            if pos.get(name) != None:
                raise ValueError(f"{self.name}.{name}: Duplicate flag")
            elif ind > 0 and ctr == 0:
                raise ValueError(f'{self.name}: Redundant arguments passed before flag .{name}')
            else:
                pos[ind] = flag
                ctr += 1

        pos = list(pos.items())
        pos = sorted(pos, key=lambda x: x[0])

        if len(pos) == 0:
            self.args = [*args, *positional]
            return

        for i in range(len(pos)-1):
            current, next_ = pos[i], pos[i+1]
            current_ind, next_ind = current[0], next_[0]
            current, next_ = current[1], next_[1]
            _args = args[current_ind+1:next_ind]
            prefix = f'{self.name}.{current.name}'
            check_nargs(_args, current.nargs, prefix=prefix)

            if len(_args) == 0:
                if invert.get(current.name):
                    current.value = False
                elif toggle.get(current.name):
                    current.toggle()
                else:
                    current.value = True
            else:
                current.validate(_args[0], put=True)

        last: CommandFlagParser = pos[-1][1]
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
            return
        elif len(last_args) > 0:
            positional.extend(last_args[1:])
            last_args = [last_args[0]]

        check_nargs(last_args, last.nargs, prefix=prefix)
        last.validate(last_args[0], put=True)

        self.args = positional
        
    def parse(self, args: list[str]) -> tuple[str, list, dict]:
        self.parse_args(args)
        check_nargs(self.args, self.nargs, prefix=self.name)

        if self.validator:
            res = self.validator(self.args)
            self.args = res if res != None else self.args

        return self.extract()


class Parser:
    def __init__(self) -> None:
        self.commands: dict[str, CommandParser] = {}
        self._commands: dict[str, CommandParser] = {}
        self._commands_aliases: dict[str, CommandParser] = {}
        self.variables: dict[str, CommandParser] = {}
        self._variables: dict[str, CommandParser] = {}
        self._variables_aliases: dict[str, CommandParser] = {}

    def reset(self) -> None:
        for cmd in self.commands.values(): cmd.reset()

    def __getitem__(self, command: str) -> CommandParser:
        if cmd := self.commands.get(command):
            return cmd
        else:
            raise ValueError(f'No specification provided for command `{command}`')

    def get_commands(self) -> list[CommandParser]:
        return list(self._commands.values())

    def get_variables(self) -> list[CommandParser]:
        return list(self._variables.values())

    def add_variable(
        self,
        name: str,
        metavar: str | None=None,
        validator: Validator | ValidatorCallable | str | None=None,
        aliases: list[str] | None=None,
        help: str | None=None,
        should_parse_args: bool=True,
        default: Value | None=None,
    ) -> CommandParser:
        return self.add_command(
            name, 
            nargs=1,
            metavar=metavar,
            validator=validator,
            aliases=aliases,
            help=help,
            should_parse_args=False,
            default=default,
            variable=True
        )

    def add_command(
        self,
        name: str,
        nargs: str | int=0,
        metavar: str | None=None,
        validator: Validator | ValidatorCallable | str | None=None,
        aliases: list[str] | None=None,
        help: str | None=None,
        should_parse_args: bool=True,
        variable: bool=False,
        default: Value | None=None,
    ) -> CommandParser:
        self.commands[name] = CommandParser(
            name,
            nargs,
            validator,
            aliases=aliases,
            help=help,
            should_parse_args=should_parse_args,
            variable=variable,
            default=default,
            metavar=metavar,
        )
        self._commands[name] = self.commands[name]

        if variable: 
            self.variables[name] = self.commands[name]
            self._variables[name] = self.commands[name]

        if aliases:
            for a in aliases:
                self.commands[a] = self.commands[name]
                self._commands_aliases[a] = self.commands[name]

                if variable:
                    self.variables[a] = self.commands[name]
                    self._variables_aliases[a] = self.commands[name]

        return self.commands[name]

    def print(self) -> None:
        for name, cmd in self.commands.items():
            if not self._commands_aliases.get(name):
                cmd.print(color='light_grey')
                print()

    def parse(self, line: str) -> any:
        tokens = split(line, maxsplit=1)
        if len(tokens) == 0:
            raise ValueError('No input provided')

        cmd = self[tokens[0]]
        tokens = tokens[1:]

        if cmd.variable:
            if len(tokens) < 1:
                raise ValueError(f"{cmd.name}: No argument provided")
            elif cmd.validator:
                cmd.value = cmd.validator(tokens[0])
            else:
                cmd.value = tokens[0]
            return (cmd.name, [cmd.value], {})
        elif len(tokens) > 0:
            return cmd.parse(split(tokens[0]))
        else:
            return cmd.parse([])


Parser.add_cmd = Parser.add_command
Parser.add_var = Parser.add_variable
Parser.get_vars = Parser.get_variables
Parser.get_cmds = Parser.get_commands
