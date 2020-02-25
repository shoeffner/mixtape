import os
from logging import getLogger
from telegram.ext import Updater


LOG = getLogger(__name__)


class MixtapeError(Exception):
    pass


try:
    updater = Updater(os.environ['TELEGRAM_BOT_TOKEN'], use_context=True)
except KeyError as e:
    raise e from MixtapeError('TELEGRAM_BOT_TOKEN environment variable not set')


# Once the updater is initialized, we can import the handlers to register them
import mixtape.handlers  # noqa


def _format_botfather_commandlist():
    from mixtape.decorators import commands
    cmds = "\n".join(commands)
    return f'{" BotFather Command List ":=^80}\n{cmds}\n{"":=^80}'


botfather_commandlist = _format_botfather_commandlist()
