import sys

from dataclasses import dataclass, field
# from .cli parser import *
# from .client import Client
# from .config import Config
# from .history import History
#
from src.deepseek.input import Prompt
from src.deepseek.utils import *
from src.deepseek.cli_parser import *
from src.deepseek.client import Client
from src.deepseek.config import Config
from src.deepseek.history import History

@dataclass
class Variable:
    name: str
    nargs: str = field(default_factory=lambda: 0)
    validator: Validator = field(default_factory=lambda: None)
    value: Value = field(default_factory=lambda: None)
    default: Value = field(default_factory=lambda: None)
    aliases: list[str] = field(default_factory=lambda: [])

    def read(self) -> Value:
        value = self.value
        self.value = None
        return value

    def validate(self, value: Value | None=None, put: bool=False) -> Result: 
        value = [] if value == None else value
        res = check_nargs(value, self.nargs)

        if not res.ok:
            return res

        if self.validator and value != None:
            res = validate(value, self.validator)
            if not res.ok:
                return res
            else:
                value = res.value

        if put and value != None:
            self.value = value

        return res

    def set(self, value: Value) -> Result:
        return self.validate(value, put=True)

    def toggle(self) -> Result:
        res = check_nargs([], self.nargs)

        if not res.ok:
            return res
        elif self.value:
            self.value = False
        else:
            self.value = True

        return Result(True, None, self.value)


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

    def add_variable(self, *vs: Variable) -> None: 
        for var in vs:
            self.variables[var.name] = var
            self._variables[var.name] = var

            for alias in var.aliases:
                self.variables[alias] = var
                self._variables_aliases[alias] = var

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

    def add_command(self, *command: CommandParser)  -> None:
        for cmd in command:
            self.commands[command.name] = command

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


CLI.toggle_var = CLI.toggle_variable
CLI.set_var = CLI.set_variable
CLI.get_vars = CLI.get_variables
CLI.read_vars = CLI.read_variables
CLI.print_vars = CLI.print_variables
CLI.add_cmd = CLI.add_command

cli = CLI()
cli.add_variable(
    Variable("stream", default=True),
    Variable(
        "max_tokens",
        aliases=['tokens', 'max-tokens'],
        validator='^[0-9]+$',
        default=3000,
    ),
    Variable(
        'clipboard',
        aliases=['copy', 'clip'],
        default=False
    )
)

add_cmd = cli.parser.add_cmd
add_cmd('help', aliases=['h'], nargs=0)
add_cmd('quit', aliases=['q'], nargs=0)
add_cmd('set', nargs='+')
add_cmd('unset', nargs=1)
add_cmd('toggle', nargs='?')
add_cmd('variables', aliases=['vars', 'v'], nargs=0)
add_cmd('defaults', aliases=['d'], nargs=0)

ask = add_cmd('ask', aliases=['/'], nargs='+')
ask.add_flag('clipboard', nargs=0, aliases=['clip', 'c'])
ask.add_flag('stream', nargs=0, aliases=['s'])
ask.add_flag('max_tokens', nargs=1, aliases=['tokens', 't'], validator=parse_int)

history = add_cmd('history', nargs='?', aliases=['?'])
history.add_flag('fzf', nargs=0, default=True, aliases=['f'])
history.add_flag('json', nargs=0, default=False, aliases=['j'])
history.add_flag('clipboard', nargs=0, default=False, aliases=['clip', 'c'])
history.add_flag('query_only', nargs=0, default=False, aliases=['q'])
history.add_flag('response_only', nargs=0, default=False, aliases=['r'])

cli.start()
