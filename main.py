import asyncio
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import logging
import os
import time
import atexit

YDL_OPTIONS = {'format': 'bestaudio',
               'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
               'restrictfilenames': True,
               'no-playlist': True,
               'nocheckcertificate': True,
               'ignoreerrors': False,
               'logtostderr': False,
               'geo-bypass': True,
               'quiet': True,
               'no_warnings': True,
               'default_search': 'auto',
               'source_address': '0.0.0.0',
               'no_color': True,
               'overwrites': True,
               'age_limit': 100,
               'live_from_start': True}

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

youtube_dl.utils.bug_reports_message = lambda: ''
logging.basicConfig(level=logging.WARNING)

token = open("token.txt", "r").read()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(intents=intents, activity=discord.Activity(name='Вот бы багнуться и сдохнуть', type=discord.ActivityType.listening), command_prefix='-')

voice_client = None


class Node:
    def __init__(self, data):
        self.data = data  # Assign data
        self.next = None  # Initialize next as null
        self.prev = None  # Initialize prev as null


# Queue class contains a Node object
class Queue:
    def __init__(self):
        self.head = None
        self.last = None

    # Function to add an element data in the Queue
    def enqueue(self, data):
        if self.last is None:
            self.head = Node(data)
            self.last = self.head
        else:
            self.last.next = Node(data)
            self.last.next.prev = self.last
            self.last = self.last.next

    # Function to remove first element and return the element from the queue
    def dequeue(self):
        if self.head is None:
            return None
        elif self.last == self.head:
            temp = self.head.data
            self.head = None
            self.last = None
            return temp
        else:
            temp = self.head.data
            self.head = self.head.next
            self.head.prev = None
            return temp

    # Function to return top element in the queue
    def first(self):
        return self.head.data

    def next(self):
        self.dequeue()

        return self.first()

    # Function to return the size of the queue
    def size(self):
        temp = self.head
        count = 0
        while temp is not None:
            count = count + 1
            temp = temp.next
        return count

    # Function to check if the queue is empty or not
    def is_empty(self):
        if self.head is None:
            return True
        else:
            return False

    def clear(self):
        self.head = None
        self.last = None

    # Function to print the stack
    def print_queue(self):
        print("queue elements are:")
        temp = self.head
        while temp is not None:
            print(temp.data, end="->")
            temp = temp.next


queue = Queue()


@atexit.register
def cleanup():
    clean_cache_files()

    if voice_client is None:
        return
    voice_client.disconnect()


@bot.event
async def on_ready():
    print(f"Logged on as {bot.user}")


@bot.command()
async def join(ctx):
    global voice_client

    try:
        voice_channel = ctx.author.voice.channel
        voice_client = await voice_channel.connect(timeout=60.0, reconnect=False, self_deaf=True)

    except:
        await ctx.send('Не удалось подключиться!')
        print('Не удалось подключиться!')


@bot.command()
async def leave(ctx):
    await ctx.voice_client.disconnect()


@bot.command()
async def skip(ctx):
    global voice_client

    if queue.size() == 1:
        await stop(ctx)
        return

    source, metadata = queue.next()
    voice_client.source = source
    await ctx.send(f"Сейчас играет: {metadata['title']}")


@bot.command()
async def stop(ctx):
    voice_client.stop()
    queue.clear()

    await ctx.send(f"Музыка остановлена")


@bot.command()
async def play(ctx, url):
    global voice_client

    if voice_client is None or not voice_client.is_connected():
        voice_channel = ctx.author.voice.channel
        voice_client = await voice_channel.connect(timeout=60.0, reconnect=False, self_deaf=True)

    source, metadata = await get_source(url=url, loop=bot.loop)
    queue.enqueue((source, metadata))

    if voice_client.is_playing():
        await ctx.send(f"Добавлено в очередь: {metadata['title']}")
    else:
        await start_playing(ctx, voice_client, source, metadata)


async def start_playing(ctx, vc, source, metadata):
    vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(after_playing(ctx, vc, e), bot.loop))
    await ctx.send(f"Сейчас играет: {metadata['title']}")


async def after_playing(ctx, vc, error):
    if error:
        raise error
    else:
        if not queue.is_empty():
            source, metadata = queue.next()
            await start_playing(ctx, vc, source, metadata)


async def get_source(url, loop=None):
    # with youtube_dl.YoutubeDL(YDL_OPTIONS) as ydl:
    #     info = ydl.extract_info(arg, download=False)
    #
    # URL = info['url']
    #
    # return discord.FFmpegPCMAudio(executable="C:/FFmpeg/bin/ffmpeg.exe", source=URL, **FFMPEG_OPTIONS)

    with youtube_dl.YoutubeDL(YDL_OPTIONS) as ytdl:
        loop = loop or asyncio.get_event_loop()
        metadata = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        if 'entries' in metadata: metadata = metadata['entries'][0]

        url = metadata['url']

        return discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), metadata


def clean_cache_files():
    for file in os.listdir():
        file_a = file.split('.')
        if len(file_a) <= 1:
            continue

        if file_a[1] in ['webm', 'mp4', 'm4a', 'mp3', 'ogg']:
            os.remove(file)


@bot.command()
async def get_cache(ctx):
    for file in os.listdir():
        print(file)

if __name__ == '__main__':
    clean_cache_files()
    bot.run(token)
