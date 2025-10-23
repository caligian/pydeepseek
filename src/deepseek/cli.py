import sys

from termcolor import cprint
from openai import APITimeoutError
from .input import Prompt
from .validate import Validator
from .cli_parser import (
    VALIDATORS,
    CommandParser,
    Parser,
    ValidatorCallable,
)
from .client import Client
from .config import Config
from .history import History
from .utils import Value, print_error

int_in_range = VALIDATORS["int"].partial
float_in_range = VALIDATORS["float"].partial


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
        return self.commands.get(command)

    def print_variables(self) -> None:
        for command in self.parser.get_variables():
            name = command.name
            value = command.value
            default = command.default
            cprint(f"{name:<20} = {value} (default: {default})", "green")

    def add_variable(
        self,
        name: str,
        validator: Validator | ValidatorCallable | str | None = None,
        aliases: list[str] | None = None,
        help: str | None = None,
        default: Value | None = None,
        metavar: str | None = None,
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
        nargs: int | str = 0,
        validator: Validator | None = None,
        aliases: list[str] | None = None,
        help: str | None = None,
        variable: bool = False,
        default: Value | None = None,
        metavar: str | None = None,
        should_parse_args=True,
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
            should_parse_args=True,
        )
        return self.commands[name]

    def read_variables(self) -> dict[str, Value]:
        res = {}

        for cmd in self.parser.get_variables():
            value = cmd.value
            if value is None:
                value = cmd.default
            res[cmd.name] = value

        return res

    def ask(self, words: list[str], **kwargs) -> str:
        for k, v in self.read_variables().items():
            if kwargs.get(k) is None:
                kwargs[k] = v

        kwargs["stdout"] = True

        return self.client.ask((" ").join(words), **kwargs)

    def readline(self) -> str | None:
        inp = None
        try:
            inp = self.prompt.input()
        except KeyboardInterrupt:
            return self.readline()
        except EOFError:
            sys.stdout.flush()
            self.client.close()
            cprint("Goodbye.", "yellow")
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
        user_input = self.readline()
        cmd, args, kwargs = ("", [], {})

        try:
            cmd, args, kwargs = self.parser.parse(user_input)
        except Exception as error:
            print_error(error)

        match cmd:
            case x if x in self.variables:
                cmd = self.commands[x]
                if cmd.validator:
                    try:
                        cmd.validator(args[0])
                        self.commands[x].value = args[0]
                    except Exception as error:
                        print_error(error)
            case "ask":
                kwargs.update(self.read_variables())
                try:
                    self.ask(args, **kwargs)
                except Exception as error:
                    print_error(error)
            case "history":
                self.history.print(**kwargs)
            case "variables":
                self.print_variables()
            case "defaults":
                self.print_variables()
            case "help":
                self.help()
            case "quit":
                self.client.close()
                cprint("Goodbye.", "yellow")
                return

        self.next()

    def help(self) -> None:
        self.parser.print()

    def setup_default_variables(self) -> None:
        add_var = self.add_variable
        add_var(
            "top_p",
            aliases=["p"],
            validator=float_in_range(0.0, 1.0),
            help="Set nucleus sampling parameter",
        )
        add_var(
            "presence_penalty",
            aliases=["ppenalty", "pp"],
            validator=float_in_range(-2.0, 2.0),
            help="Penalize new tokens by a multiplier (range: -2.0-2.0)",
        )
        add_var(
            "frequency_penalty",
            aliases=["fpenalty", "fp"],
            validator=float_in_range(-2.0, 2.0),
            help="Penalize frequent tokens by a multiplier (range: -2.0-2.0)",
        )
        add_var(
            "temperature",
            aliases=["temp", "t"],
            validator=float_in_range(0.0, 2.0),
            help="Controls randomness (0 = deterministic, 2 = more random)",
        )
        add_var(
            "stream",
            validator="bool",
            default=True,
            aliases=["st"],
            metavar="on|off",
            help="Set streaming output on|off",
        )
        add_var(
            "clipboard",
            validator="bool",
            default=False,
            metavar="on|off",
            aliases=["clip", "cl"],
            help="Set copying output of queries to clipboard on|off",
        )
        add_var(
            "max_tokens",
            default=3000,
            metavar="INTEGER",
            validator=int_in_range(start=50, end=4096),
            aliases=["tokens", "max-tokens"],
            help="Set maximum number of words to output",
        )

    def setup_default_command(self) -> None:
        add_cmd = self.add_command
        # Show help
        add_cmd("help", aliases=["h"], nargs=0, help="Display help")

        # Quit session
        add_cmd("quit", aliases=["q"], nargs=0, help="Quit session")

        # Display all commands that are variables and affect the 'ask' command
        add_cmd(
            "variables",
            aliases=["vars", "v"],
            nargs=0,
            help="Diplay all variables for this session",
        )

        # Display defaults of the aforementioned variables
        add_cmd(
            "defaults",
            aliases=["d"],
            nargs=0,
            help="Display variable defaults for this session",
        )

        # The main command
        ask = add_cmd(
            "ask", aliases=["/", "query"], nargs="+", help="Ask deepseek a query"
        )
        add_flag = ask.add_flag
        add_flag(
            "top_p",
            nargs=1,
            aliases=["p"],
            validator=int_in_range(0.0, 1.0),
            help="Set nucleus sampling parameter",
        )
        add_flag(
            "presence_penalty",
            nargs=1,
            aliases=["ppenalty", "pp"],
            validator=float_in_range(-2.0, 2.0),
            help="Penalize new tokens by a multiplier (range: -2.0-2.0)",
        )
        add_flag(
            "frequency_penalty",
            nargs=1,
            aliases=["fpenalty", "fp"],
            validator=float_in_range(-2.0, 2.0),
            help="Penalize frequent tokens by a multiplier (range: -2.0-2.0)",
        )
        add_flag(
            "temperature",
            nargs=1,
            aliases=["temp", "t"],
            validator=float_in_range(0.0, 2.0),
            help="Control the randomness of the output (0.0-2.0)",
        )
        add_flag(
            "clipboard",
            nargs=0,
            aliases=["clip", "c"],
            help="Copy the results to clipboard",
        )
        add_flag(
            "stream",
            nargs=0,
            aliases=["s"],
            default=True,
            help="Display output as it comes",
        )
        add_flag(
            "max_tokens",
            nargs=1,
            aliases=["tokens", "t"],
            validator=int_in_range(start=50, end=4096),
            default=3000,
            help="Set the maximum number of tokens to output",
        )

        ## History command
        history = add_cmd(
            "history",
            nargs=0,
            aliases=["?", "search"],
            help="Select query and print to screen",
        )
        add_flag = history.add_flag
        add_flag(
            "fzf",
            nargs=0,
            default=True,
            aliases=["f"],
            help="Use a fuzzy matcher for queries (default: True)",
        )
        add_flag(
            "json", nargs=0, default=False, aliases=["j"], help="Output in JSON format"
        )
        add_flag(
            "clipboard",
            nargs=0,
            default=False,
            aliases=["clip", "c"],
            help="Copy the selected query to clipboard",
        )
        add_flag(
            "query-pattern",
            nargs=1,
            default=".+",
            aliases=["q", "query"],
            help="Select queries by matching pattern on queries",
        )
        add_flag(
            "response-pattern",
            nargs=1,
            default=".+",
            aliases=["r", "response", "resp"],
            help="Select queries by matching pattern on responses",
        )

    def setup_defaults(self) -> None:
        self.setup_default_variables()
        self.setup_default_command()


CLI.read_vars = CLI.read_variables
CLI.print_vars = CLI.print_variables
CLI.add_cmd = CLI.add_command
CLI.add_var = CLI.add_variable


def start_cli(**config) -> None:
    try:
        cli = CLI(**config)
        cli.setup_defaults()
        cli.start()
    except APITimeoutError:
        print_error("Restarting session.")
        start_cli()


start_cli()
