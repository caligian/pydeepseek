from typing import Callable
from dataclasses import field, dataclass
from collections import namedtuple

import re

Result = namedtuple(
    'Result',
    ('ok', 'msg', 'value'),
    defaults=(False, None, None)
)


def mkdefault(value: any, when_none: Callable[[], any]) -> any:
    if value == None:
        return when_none()
    else:
        return value


def error_msg(e: Exception) -> str:
    return e.args[0]


def error_args(e: Exception) -> list:
    return list(e.args)


def make_msg(msg: str, prefix: str='') -> str:  
    if prefix == '':
        return msg
    else:
        return f'{prefix}: {msg}'


def parse_number(
    s: str,
    t: int | float,
    start: int | None=None,
    end: int | None=None,
    prefix: str=''
) -> int:
    t_msg = 'an integer' if t == int else 'a decimal'
    try:
        s: int | float = t(s)
    except ValueError:
        raise ValueError(
            make_msg(f'Expected a {t_msg}, got {s}', prefix)
        )

    if start and end:
        if s < start or s > end:
            raise ValueError(
                make_msg(f'Expected a {t_msg} between {start} and {end}, got {s}', prefix)
            )
    elif start:
        if s < start:
            raise ValueError(
                make_msg(f'Expected a {t_msg} smaller than {start}, got {s}', prefix)
            )
    elif end:
        if s < start:
            raise ValueError(
                make_msg(f'Expected a {t_msg} greater than {end}, got {s}', prefix)
            )
    return s



def parse_int(
    s: str,
    start: int | None=None,
    end: int | None=None,
    prefix: str=''
) -> int:
    return parse_number(s, int, start=start, end=end, prefix=prefix)


def parse_float(
    s: str,
    start: float | None=None,
    end: float | None=None,
    prefix: str='',
) -> int:
    return parse_number(s, float, start=start, end=end, prefix=prefix)


def empty(
    s: str | list | dict | tuple,
    prefix: str=''
) -> str:
    if len(s) != 0:
        raise ValueError(
            make_msg(f'Expected an empty container, got `{s}`', prefix)
        )
    else:
        return s


def non_empty(
    s: str | list | dict | tuple,
    prefix: str=''
) -> str:
    if len(s) == 0:
        raise ValueError(
            make_msg(f'Expected a non-empty container', prefix)
        )
    else:
        return s


def parse_bool(s: str | int='', prefix: str='') -> bool:
    s = str(s)
    if s == '' or s == 'off' or s.lower() == 'false' or s == '0':
        return False
    elif s == 'on' or s.lower() == 'true' or s == '1':
        return True
    else:
        raise ValueError(
            make_msg(f'Expected any of `on, true, True` OR `off, false, False`, got `{s}`', prefix)
        )


def matches(s: str, pattern: str, prefix: str='') -> str:
    s = str(s)
    if not re.search(s, pattern, re.I + re.M):
        raise ValueError(
            make_msg(f"Could not match pattern `{pattern}` with `{s}`", prefix)
        )
    else:
        return s


def not_in(
    needle: str,
    haystack: list[str] | dict[str, str],
    prefix: str=''
) -> str:
    if type(haystack) == list:
        if needle in haystack:
            raise ValueError(
                make_msg(f"Did not expect {needle} to exist in {haystack}", prefix)
            )
        else:
            return needle

    value = haystack.get(needle)
    if value != None:
        raise ValueError(
            make_msg(f"Did not expect {needle} to exist in {list(haystack.keys())}", prefix)
        )
    else:
        return value


def is_in(
    needle: str,
    haystack: list[str] | dict[str, str],
    prefix: str=''
) -> str:
    if type(haystack) == list:
        if needle not in haystack:
            raise ValueError(
                make_msg(f"{needle} does not exist in {haystack}", prefix)
            )
        else:
            return needle

    value = haystack.get(needle)
    if value == None:
        raise ValueError(
            make_msg(f"{needle} does not exist in {list(haystack.keys())}", prefix)
        )
    else:
        return value


