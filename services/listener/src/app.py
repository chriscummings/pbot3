import os
from redis import Redis
import discord
from dotenv import load_dotenv
import json
from logger import logger
from discord.ext import commands, tasks
from listen.process_msg import process_msg
from datetime import datetime, timedelta

# Set up intents for bot.
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Set up clients.
discord_client = discord.Client(intents=intents)
redis_client = Redis(host='redis', port=6379, decode_responses=True)






@tasks.loop(seconds=1)
async def response_check():
	print("heartbeat")

	# Get recent responses.
	response_delve_time = timedelta(days=5)
	timestamp = (datetime.now() - response_delve_time).timestamp()
	response_activity = redis_client.zrangebyscore("response_activity", timestamp, '+inf', withscores=True)

	# Handle any unsent.
	for k in response_activity:
		mixedKey = k[0].replace("resp:","")
		server_channel_ids, resp_id = mixedKey.split("-")
		_, channle_id = server_channel_ids.split(".")

		response = redis_client.hgetall("resp:"+resp_id)

		if response["sent_at"] == "":
			channel = discord_client.get_channel(int(channle_id))
			print(channel.name)
			msg = channel.get_partial_message(int(response["message_id"]))


			try:
				print("posting message")
				print(response)
				print(len(response["message"]))
				await msg.reply(response["message"])
				redis_client.hset("resp:"+resp_id, "sent_at", datetime.now().timestamp())

			except Exception as error:
				pass
				#FIXME: handle this


# Events -----------------------------------------------------------------------

@discord_client.event
async def on_ready():
	print('We have logged in as {0.user}'.format(discord_client))
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