from telethon import TelegramClient, events, sync
import asyncio
import discord
import os, sys
import json
import logging

logging.basicConfig(filename="app.log", level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

with open('./config.json', 'r') as f:
    global config 
    config = json.loads(f.read())
    logging.debug('Config file loaded')

telegram_client = TelegramClient("Client", config["telegram_api_id"], config["telegram_api_hash"], connection_retries = sys.maxsize, retry_delay = 10, auto_reconnect = True, timeout = 10)
telegram_client.start(bot_token="994686549:AAFnHc7lXVh83JOACiFCDzeaQe7EdBnk2aU")

discord_client = discord.Client()


async def get_current_relay(channel_id):
    for current in config["relay"]:
        if current["tlgrm_channel"] == channel_id:
            logging.debug("Current relay is" + current["title"])
            return current
    logging.debug("Relay with that tlgrm_channel not found")

async def send_to_discord(relay, text="", img_file=None):
    discord_channel = discord_client.get_channel(relay["discord_channel"])
    if img_file is not None:
        await discord_channel.send(content=text, file=img_file)    
    else:
        await discord_channel.send(content=text)

async def format_message(relay, text="", wphoto=False, is_reply=False, replied_msg=""):
    a = "\n"
    if is_reply:
        text = "Previous Message:\n{}\n------------------\nReaction:\n{}".format(replied_msg, text)
    if relay["words_correction"]["is_on"] == True:
        for word in relay["words_correction"]["delete_words"]:
            text = text.replace(word, "")
    text = "New Message/Signal By {0}:{3}{1} {3}{3}{2}".format(relay["title"], text, relay["signature"], a)
    return text

async def text_filter(relay, text):
    if relay["text_filter"]["is_on"] == True:
        for word in relay["text_filter"]["keywords"]:
            if text.find(word) != -1:
                logging.debug("Text filter isn't passed")
                return True
    return False

async def forwarder_filter(relay, forwarder_id=-1):
    if relay["forwarder_filter"]["is_on"] == True:
            if (forwarder_id in relay["forwarder_filter"]["forwarder_ids"]) == False:
                logging.debug("Forwarder filter isn't passed")
                logging.debug(forwarder_id)
                return True
    return False

async def get_img(event):
    img = await event.download_media()
    with open(img, 'rb') as f:
        discord_img = discord.File(f)
        os.remove(img)
        return discord_img

@telegram_client.on(events.NewMessage)
async def main_loop(event):
    tlgrm_channel = event.message.to_id.channel_id
    current_relay = await get_current_relay(tlgrm_channel)
    replied_msg = (await telegram_client.get_messages(current_relay["tlgrm_channel"], ids=event.reply_to_msg_id)).message if event.is_reply else ""
    text = await format_message(current_relay, event.raw_text, True if event.photo else False, event.is_reply, replied_msg)
    if await text_filter(current_relay, text):
        return False
    if hasattr(event.message.fwd_from, "channel_id"):
        if await forwarder_filter(current_relay, event.message.fwd_from.channel_id):
            return False
    if event.photo is not None:
        await send_to_discord(current_relay, text, await get_img(event))
    else:
        await send_to_discord(current_relay, text)

@discord_client.event
async def on_ready():
    logging.debug('Logged in Discord as '+discord_client.user.name)
    
@discord_client.event
async def on_disconnect():
    logging.debug('Discord client relogin...')
    await discord_client.connect()
    logging.debug('Discord client relogin - success!')

discord_client.run(config["discord_token"])
with telegram_client:
    telegram_client.run_until_disconnected()