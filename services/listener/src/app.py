"""
"""
import os
from redis import Redis
import discord
from dotenv import load_dotenv
import json
from logger import logger
from discord.ext import commands, tasks
from listen.process_msg import process_msg
from datetime import datetime, timedelta
import time

# Set up intents for bot.
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Set up clients.
discord_client = discord.Client(intents=intents)
redis_client = Redis(host='redis', port=6379, decode_responses=True)

def chunk_str(blurb, size):
	"""Breaks string up (on whitespace) by chunk size."""
	if len(blurb) > size:
		all_chunks = []
		current_line = ""
		words = blurb.split(" ")

		for i, word in enumerate(words):
			# If str wouldn't exceed chunk size:
			if (len(current_line) + len(word) + 1) < size:
				# If its the initial, empty line.
				if current_line == "":
					current_line = str(word)
				# Otherwise append + space.
				else:
					current_line += " "+str(word)
			# Otherwise, start a new chunk
			else:
				all_chunks.append(current_line)
				current_line = str(word)

		# Append last chunk segment.
		all_chunks.append(current_line)

		return all_chunks
	else:
		return [blurb]

@tasks.loop(seconds=2)
async def response_check():
	# Get recent responses.
	response_delve_time = timedelta(hours=1)
	timestamp = (datetime.now() - response_delve_time).timestamp()
	response_activity = redis_client.zrangebyscore("response_activity", timestamp, '+inf', withscores=True)

	logger.debug(response_activity)

	# Handle any unsent.
	for k in response_activity:
		mixedKey = k[0].replace("resp:","")
		server_channel_ids, resp_id = mixedKey.split("-")
		_, channle_id = server_channel_ids.split(".")

		response = redis_client.hgetall("resp:"+resp_id)

		if response["sent_at"] == "":
			logger.info("handling response {}".format(response["id"]))
			channel = discord_client.get_channel(int(channle_id))
			msg = channel.get_partial_message(int(response["message_id"]))

			if len(response["message"]) > 2000:
				chunks = chunk_str(response["message"], 2000)
				try:
					for chunk in chunks:
						await msg.reply(chunk)
					redis_client.hset("resp:"+resp_id, "sent_at", datetime.now().timestamp())
				except Exception as error:
					print(error)
					logger.error(error)
			else:
				try:
					await msg.reply(response["message"])
					redis_client.hset("resp:"+resp_id, "sent_at", datetime.now().timestamp())
				except Exception as error:
					print(error)
					logger.error(error)

# Events -----------------------------------------------------------------------

@discord_client.event
async def on_ready():
	login_msg = 'We have logged in as {0.user}'.format(discord_client)
	print(login_msg)
	logger.debug(login_msg)
	response_check.start()

@discord_client.event
async def on_message(message):
	log_string = "{}|{}|{}.{}|{}({}): {}".format(
										message.created_at,
										message.id,
										message.guild.name,
										message.channel.name,
										message.author.name,
										message.author.nick,
										message.clean_content)
	logger.debug(log_string)

	process_msg(redis_client, message)

# Exec -------------------------------------------------------------------------

load_dotenv()
discord_client.run(os.getenv('DISCORD_TOKEN'))