def check_nargs(
    args: str | list[str] | None,
    nargs: str | int,
    prefix: str=''
) -> bool:
    l = len(args)
    args = [] if args == None else args
    args = [args] if type(args) != list else args

    if nargs == '+':
        if l == 0:
            raise ValueError(make_msg("No arguments provided", prefix))
        else:
            return True
    elif nargs == '*':
        return True
    elif nargs == '?':
        if l > 1:
            raise ValueError(make_msg(f"Expected 1 or more arguments, got {l}", prefix))
        else:
            return True
    elif type(nargs) == int:
        if nargs < 0: 
            raise ValueError(make_msg(f"Expected a whole number or any of ?, +, *, got {nargs}", prefix))
        elif l != nargs:
            raise ValueError(make_msg(f'Expected {nargs} arguments, got {l}', prefix))
        else:
            return True
    else:
        raise ValueError(
            make_msg(f"Expected a whole number or any of ?, +, *, got `{x}`", prefix)
        )


def check_command_nargs(
    cmd: str,
    args: str | list[str] | None,
    nargs: str | int,
) -> bool:
    prefix = cmd
    l = len(args)
    args = [] if args == None else args
    args = [args] if type(args) != list else args

    if nargs == '+':
        if l == 0:
            raise ValueError(make_msg("No arguments provided", prefix))
        else:
            return True
    elif nargs == '*':
        return True
    elif nargs == '?':
        if l > 1:
            raise ValueError(make_msg(f"Expected 1 or more arguments, got {l}", prefix))
        else:
            return True
    elif type(nargs) == int:
        if nargs < 0: 
            raise ValueError(make_msg(f"Expected a whole number or any of ?, +, *, got {nargs}", prefix))
        elif l != nargs:
            raise ValueError(make_msg(f'Expected {nargs} arguments, got {l}', prefix))
        else:
            return True
    else:
        raise ValueError(
            make_msg(f"Expected a whole number or any of ?, +, *, got `{x}`", prefix)
        )


@dataclass
class Validator:
    name: str
    condition: Callable[[any], any]

    def parse(self, value: any, *validate_args, **validate_kwargs) -> any:
        return self.condition(value, *validate_args, **validate_kwargs)

    def apply(
        self,
        f: Callable[[...], any],
        value: any,
        *validate_args, **validate_kwargs,
    ) -> any:
        return f(self.parse(value, *validate_args, **validate_kwargs))

    def partial(
        self,
        *validate_args,
        **validate_kwargs
    ) -> Callable[[...], any]:
        def apply(value) -> Callable:
            return self.condition(
                value, *validate_args, **validate_kwargs
            )

        return apply

    def wrap(
        self,
        *validate_args,
        **validate_kwargs
    ) -> Callable[[...], any]:
        def decorator(f: Callable[[...], any]):
            return self.partial(*validate_args, **validate_kwargs)

        return decorator


class Validators:
    def __init__(self) -> None:
        self.validators: dict[str, Validator] = {}
        self.add_defaults()

    def get(self, key: str) -> Validator | None:
        return self.validators.get(key)

    def add(self, validator: Validator) -> Validator:
        self.validators[validator.name] = validator
        return validator

    def create(
        self,
        name: str,
        condition: Callable[[any], any],
    ) -> Validator:
        self.validators[name] = Validator(name, condition)
        setattr(self, name, self.validators[name].wrap)
        return self.validators[name]

    def __getitem__(self, name: str) -> Validator | None:
        return self.validators.get(name)

    def add_defaults(self) -> None:
        self.create('int', parse_int)
        self.create('float', parse_float)
        self.create('bool', parse_bool)
        self.create('non_empty', non_empty)
        self.create('matches', matches)
        self.create('is_in', is_in)
        self.create('not_in', not_in)
        self.create('has_nargs', check_nargs)
        self.create('command', check_command_nargs)


def with_validation(
    validators: Validators,
    name: str,
    *validator_args, **validator_kwargs
) -> Validator:
    return validators[name].pwrap(
        *validator_args, **validator_kwargs
    )

VALIDATORS = Validators()

__all__ = [
    'VALIDATORS',
    'Validators',
    "Validator",

]

# validators = Validators()
# # # validators['has_nargs'].pparse(['a', 'b', 'c'], -1, prefix='hello')
# # validators['float'].pparse(2.51, start=1.2, end=2.5, prefix='some-command')
# # validators['command'].pparse('hello', [1], nargs=0)
# # validators['is_in'].pparse(1, [11, 2, 3, 4])
# # validators.add_defaults()
# #
# @validators.int(start=1.2, end=1.5)
# def when_int_in_range(x: int) -> None:
#      print(x)
# #
# # @validators.float(start=-5.2, end=5.3)
# # def when_float_in_range(x: float) -> None:
# #     print(x + 10)
# #
# # @validators.matches('[a-z]')
# # def when_matches(s: str) -> None:
# #     print(s)
# #
# # validators.validators['int'].validate('01x')
