import sys
import re
import os
import datetime
import json
import openai 

from termcolor import cprint
from .utils import *

pjoin = os.path.join
HOME = os.getenv('HOME')

class Config:
    def __init__(
        self,
        api_key_file: str=pjoin(HOME, '.deepseek', 'api-key.txt'),
        history_dir: str=pjoin(HOME, '.deepseek', 'history'),
        write_on_append: bool=True,
    ) -> None:
        self.api_key_file = api_key_file
        self.history_dir = history_dir
        self.write_on_append = write_on_append
        self.file = pjoin(HOME, '.deepseek', 'config') 
        self._valid_keys = {
            'api_key_file': True, 
            'history_dir': True,
            'write_on_append': True,
        }

        if not os.path.isfile(self.file):
            self.write()

        self.read()

    def read(self) -> None:
        print_info(f"Reading config from {self.file}")

        with open(self.file) as fh:
            text = fh.read().strip()
            text = text.split("\n")

            for i, line in enumerate(text):
                if re.match(r'^\s*#', line):
                    continue
                elif '=' in line:
                    line = line.split("=", maxsplit=2)
                    line = [x.strip() for x in line]

                    if len(line) != 2:
                        print_warn(f"Parsing error on line {i}:\nExpected form: <key> = <value>, got {line}")
                        sys.exit(1)

                    var, value = line
                    if not re.search(r'[a-z_]+', var):
                        print_warn(f"Parsing error on line {i}:\n<key> can only contain lowercase letters and underscore")
                        sys.exit(1)
                    elif not self._valid_keys.get(var):
                        print_warn(f"Parsing error on line {i}:\nExpected any of {(', ').join(list(self._valid_keys.keys()))}, got {var}")
                        sys.exit(1)
                    else:
                        match var:
                            case 'api_key_file':
                                if not os.path.isfile(value):
                                    error(f"Invalid API key path: {value}", "red")
                            case 'write_on_append':
                                if value == 'off' or value == 'false' or value == 'False' or value == '0':
                                    value = False
                                else:
                                    value = True

                        setattr(self, var, value)

    def write(self) -> None:
        with open(self.file, 'w') as fh:
            for k in self._valid_keys.keys():
                v = getattr(self, k)
                fh.write(f'{k} = {v}\n')


