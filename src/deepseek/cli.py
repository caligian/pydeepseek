import sys

from typing import Self
from dataclasses import dataclass, field
from .input import Prompt
from .utils import *
from .cli_parser import *
from .client import Client
from .config import Config
from .history import History


@dataclass
class CLI:
    def __init__(self, **config: dict[str, str]) -> None:
        # Will be cleared after being read each time
        self.prompt = Prompt()
        self.variables: dict[str, Variable] = {}
        self.config = Config(**config)
        self.history = History(self.config.history_dir)
        self.client = Client(self.config, self.history)
        self.parser = Parser()
        self._variables: dict[str, Variable] = {}
        self._variables_aliases: dict[str, Variable] = {}
        self._commands = self.parser._commands
        self._commands_aliases = self.parser._commands_aliases
        self.commands = self.parser.commands

    def __getitem__(self, variable: str) -> Variable | None:
        return self.variables.get(variable)

    def get_variable(self, variable: str) -> Result:
        v = self[variable]
        if v:
            return Result(True, None, v)
        else:
            return Result(
                False,
                f'No such variable has been set',
                dict(variable=variable)
            )

    def add_variables(self, *vs: Variable) -> None: 
        for var in vs:
            self.variables[var.name] = var
            self._variables[var.name] = var

            for alias in var.aliases:
                self.variables[alias] = var
                self._variables_aliases[alias] = var

    def add_variable(
        self,
        name: str,
        nargs: int | str=0,
        validator: Validator | None=None,
        default: Value | None=None,
        aliases: list[str] = []
    ) -> None:
        self.add_variables(
            Variable(
                name,
                nargs=nargs,
                validator=validator,
                default=default,
                aliases=aliases
            )
        )

    def get_variable(self, var: str) -> Result:
        if obj := self.variables.get(var):
            return Result(True, None, obj)
        else:
            return Result(False, f'No such variable: {var}', dict(variable=var))

    def read_variable(self, var: str) -> Result:
        res = self.get_variable(var)
        if not res.ok:
            return res

        obj = res.value
        value = obj.read()
        value = obj.default if value == None else value

        return Result(True, None, value)

    def print_variable(self, var: str) -> Result:
        res = self.get_variable(var)
        if not res.ok:
            return res

        obj = res.value
        cprint(f'{obj.value} (default: {obj.default})', 'green')

        return Result(True, None, obj)

    def get_variables(self) -> dict[str, Value]:
        res = {}
        for variable, obj in self._variables.items():
            obj: Variable
            res[variable] = obj.value

        return res

    def read_variables(self) -> dict[str, Value]:
        res = {}
        for variable, obj in self._variables.items():
            obj: Variable
            value = obj.read()
            if value == None: res[variable] = obj.default

        return res

    def print_defaults(self) -> None:
        for variable in self._variables.keys():
            variable = self._variables[variable]
            default = variable.default
            cprint(f'{variable.name:<15} = {default}', 'green')

    def print_variables(self) -> None:
        for variable in self._variables.keys():
            variable = self._variables[variable]
            value = variable.read()
            default = variable.default
            cprint(f'{variable.name:<15} = {value} (default: {default})', 'green')

    def add_command(
        self,
        name: str,
        nargs: int | str=0,
        validator: Validator | None=None,
        aliases: list[str] | None=None,
        help: str | None=None,
    ) -> CommandParser:
        self.parser.add_command(
            name,
            nargs=nargs,
            validator=validator,
            aliases=aliases,
            help=help
        )
        return self.commands[name]

    def add_commands(self, *commands: CommandParser) -> None:
        for cmd in commands:
            self.add_command(
                cmd.name,
                nargs=cmd.nargs,
                validator=cmd.validator,
                aliases=cmd.aliases,
                help=cmd.help
            )

    def ask(self, words: list[str], **kwargs) -> str | None:
        for k, v in self.read_variables().items():
            if kwargs.get(k) == None: kwargs[k] = v

        kwargs['stdout'] = True

        return self.client.ask((" ").join(words), **kwargs)

    def readline(self) -> str | None:
        inp = ''
        try:
            inp = self.prompt.input()
        except EOFError:
            self.client.close()
            sys.exit(0)

        if not inp:
            return self.readline()
        else:
            return inp

    def set_variable(self, key: str, value: str | None=None) -> None:
        res = self.get_variable(key)
        if not res.ok:
            print_error(res.msg)
            return

        variable = res.value
        res: Result

        match value:
            case None:
                res = variable.toggle()
            case _:
                res = variable.set(value)

        if not res.ok:
            print_error(res.msg) 

    def unset_variable(self, key: str) -> None:
        res = self.get_variable(key)
        if not res.ok:
            print_error(res.msg)
            return

        variable = res.value
        variable.value = None

    def toggle_variable(self, key: str) -> None:
        res = self.get_variable(key)
        if not res.ok:
            print_error(res.msg)
            return

        variable = res.value
        res = variable.toggle()

        if not res.ok:
            print_error(res.msg)

    def start(self) -> None:
        self.next()

    def next(self) -> None:
        cmds = self.parser._commands.values()
        self.prompt.add_command_completer(*cmds)
        res = str

        try:
            res = self.readline()
        except EOFError:
            sys.stdout.flush()
            self.client.close()
            cprint("Goodbye.", 'yellow')
            sys.exit(0)

        res: Result = self.parser.parse(res)
        if not res.ok:
            print_error(res.msg)
            return self.next()

        cmd, args, kwargs = res.value
        match cmd:
            case 'ask':
                kwargs.update(self.read_variables())
                self.ask(args, **kwargs)
            case 'history':
                pattern = args[0] if len(args) > 0 else '.+'
                self.history.print(pattern, **kwargs)
            case 'variables':
                self.print_vars()
            case 'defaults':
                self.print_defaults()
            case 'set':
                self.set_variable(*args)
            case 'unset':
                self.unset_variable(args[0])
            case 'toggle':
                self.toggle_variable(*args)
            case 'help':
                self.help()
            case 'quit':
                self.client.close()
                cprint('Goodbye.', 'yellow')
                return

        self.next()

    def help(self) -> None:
        self.parser.print()

    @classmethod
    def setup(cls) -> Self:
        cli = cls()
        add_var = cli.add_variable
        add_var('stream', default=True)
        add_var(
            'max_tokens',
            nargs=1,
            default=3000,
            validator=parse_int,
            aliases=['tokens', 'max-tokens']
        )
        add_var(
            'clipboard',
            nargs=0,
            aliases=['clip'],
            default=False,
        )

        add_cmd = cli.add_command
        add_cmd('help', aliases=['h'], nargs=0, help="Display help")
        add_cmd('quit', aliases=['q'], nargs=0, help='Quit session')
        add_cmd('set', nargs='+', help='Set variable with a value')
        add_cmd('unset', nargs=1, help='Unset a variable. This variable will now use default values')
        add_cmd('toggle', nargs='?', help='Toggle a variable')
        add_cmd('variables', aliases=['vars', 'v'], nargs=0, help='Diplay all variables for this session')
        add_cmd('defaults', aliases=['d'], nargs=0, help='Display variable defaults for this session')

        ask = add_cmd(
            'ask',
            aliases=['/'],
            nargs='+',
            help='Ask deepseek a query'
        )
        add_flag = ask.add_flag
        add_flag(
            'clipboard',
            nargs=0,
            aliases=['clip', 'c'],
            help='Copy the results to clipboard'
        )
        add_flag(
            'stream', 
            nargs=0,
            aliases=['s'],
            help='Display output as it comes'
        )
        add_flag(
            'max_tokens',
            nargs=1,
            aliases=['tokens', 't'],
            validator=parse_int,
            help='Set the maximum number of tokens to output'
        )

        history = add_cmd(
            'history',
            nargs='?',
            aliases=['?'],
            help='Display and select query (optionally with a pattern)'
        )
        add_flag = history.add_flag
        add_flag(
            'fzf',
            nargs=0,
            default=True,
            aliases=['f'],
            help='Use a fuzzy matcher for queries (default: True)',
        )
        add_flag(
            'json',
            nargs=0,
            default=False,
            aliases=['j'],
            help='Output in JSON format'
        )
        add_flag(
            'clipboard',
            nargs=0,
            default=False,
            aliases=['clip', 'c'],
            help='Copy the selected query to clipboard'
        )
        add_flag(
            'query_only',
            nargs=0,
            default=False,
            aliases=['q'],
            help='Select from queries and not print their response'
        )
        add_flag(
            'response_only',
            nargs=0,
            default=False,
            aliases=['r'],
            help='Select from responses instead of queries and print only the response'
        )

        return cli


CLI.toggle_var = CLI.toggle_variable
CLI.set_var = CLI.set_variable
CLI.get_vars = CLI.get_variables
CLI.get_var = CLI.get_variable
CLI.read_var = CLI.read_variable
CLI.read_vars = CLI.read_variables
CLI.print_vars = CLI.print_variables
CLI.add_cmd = CLI.add_command
CLI.add_cmds = CLI.add_commands
CLI.add_var = CLI.add_variable
CLI.add_vars = CLI.add_variables


def start_cli() -> None:
    cli = CLI.setup()
    cli.start()

start_cli()
if __name__ != '__main__':
    start_cli()
