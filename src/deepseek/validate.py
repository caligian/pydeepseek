from typing import Callable
from dataclasses import dataclass

import re


class ExcessArgumentsError(Exception):
    pass


class NotEnoughArgumentsError(Exception):
    pass


class WrongNumberOfArgumentsError(Exception):
    pass


class InvalidNargsError(Exception):
    pass


class ValidationError(Exception):
    pass


class OutOfBoundsError(Exception):
    pass


def mkdefault(value: any, when_none: Callable[[], any]) -> any:
    if value is None:
        return when_none()
    else:
        return value


def error_msg(e: Exception) -> str:
    return e.args[0]


def error_args(e: Exception) -> list:
    return list(e.args)


def make_msg(msg: str, prefix: str = "") -> str:
    if prefix == "":
        return msg
    else:
        return f"{prefix}: {msg}"


def parse_number(
    s: str,
    t: int | float,
    start: int | None = None,
    end: int | None = None,
    prefix: str = "",
) -> int:
    t_msg = "an integer" if t is int else "a decimal"
    try:
        s: int | float = t(s)
    except ValueError:
        raise ValueError(make_msg(f"Expected a {t_msg}, got {s}", prefix))

    if isinstance(start, t) and isinstance(end, t):
        if s < start or s > end:
            raise OutOfBoundsError(
                make_msg(
                    f"Expected a {t_msg} between {start} and {end}, got {s}", prefix
                )
            )
    elif isinstance(start, t):
        if s < start:
            raise OutOfBoundsError(
                make_msg(f"Expected a {t_msg} smaller than {start}, got {s}", prefix)
            )
    elif isinstance(end, t):
        if s > end:
            raise OutOfBoundsError(
                make_msg(f"Expected a {t_msg} greater than {end}, got {s}", prefix)
            )
    return s


def parse_int(
    s: str, start: int | None = None, end: int | None = None, prefix: str = ""
) -> int:
    return parse_number(s, int, start=start, end=end, prefix=prefix)


def parse_float(
    s: str,
    start: float | None = None,
    end: float | None = None,
    prefix: str = "",
) -> int:
    return parse_number(s, float, start=start, end=end, prefix=prefix)


def empty(s: str | list | dict | tuple, prefix: str = "") -> str:
    if len(s) != 0:
        raise ValueError(make_msg(f"Expected an empty container, got `{s}`", prefix))
    else:
        return s


def non_empty(s: str | list | dict | tuple, prefix: str = "") -> str:
    if len(s) == 0:
        raise ValueError(make_msg("Expected a non-empty container", prefix))
    else:
        return s


def parse_bool(s: str | int = "", prefix: str = "") -> bool:
    s = str(s)
    if s == "" or s == "off" or s.lower() == "false" or s == "0":
        return False
    elif s == "on" or s.lower() == "true" or s == "1":
        return True
    else:
        raise ValueError(
            make_msg(
                f"Expected any of `on, true, True` OR `off, false, False`, got `{s}`",
                prefix,
            )
        )


def matches(s: str, pattern: str, prefix: str = "") -> str:
    s = str(s)
    if not re.search(s, pattern, re.I + re.M):
        raise ValueError(
            make_msg(f"Could not match pattern `{pattern}` with `{s}`", prefix)
        )
    else:
        return s


def not_in(needle: str, haystack: list[str] | dict[str, str], prefix: str = "") -> str:
    if type(haystack) is list:
        if needle in haystack:
            raise ValueError(
                make_msg(f"Did not expect {needle} to exist in {haystack}", prefix)
            )
        else:
            return needle

    value = haystack.get(needle)
    if value is not None:
        raise ValueError(
            make_msg(
                f"Did not expect {needle} to exist in {list(haystack.keys())}", prefix
            )
        )
    else:
        return value


def is_in(needle: str, haystack: list[str] | dict[str, str], prefix: str = "") -> str:
    if type(haystack) is list:
        if needle not in haystack:
            raise ValueError(make_msg(f"{needle} does not exist in {haystack}", prefix))
        else:
            return needle

    value = haystack.get(needle)
    if value is None:
        raise ValueError(
            make_msg(f"{needle} does not exist in {list(haystack.keys())}", prefix)
        )
    else:
        return value


def check_nargs(
    args: str | list[str] | None, nargs: str | int, prefix: str = ""
) -> bool:
    args_len = len(args)
    args = [] if args is None else args
    args = [args] if type(args) is not list else args

    if nargs == "+":
        if args_len == 0:
            raise NotEnoughArgumentsError(make_msg("No arguments provided", prefix))
        else:
            return True
    elif nargs == "*":
        return True
    elif nargs == "?":
        if args_len > 1:
            raise ExcessArgumentsError(
                make_msg(f"Expected 1 or more arguments, got {args_len}", prefix)
            )
        else:
            return True
    elif type(nargs) is int:
        if nargs < 0:
            raise NotEnoughArgumentsError(
                make_msg(
                    f"Expected a whole number or any of ?, +, *, got {nargs}", prefix
                )
            )
        elif args_len != nargs:
            raise WrongNumberOfArgumentsError(
                make_msg(f"Expected {nargs} arguments, got {args_len}", prefix)
            )
        else:
            return True
    else:
        raise InvalidNargsError(
            make_msg(
                f"Expected a whole number or any of ?, +, *, got `{nargs}`", prefix
            )
        )


def check_command_nargs(
    cmd: str,
    args: str | list[str] | None,
    nargs: str | int,
) -> bool:
    prefix = cmd
    args: list[str] | None = [] if not args else args
    args: list[str] = [args] if type(args) is not list else args

    return check_nargs(args, nargs, prefix=prefix)


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
        *validate_args,
        **validate_kwargs,
    ) -> any:
        return f(self.parse(value, *validate_args, **validate_kwargs))

    def partial(self, *validate_args, **validate_kwargs) -> Callable[[...], any]:
        def apply(value) -> Callable:
            return self.condition(value, *validate_args, **validate_kwargs)

        return apply

    def wrap(self, *validate_args, **validate_kwargs) -> Callable[[...], any]:
        def decorator(f: Callable[[...], any]):
            return self.partial(*validate_args, **validate_kwargs)

        return decorator


@dataclass
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
        self.create("int", parse_int)
        self.create("float", parse_float)
        self.create("bool", parse_bool)
        self.create("non_empty", non_empty)
        self.create("matches", matches)
        self.create("is_in", is_in)
        self.create("not_in", not_in)
        self.create("has_nargs", check_nargs)
        self.create("command", check_command_nargs)


def with_validation(
    validators: Validators, name: str, *validator_args, **validator_kwargs
) -> Validator:
    return validators[name].pwrap(*validator_args, **validator_kwargs)


VALIDATORS = Validators()

__all__ = [
    "VALIDATORS",
    "Validators",
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
