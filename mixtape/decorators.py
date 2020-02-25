import logging
from functools import wraps

from telegram.ext import (
    CommandHandler,
    MessageHandler,
)
from telegram.ext.filters import Filters

from mixtape import updater


LOG = logging.getLogger(__name__)
commands = []


def _register_command(name, fun):
    if fun.__doc__ is None:
        LOG.warning(f'No documentation for /{name} (Handler: {fun.__name__})')
        commands.append(f'{name} - Undocumented')
    else:
        firstline, *rest = fun.__doc__.splitlines()
        commands.append(f'{name} - {firstline}')

    handler = CommandHandler(name, fun)
    updater.dispatcher.add_handler(handler)


def _register_message_handler(filters, callback):
    if len(filters) > 0:
        filter_mask = filters[0]
        for f in filters[1:]:
            filter_mask |= f
    else:
        filter_mask = Filters.text
    handler = MessageHandler(filter_mask, callback)
    updater.dispatcher.add_handler(handler)


def command(name_or_fun):
    if isinstance(name_or_fun, str):
        def decorator(fun):
            @wraps(fun)
            def log_wrapper(*args, **kwargs):
                LOG.debug('Command /%s called', fun.__name__)
                return fun(*args, **kwargs)
            _register_command(name_or_fun, log_wrapper)
            return log_wrapper
        return decorator
    else:
        _register_command(name_or_fun.__name__, name_or_fun)
        return name_or_fun


def message_handler(*filters):
    def decorator(fun):
        @wraps(fun)
        def log_wrapper(*args, **kwargs):
            LOG.debug('MessageHandler %s called', fun.__name__)
            return fun(*args, **kwargs)
        _register_message_handler(filters, log_wrapper)
        return log_wrapper
    return decorator


def error_handler(fun):
    updater.dispatcher.add_error_handler(fun)
    return fun
