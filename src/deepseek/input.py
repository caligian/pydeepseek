import os
import re
import sys

from typing import Callable
from termcolor import cprint, COLORS
from prompt_toolkit import prompt
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import FuzzyWordCompleter, WordCompleter, NestedCompleter
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style

class Prompt:
    def __init__(self) -> None:
        self.history_file = os.path.join(
            os.getenv("HOME"), '.deepseek', 'prompt-history.txt'
        )
        self.history = FileHistory(self.history_file)
        self.session = PromptSession(
            search_ignore_case=True,
            history=self.history
        )
        mkvalidator = Validator.from_callable
        self.validators = dict(
            is_number = mkvalidator(
                lambda x: re.search(r'^[0-9]+$', x, re.I) != None,
                error_message='Numeric input expected',
                move_cursor_to_end=True
            ),
            is_dir = mkvalidator(
                os.path.isdir,
                error_message='Expected valid directory path',
                move_cursor_to_end=True
            ),
            is_non_empty = mkvalidator(
                lambda s: len(s) > 0,
                error_message='No input provided',
                move_cursor_to_end=True
            )
        )
        mkstyle = Style.from_dict
        self.styles = {
             'frame.border': mkstyle({'frame.border': "#884444"}),
        }
        self.completers: NestedCompleter | None = None

    def add_command_completer(self, *command) -> None:
        cmds = {}

        for cmd in command:
            if len(cmd._flags) > 0:
                cmds[cmd.name] = {}
                for flag in cmd.flags.keys():
                    cmds[cmd.name]['-' + flag] = None
            else:
                cmds[cmd.name] = None

            if cmd.aliases:
                for a in cmd.aliases: cmds[a] = cmds[cmd.name]

        self.completers = NestedCompleter.from_nested_dict(cmds)

    def input(
        self,
        message: str='deepseek # ',
        multiline: bool=False,
        default: any=None,
        validator: str='is_non_empty',
        completer: list[str] | NestedCompleter=[],
        apply: Callable[[str], any]=lambda x: x,
        on_eof: Callable=lambda: None,
        on_interrupt: Callable=lambda: None
    ) -> str | None:
        response: str
        get_multiline_message = lambda: [
            ('class:multiline', '[multiline] '),
            ('class:prompt', message)
        ]
        get_message = lambda: [
            ('class:prompt', message)
        ]
        style = Style.from_dict({
            "frame.border": "#ffffff",
            "multiline": "#0f52ba",
            "prompt": "#ff0000",
        })

        if type(completer) != NestedCompleter:
            completer = self.completers if len(completer) == 0 else completer

        try:
            if multiline:
                response = self.session.prompt(
                    get_multiline_message(),
                    style=style,
                    multiline=True,
                    prompt_continuation='>> ',
                    completer=completer,
                    validator=self.validators[validator],
                    validate_while_typing=True,
                )
            else:
                response = self.session.prompt(
                    get_message(),
                    style=style,
                    completer=completer,
                    validator=self.validators[validator],
                    validate_while_typing=True,
                )
        except KeyboardInterrupt:
            sys.stdout.flush()
            on_interrupt()
            return
        except EOFError:
            sys.stdout.flush()
            on_eof()
            raise EOFError

        response = response.strip()
        if len(response) == 0:
            return None
        else:
            return apply(response)
