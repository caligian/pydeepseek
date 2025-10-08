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
        self.config = Config(**config)
        self.history = History(self.config.history_dir)
        self.client = Client(self.config, self.history)
        self.parser = Parser()
        self._commands = self.parser._commands
        self._commands_aliases = self.parser._commands_aliases
        self.commands = self.parser.commands

    def __getitem__(self, command: str) -> CommandParser | None:
        return self.commands.get(variable)

    def print_defaults(self) -> None:
        for command in self._commands.values():
            if command.variable:
                cprint(f'{command.name:<15} = {command.default}', 'green')

    def print_variables(self) -> None:
        for command in self._commands.values():
            if command.variable:
                name = command.name
                value = command.value
                default = command.default
                cprint(f'{name:<15} = {value} (default: {default})', 'green')

    def add_command(
        self,
        name: str,
        nargs: int | str=0,
        validator: Validator | None=None,
        aliases: list[str] | None=None,
        help: str | None=None,
        variable: bool=False,
        default: Value | None=None,
        metavar: str | None=None,
    ) -> CommandParser:
        self.parser.add_command(
            name,
            nargs=nargs,
            validator=validator,
            metavar=metavar,
            aliases=aliases,
            help=help,
            variable=variable,
            default=default,
        )
        return self.commands[name]

    def read_variables(self) -> dict[str, Value]:
        res = {}

        for cmd in self._commands.values():
            if cmd.variable:
                value = cmd.value
                if value == None: value = cmd.default
                res[cmd.name] = value

        return res

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
        variables: list[str] = [
            'stream',
            'clipboard',
            'max_tokens',
            'json',
        ]

        match cmd:
            case x if x in variables:
                self.commands[x].value = args[0]
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
        add_cmd = cli.add_command
        add_cmd('help', aliases=['h'], nargs=0, help="Display help")
        add_cmd('quit', aliases=['q'], nargs=0, help='Quit session')
        add_cmd('variables', aliases=['vars', 'v'], nargs=0, help='Diplay all variables for this session')
        add_cmd('defaults', aliases=['d'], nargs=0, help='Display variable defaults for this session')
        add_cmd(
            'stream',
            validator=parse_bool,
            variable=True,
            default=True,
            aliases=['st'],
            metavar='on|off',
            help='Set streaming output on|off',
        )
        add_cmd(
            'clipboard',
            validator=parse_bool,
            variable=True,
            default=False,
            metavar='on|off',
            aliases=['clip', 'cl'],
            help='Set copying output of queries to clipboard on|off',
        )
        add_cmd(
            'max_tokens',
            default=3000,
            metavar='INTEGER',
            validator=parse_int_in_range(50, 4096),
            aliases=['tokens', 'max-tokens'],
            variable=True,
            help='Set maximum number of words to output'
        )
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
            validator=parse_int_in_range(50, 4096),
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


CLI.print_vars = CLI.print_variables
CLI.add_cmd = CLI.add_command

def start_cli() -> None:
    cli = CLI.setup()
    cli.start()

start_cli()
if __name__ != '__main__':
    start_cli()
