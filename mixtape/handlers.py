import logging
import os
import re
import sys
from threading import Thread

from telegram import ChatAction, MessageEntity
from telegram.ext.filters import Filters

import mixtape.util as util
from mixtape.util import mpdclient
from mixtape.decorators import (
    command,
    message_handler,
    error_handler,
)


LOG = logging.getLogger(__name__)
LOG.debug('Registering handlers')


@command
def start(update, context):
    """Welcome message.

    Reads the start.md and sends it to the user.
    """
    text = util.get_resource('start.md').format(update.message.from_user)
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=text,
                             parse_mode='MarkdownV2')


@command
def friends(update, context):
    """Shows my inline friends."""
    text = util.get_resource('friends.md')
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=text,
                             parse_mode='MarkdownV2')


@command
def clear(update, context):
    """Clears the queue."""
    with mpdclient() as c:
        c.clear()
    update.message.reply_text('Queue cleared!')


@command
def skip(update, context):
    """Skips the current song."""
    with mpdclient() as c:
        c.next()
    update.message.reply_text('Skipping.')


@command
def restart_bot(update, context):
    """Restarts the bot."""

    def stop_and_restart():
        """Restarts the bot."""
        from mixtape import updater
        updater.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

    update.message.reply_text('Restarting.')
    Thread(target=stop_and_restart).start()


@message_handler(Filters.document.video)
def handle_video(update, context):
    update.message.reply_text('Thanks, adding file to queue...')
    LOG.info('Video of type %s received %s', update.message.document.mime_type, update.message.document)

    context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.RECORD_AUDIO)
    fn = util.download_shared_file(context.bot, update.message.document)
    util.add_to_queue(fn)
    update.message.reply_text('Song added to queue!')


@message_handler(Filters.audio)
def handle_audio(update, context):
    update.message.reply_text('Thanks, adding file to queue...')
    LOG.info('Audio of type %s received %s', update.message.audio.mime_type, update.message.audio)

    context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.RECORD_AUDIO)
    fn = util.download_shared_file(context.bot, update.message.audio)
    util.add_to_queue(fn)
    update.message.reply_text('Song added to queue!')


# TODO(shoeffner): Add proper filter,
# TODO(shoeffner): handle multiple links from different sites?
@message_handler(Filters.entity(MessageEntity.TEXT_LINK))
def handle_youtube(update, context):
    print(update.message)
    for entity in update.message.entities:
        if entity.type != 'text_link':
            continue
        if re.match(r'^https?://(www\.)?youtu(\.be|be\.com)/', entity.url):
            context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=ChatAction.RECORD_AUDIO)
            fn = util.download_youtube_video(entity.url)
            util.add_to_queue(fn)
            update.message.reply_text('Song added to queue!')


@command
def play(update, context):
    """Starts playing."""
    with mpdclient() as c:
        c.consume(1)
        c.play()
    update.message.reply_text('Playing music.')


@command('np')
def now_playing(update, context):
    """Information about the current song."""
    with mpdclient() as c:
        song = c.currentsong()
    # TODO(shoeffner): Handle properly
    update.message.reply_text(song)


@command('status')
def status(update, context):
    """Current player status"""
    with mpdclient() as c:
        # TODO(shoeffner): Handle properly
        update.message.reply_text(c.status())


@command
def queue(update, context):
    """Lists upcoming songs."""
    args = util.parse_command_args(update.message, int)
    limit = args[0] if len(args) else 5

    with mpdclient() as c:
        items = c.playlistinfo(f'0:{limit}')

    upcoming = r'Queue is empty\.'
    if len(items) > 0:
        try:
            upcoming = '\n'.join(util.format_song_for_queue(*x) for x in enumerate(items, 1))
        except Exception as e:
            print(e)
    # upcoming = '\n'.join(upcoming.splitlines()[:1])
    print(upcoming)
    update.message.reply_text(upcoming, parse_mode='MarkdownV2')


@command
def stop(update, context):
    """Stops playing."""
    with mpdclient() as c:
        c.stop()
    update.message.reply_text('Stopping music.')


@error_handler
def error(update, context):
    LOG.error(update)
    LOG.error(context)
    if update is not None and hasattr(update, 'message'):
        update.message.reply_text('Sorry, but something went wrong...')
