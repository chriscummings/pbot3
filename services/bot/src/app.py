import sys
import os
import json
import pprint
from dotenv import load_dotenv
from redis import Redis
import discord
import tiktoken
import time
from openai import OpenAI
from logger import logger
from ratelimit import limits, RateLimitException, sleep_and_retry
import asyncio
from datetime import datetime, timedelta
import random
from discord.ext import commands

affinity_words = ["the empreror", "40k"]
history_delve_time = timedelta(hours=6) # How far back to look for channel activity.

encoding_name = "cl100k_base"


# Load hateful words to avoid.
phobic_words = []
with open("./.phobic-words.txt") as f:
	content = f.read()
	phobic_words=content.split("\n")

def mark_as_read(messages):
	for message in messages:
		redis_client.hset("msg:"+message["id"], "read_at", datetime.now().timestamp())

def num_tokens_from_string(str):
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(str))
    return num_tokens

def response_chance_for_messages(messages):
	"""Determine if messages should be responded to and which one.
	"""
	if(len(messages)==0):
		return (0,0)

	messages.sort(key=lambda x: float(x["timestamp"]), reverse=False)

	# TODO: Add in user-affinity and other modifiers.
	message_values = {}
	message_count = 0
	user_count = 0
	duration_in_m = 0
	total_affinity_word_count = 0
	total_phobic_word_count = 0

	users = set()

	assessed_messages = []

	for i, message in enumerate(messages):

		assessed_messages.append(message)

		# Don't contribute bot comment to values
		if message["bot"] == "1":
			continue

		affinity_word_count = 0
		phobic_word_count = 0
		message_count+=1
		word_count = 0

		# Always address earliest direct references to bot.
		if "pbot" in message["content"].lower() and message["bot"] == "0" and message["read_at"] == "":
			logger.debug("Exiting message reply chance b/c of a direct call")
			mark_as_read(assessed_messages)
			return (sys.maxsize, message["id"])

		# Initial message interest value.
		message_values[message["id"]] = 0

		word_count = len((message["content"].split(" ")))

		if(message["bot"]=="0"):
			users.add(message["user_id"])

		for affinity_word in affinity_words:
			if affinity_word.lower() in message["content"].lower():
				affinity_word_count+=1

		for phobic_word in phobic_words:
			if phobic_word.lower() in  message["content"].lower():
				phobic_word_count += 1

		# Value message by "interest".
		if(message["bot"]=="1") or message["content"] == "" or message["read_at"] != "":
			message_values[message["id"]] = -99
		else:	
			message_values[message["id"]] += affinity_word_count + (word_count*0.15) - (phobic_word_count*0.33)

	# If there are no (real) users, bail.
	if(len(users)) == 0:
		logger.debug("Exiting message reply chance b/c it's all bots.")
		mark_as_read(messages)
		return(-99,0)

	start = datetime.fromtimestamp(float(messages[0]["timestamp"]))
	end = datetime.fromtimestamp(float(messages[-1]["timestamp"]))
	duration_in_m = (end-start).total_seconds()/60

	modifier = 10 # starting chance
	modifier += message_count*.025
	modifier += len(users)*.025
	modifier += duration_in_m*.025
	modifier += total_affinity_word_count*.05
	modifier -= total_phobic_word_count*.1

	mark_as_read(messages)
	return (modifier, max(message_values, key=message_values.get))

def create_response(messages, target_message_id):
		
		logger.info("create response to {}".format(target_message_id))

		# TODO: add relationship history and user summaries in the mix.

		print("create a resp")

		instruction = ""
		token_count = 0

		# Load/update prompt(s).
		with open("prompt-persona.txt") as f:
			instruction += f.read().strip()
		with open("prompt-instruction.txt") as f:
			instruction += f.read().strip()

		token_count += num_tokens_from_string(instruction)

		# Trim message history to conserve tokens. -----------------------------
		messages.sort(key=lambda x: float(x["timestamp"]), reverse=True)
		cutoff_index = None
		for i, msg in enumerate(messages):
			msg_tokens = num_tokens_from_string(msg["content"])

			if i == 0:
				token_count += msg_tokens
			else:
				if(token_count + num_tokens_from_string(msg["content"]) > 2000):
					cutoff_index = i
					break
				else:
					token_count += num_tokens_from_string(msg["content"])
		# Trim history as needed.
		if cutoff_index:
			messages = messages[0:cutoff_index]


		scene = []
		messages.sort(key=lambda x: float(x["timestamp"]), reverse=False)

		joined_message = ""

		current_user = None
		message_group = []

		for message in messages:
			# Use server nick if present.
			username = message["user_name"]
			if(message["user_nick"] != ""):
				username = message["user_nick"]

			# If new-user (or first message)
			if current_user != username:
				# Check for & handle unsent messages in buffer..
				if len(message_group) > 0:
					# Merge consecutive messages by same person.
					compacted_messages = ""
					for msg in message_group:
						compacted_messages += " "+msg["content"]
					joined_message += "{}:{} \n".format(current_user, compacted_messages)
				message_group = []
				current_user = username
				message_group.append(message)
			else:
				message_group.append(message)

		joined_message += "{}:{} \n".format(username, message["content"])
		key_message = list(filter(lambda x: x["id"] == target_message_id, messages))[0]


		instruction = instruction.replace("chat_history", joined_message)
		instruction = instruction.replace("target_message", key_message["content"])

		# Reassign token count to the end result token count.
		token_count = num_tokens_from_string(instruction)

		logger.debug("About to submit the following(tokens:{}):{}".format(token_count,instruction))

		scene.append({"role":"system", "content": instruction})

		# FIXME: exception handling
		chat_completion = openai_client.chat.completions.create(
			messages=scene,
			max_tokens=4000-token_count,
			model='gpt-3.5-turbo',
			temperature=1, #0-2
			n=1,
			user=key_message["user_name"]
		)

		logger.debug("OPENAI completetion message: "+chat_completion.choices[0].message.content.strip())

		# Clean up completion id
		completion_id = chat_completion.id.replace("chatcmpl-", "")

		# Store & update
		redis_client.hset("msg:"+target_message_id, "response_id", completion_id)
		redis_client.zadd('response_activity', {"{}.{}-{}".format(key_message["server_id"], key_message["channel_id"], completion_id):chat_completion.created})
		redis_client.hset("resp:"+completion_id, mapping={
			"response_ts":chat_completion.created,
			"model":chat_completion.model,
			"in_tokens":chat_completion.usage.prompt_tokens,
			"out_tokens":chat_completion.usage.completion_tokens,
			"message":chat_completion.choices[0].message.content.strip(),
			# "raw_api_resp":json.dumps(chat_completion),
			"message_id":target_message_id,
			"channel":key_message["channel_id"],
			"server":key_message["server_id"],
			"sent_at":"",
			"original":key_message["content"]
		})


