import sys

from openai import APITimeoutError
from typing import Self
from dataclasses import dataclass, field
from .input import Prompt
from .cli_parser import *
from .client import Client
from .config import Config
from .history import History


@dataclass
class CLI:
    def __init__(self, **config: dict[str, str]) -> None:
        # Will be cleared after being read each time
        self.validators = VALIDATORS
        self.prompt = Prompt()
        self.config = Config(**config)
        self.history = History(self.config.history_dir)
        self.client = Client(self.config, self.history)
        self.parser = Parser()
        self._commands = self.parser._commands
        self._commands_aliases = self.parser._commands_aliases
        self.commands = self.parser.commands
        self.variables = self.parser.variables
        self._variables = self.parser._variables
        self._variables_aliases = self.parser._variables_aliases

    def __getitem__(self, command: str) -> CommandParser | None:
        return self.commands.get(variable)

    def print_variables(self) -> None:
        for command in self.parser.get_variables():
            name = command.name
            value = command.value
            default = command.default
            cprint(f'{name:<15} = {value} (default: {default})', 'green')
    def add_variable(
        self,
        name: str,
        validator: Validator | ValidatorCallable | str | None=None,
        aliases: list[str] | None=None,
        help: str | None=None,
        default: Value | None=None,
        metavar: str | None=None,
    ) -> CommandParser:
        return self.add_command(
            name,
            nargs=1,
            validator=validator,
            should_parse_args=False,
            aliases=aliases,
            help=help,
            default=default,
            variable=True,
        )

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

        for cmd in self.parser.get_variables():
            value = cmd.value
            if value == None: value = cmd.default
            res[cmd.name] = value

        return res

    def ask(self, words: list[str], **kwargs) -> Result:
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
        res = ''

        try:
            res = self.readline()
        except EOFError:
            sys.stdout.flush()
            self.client.close()
            cprint("Goodbye.", 'yellow')
            sys.exit(0)

        cmd, args, kwargs = ('', [], {})
        try:
            cmd, args, kwargs = self.parser.parse()
        except ValueError as error:
            msg = error_msg(error)
            if msg == NO_INPUT:
                self.next()
            else:
                print_error(error_msg(error))
                self.next()

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
                res = self.ask(args, **kwargs)

                if not res.ok:
                    print_error(res.msg)
                elif res.msg:
                    print_msg(res.msg)
            case 'history':
                pattern = args[0] if len(args) > 0 else '.+'
                self.history.print(pattern, **kwargs)
            case 'variables':
                self.print_variables()
            case 'defaults':
                self.print_variables()
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
            'top_p',
            nargs=1,
            aliases=['p'],
            validator=parse_int,
            help='Set top-p'
        )
        add_flag(
            'presence_penalty',
            nargs=1,
            aliases=['ppenalty'],
            validator=parse_int,
            help='Set presence penalty'
        )
        add_flag(
            'frequency_penalty',
            nargs=1,
            aliases=['fpenalty'],
            validator=parse_int,
            help='Set frequency penalty'
        )
        add_flag(
            'temperature',
            nargs=1,
            aliases=['temp'],
            validator=parse_int,
            help='Copy the results to clipboard'
        )
        add_flag(
            'clipboard',
            nargs=0,
            aliases=['clip', 'c'],
            help='Copy the results to clipboard'
        )
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
            default=True,
            help='Display output as it comes',
        )
        add_flag(
            'max_tokens',
            nargs=1,
            aliases=['tokens', 't'],
            validator=parse_int_in_range(50, 4096),
            default=3000,
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


CLI.read_vars = CLI.read_variables
CLI.print_vars = CLI.print_variables
CLI.add_cmd = CLI.add_command
CLI.add_var = CLI.add_variable

def start_cli() -> None:
    try:
        cli = CLI.setup()
        cli.start()
    except APITimeoutError:
        print_error("Restarting session.")
        start_cli()

start_cli()
