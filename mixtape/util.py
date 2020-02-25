import functools
import itertools
import logging
import pkgutil
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime as dt

import youtube_dl
from mpd import MPDClient


LOG = logging.getLogger(__name__)


# @functools.lru_cache(None)
def get_resource(filename, as_bytes=False):
    data = pkgutil.get_data(__name__, f'resources/{filename}')
    return data if as_bytes else data.decode('utf-8')


def parse_command_args(message, *types):
    for entity in message.entities:
        if entity['type'] == 'bot_command':
            arg_offset = entity['length']
            break
    args = message.text[arg_offset:].split()
    if len(types) >= len(args):
        args = [t(a) for a, t in zip(args, types)]
    else:
        args = [t(a) for a, t in itertools.zip_longest(args, types, fillvalue=str)]
    return args


@contextmanager
def mpdclient(*args, timeout=10, idletimeout=10, **kwargs):
    # TODO(@shoeffner): Move to configuration
    address = '/Users/shoeffner/.mpd/socket'

    LOG.debug('Initializing MPDClient')
    client = MPDClient()
    client.timeout = timeout
    client.idletimeout = idletimeout

    client.connect(address)
    try:
        yield client
    finally:
        client.close()
        client.disconnect()


@functools.lru_cache(None)
def music_directory():
    with mpdclient() as c:
        return Path(c.listmounts()[0]['storage'])


def escape_for_MarkdownV2(s):
    """
    https://core.telegram.org/bots/api#markdownv2-style
    """
    # TODO(shoeffner): optimize
    for c in '_*[]()~`>#+-=|{}.!':
        s = s.replace(c, '\\' + c)
    return s


def format_song_for_queue(pos, song):
    fmt = '{pos:0>2}\\. `{duration:%M:%S}` {artist}{sep}{title}'

    duration = dt.fromtimestamp(float(song.get('duration', 0)))
    artist = song.get('artist', '')
    title = song.get('title', '')
    sep = ' – ' if len(artist) > 0 and len(title) > 0 else ''
    if len(artist) + len(title) == 0:
        artist = Path(song.get('file').replace('_', ' ')).stem.title()

    res = fmt.format(pos=pos, duration=duration,
                     artist=escape_for_MarkdownV2(artist),
                     title=escape_for_MarkdownV2(title),
                     sep=escape_for_MarkdownV2(sep))
    LOG.debug('queue entry %s', res)
    return res


def download_shared_file(bot, document):
    filename = ''
    if hasattr(document, 'file_name'):
        filename = document.filename
    elif hasattr(document, 'performer') and hasattr(document, 'title'):
        filename = document.performer + ' - ' + document.title + '.mp3'
    elif hasattr(document, 'performer'):
        filename = document.performer + '.mp3'
    elif hasattr(document, 'title'):
        filename = document.title + '.mp3'

    filename = music_directory() / filename
    LOG.debug('Filename of %s download: %s', document.fileid, filename)
    if not filename.is_file():
        LOG.info('Attempting to download shared file')
        bot.get_file(document.fileid).download(filename)
        LOG.info('Downloaded shared file')
        wait_for_database_update()
    return str(filename)


def download_youtube_video(url):
    opts = {
        'format': 'bestaudio/best',
        'youtube_include_dash_manifest': False,
        'outtmpl': str(music_directory()) + '/%(title)s.%(ext)s',
    }
    with youtube_dl.YoutubeDL(opts) as ydl:
        res = ydl.extract_info(url)
        filename = Path(ydl.prepare_filename(res))
        if not filename.is_file():
            LOG.debug('Downloading new file from youtube')
            ydl.download(url)
            LOG.debug('Downloaded file from youtube')
            wait_for_database_update()
    return str(filename)


def wait_for_database_update():
    with mpdclient() as c:
        LOG.debug('Idle wait for MPD database update to complete')
        c.idle('database')
        LOG.debug('Idle response %s', r)


def add_to_queue(filename):
    with mpdclient() as c:
        LOG.debug('Updating MPD database')
        r = c.update()
        LOG.debug('MPD database update result %s', r)
        LOG.debug('Adding song to queue')
        song_id = c.addid(filename)
        LOG.debug('Song ID: %s', song_id)
        return int(c.status()['playlistlength'])