load_dotenv()

# ------------------------------------------------------------------------------

# Set up intents for bot.
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot("", intents=intents)

redis_client = Redis(host="redis", port=6379, decode_responses=True)
openai_client = OpenAI(api_key=os.environ.get("OPENAI_KEY"))

# ------------------------------------------------------------------------------

while True:
	print("----------------")

	# Get recent messages.
	timestamp = (datetime.now() - history_delve_time).timestamp()
	msg_activity = redis_client.zrangebyscore("msg_activity", timestamp, '+inf', withscores=True)

	# Sort by newest
	msg_activity.sort(key=lambda x: x[1], reverse=True)

	# Get recently active channels
	activity_by_channel = {}
	for activity in msg_activity:
		server_id, channel_id = (activity[0].split("-")[0]).split(".")
		message_id = (activity[0].split("-")[1])
		timestamp = activity[1]
		created = datetime.fromtimestamp(timestamp)
		history_cutoff = (created-timedelta(days=1))

		# Create key for channel & populate with message history since latest message.
		if not channel_id in activity_by_channel.keys():
			activity_by_channel[channel_id] = redis_client.zrangebyscore("channel:"+channel_id+":activity", history_cutoff.timestamp(), '+inf', withscores=True)

	# Replace tuples w actual messages.
	for channel_id in activity_by_channel.keys():
		message_ids = list(map(lambda x: x[0], activity_by_channel[channel_id]))
		message_ids.sort(reverse=True)

		arbitrary_cuttoff = 30
		if(len(message_ids) > arbitrary_cuttoff):
			message_ids = message_ids[0:arbitrary_cuttoff]

		activity_by_channel[channel_id] = []

		for message_id in message_ids:
			# Fetch message.
			message = redis_client.hgetall("msg:"+message_id)
			# Add message.
			activity_by_channel[channel_id].append(message)

	# Ensure channel convo isn't all read
	read_channels = []
	for channel_id in activity_by_channel.keys():
		unread_count = 0
		for m in activity_by_channel[channel_id]:
			if m["read_at"] == "":
				unread_count += 1
		if unread_count == 0:
			read_channels.append(channel_id)
	for key in read_channels:
		print("Removing channel of all read")
		del activity_by_channel[key]

	# Sort and remove responded-to conversation.
	for channel_id in activity_by_channel.keys():
		messages = activity_by_channel[channel_id]
		messages.sort(key=lambda x: x["timestamp"], reverse=True)

		# If latest message was responded to, set messages to empty list.?
		if messages[0]["response_id"] != "":
			activity_by_channel[channel_id] = []

		# Find the last message responded to.
		else:
			responded_index = len(messages)
			for i, m in enumerate(messages): 
				if(m["response_id"] != ""):
					responded_index = i
					break
			# Chop messages prior to responded-to message.
			activity_by_channel[channel_id] = messages[0:responded_index]

	for chan in activity_by_channel.keys():
		messages = activity_by_channel[chan]

		response_chance,target_message_id = response_chance_for_messages(messages)

		roll = random.randrange(100)
		# roll = 0# FIXME: remove this

		if(response_chance > roll):
			try:
				create_response(messages, target_message_id)
			except Exception as error:
				print(error)
				pass
			 	# TODO: log & retry?

	time.sleep(0.5)

"""
Every loop:
get messages since <some-time-ago>

try to handle any unresolved "promises"
	has user messaged in channel since pbot promise?
		respond...

# handle any direct mention or "attack-on-sight-words"
if any have <attack words>, <pbot-name> or are "late" replies to pbot-resp and [haven't already been responded to]
	handle message
		get author data
		increase author.affinity
		modify author.likability?
		get N messages before this message as context
			respond to last message in context stack!
				modifiers, messages, user summary, persona prompt -> API -> response
				create expiry promise to check for reply

for remaining messages:
	# handle general conversation
	for unique channels in messages
		get last pbot channel response
		# modifiers on if pbot will chime in or not
		for every <min-wait-time> ago +?
		for every recent message participants.afinity +?
		for every message since pbot.response.time +?
		for every <affinity-word> +?
"""
