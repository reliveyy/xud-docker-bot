from __future__ import annotations

import argparse


class ArgumentError(Exception):
    pass


class CommandHelp(Exception):
    pass


class _HelpAction(argparse.Action):

    def __init__(self,
                 option_strings,
                 dest=argparse.SUPPRESS,
                 default=argparse.SUPPRESS,
                 help=None):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        raise CommandHelp(parser.format_help())


class ArgumentParser(argparse.ArgumentParser):
    """
    https://stackoverflow.com/questions/5943249/python-argparse-and-controlling-overriding-the-exit-status-code
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register("action", "help", _HelpAction)

    def error(self, message):
        raise ArgumentError(message)
