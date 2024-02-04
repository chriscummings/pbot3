import os
from redis import Redis
import discord
from dotenv import load_dotenv
import json
from logger import logger
import time
from listen.process_msg import process_msg
from datetime import datetime

# Set up intents for bot.
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Set up clients.
discord_client = discord.Client(intents=intents)
redis_client = Redis(host='redis', port=6379)

# Events -----------------------------------------------------------------------

@discord_client.event
async def on_ready():
	for guild in discord_client.guilds:

		# Handle a new server.
		if(not redis_client.exists("server:"+str(guild.id))):
			redis_client.hset("server:"+str(guild.id), mapping={
				"id":guild.id,
				"name":guild.name
			})

		for c in guild.channels:
			chan = discord_client.get_channel(c.id)
			if(chan.__class__.__name__ == "TextChannel"):

				# Handle a new channel.
				if(not redis_client.exists("channel:"+str(chan.id))):
					redis_client.hset("channel:"+str(chan.id), mapping={
						"id":chan.id,
						"name":chan.name,
						"server_id":guild.id
					})

				print(guild.name+"_"+chan.name)

				valid_results = True
				last_msg_id = chan.last_message_id

				pages = 0
				while valid_results:
					pages += 1

					# FIXME: remove this
					if pages > 1:
						break


					last_msg = await chan.fetch_message(last_msg_id)
					messages = [message async for message in chan.history(limit=50, before=last_msg)]
					if len(messages) == 0:
						valid_results = False
						break

					last_msg_id = messages[-1].id
					for message in messages:

						process_msg(redis_client, message, datetime.now().timestamp())

				
	raise Exception("halt")

# Exec -------------------------------------------------------------------------

load_dotenv()
discord_client.run(os.getenv('DISCORD_TOKEN'))