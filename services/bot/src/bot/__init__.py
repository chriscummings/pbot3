"""
Temp home for bot functions.
"""
import sys
from datetime import datetime, timedelta
#
from openai import OpenAI
import tiktoken

AFFINITY_WORDS = [] # FIXME:
PHOBIC_WORDS = [] # FIXME:
MAX_INPUT_TOKEN_LENGTH = 2000
MAX_TOTAL_TOKEN_LENGTH = 4097
TOKEN_SLOP = 10

def active_channels(redis_client, msg_key="messages", hours=1, minutes=0):
    """
    Returns a list of channel Ids with recent activity.
    """

    cutoff = (datetime.now() - timedelta(hours=hours, minutes=minutes)).timestamp()
    messages = redis_client.zrangebyscore(msg_key, cutoff, "+inf")
    messages.sort(key=lambda x: x[1], reverse=True) # descending
    channels = set()
    for activity in messages:
        _, channel_id = (activity.split("-")[0]).split(".")
        channels.add(channel_id)
    return list(channels)

def channel_message_ids(redis_client, channel_id, hours=1, minutes=0):
    """
    Returns a list of channel's message ids within time window.
    """

    msg_key = "channel:"+channel_id+":messages"
    cutoff = (datetime.now() - timedelta(hours=hours, minutes=minutes)).timestamp()
    message_ids = redis_client.zrangebyscore(msg_key, cutoff, "+inf")
    return message_ids

def get_messages(redis_client, message_ids):
    """
    Returns a list of messagess from a list of message ids.
    """

    messages = []
    for message_id in message_ids:
        message = redis_client.hgetall("message:"+message_id)
        messages.append(message)
    return messages

def was_refused(resp):
    """
    Returns a bool on whether the response content string was a refusal.
    """

    problem_substrings = [
        "Sorry, but I can't",
        "I'm sorry, but",
        "I cannot comply",
        "As an AI developed by OpenAI",
        "As a large language model",
        "as a llm",
        "As an AI language model",
    ]

    for flag in problem_substrings:
        if flag.lower() in resp.lower():
            return True
    return False

def num_tokens_from_string(string, encoding_name="cl100k_base"):
    """
    Returns the number of tokens in a text string.
    """

    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

def trim_message_history(messages, max_tokens=MAX_INPUT_TOKEN_LENGTH):
    """
    Remove messages older that would exceed token length.
    """

    token_count = 0

    messages.sort(key=lambda x: float(x["timestamp"]), reverse=True) # descending
    cutoff_index = None

    for i, msg in enumerate(messages):
        # Handle exceeding length limit.
        if token_count + num_tokens_from_string(msg["content"]) > max_tokens:
            cutoff_index = i
            break

        # Handle acceptable message length.
        token_count += num_tokens_from_string(msg["content"])

    # Trim history as needed.
    if cutoff_index:
        return messages[0:cutoff_index]

    return messages

def mark_as_read(redis_client, messages):
    """
    Set read_at attr for messages.
    """
    for message in messages:
        redis_client.hset("message:"+message["id"], "read_at", datetime.now().timestamp())

def response_chance(messages): # FIXME: refator.
    """
    Determines the chance pbot will generate a response for message history and
    provides the key message ID pbot should address.

    Returns a tuple (%chance, key_message_id)
    """

    # Bounce on no massages.
    if len(messages) == 0:
        return (0, None)

    # Message history totals.
    # TODO: Add in user-affinity and other modifiers.
    message_values = {}
    duration_in_m = 0
    total_affinity_word_count = 0
    total_phobic_word_count = 0
    users = set()

    messages.sort(key=lambda x: float(x["timestamp"]), reverse=False)  # ascending

    assessed_messages = []
    for message in messages:
        assessed_messages.append(message)

        # Don't contribute bot comment to values
        if message["bot"] == "1":
            continue

        affinity_word_count = 0
        phobic_word_count = 0
        word_count = 0

        conditions = [
            "pbot" in message["content"].lower(),
            message["bot"] == "0",
            message["read_at"] == "",
            message["response_id"] == ""
        ]

        # Always address earliest direct references to bot.
        if all(conditions):
            #mark_as_read(assessed_messages) #??????????
            return (sys.maxsize, message["id"])

        # Initial message interest value.
        message_values[message["id"]] = 0

        word_count = len((message["content"].split(" ")))

        if message["bot"] == "0":
            users.add(message["user_id"])

        for affinity_word in AFFINITY_WORDS:
            if affinity_word.lower() in message["content"].lower():
                affinity_word_count += 1
                total_affinity_word_count += 1

        for phobic_word in PHOBIC_WORDS:
            if phobic_word.lower() in message["content"].lower():
                phobic_word_count += 1
                total_phobic_word_count += 1

        conditions = [
            message["bot"] == "1",
            message["content"] == ""
        ]

        if any(conditions):
            message_values[message["id"]] = -99
        else:
            message_values[message["id"]] += (
                affinity_word_count + (word_count * 0.15) - (phobic_word_count * 0.7)
            )

    # If there are no (real) users, bail.
    if (len(users)) == 0:
        return (-99, None)

    start = datetime.fromtimestamp(float(messages[0]["timestamp"]))
    end = datetime.fromtimestamp(float(messages[-1]["timestamp"]))
    duration_in_m = (end - start).total_seconds() / 60

    modifier = 0  # starting chance

    modifier += len(assessed_messages) * 0.025

    modifier += len(users) * 0.025

    modifier += duration_in_m * 0.025

    modifier += total_affinity_word_count * 0.05

    modifier -= total_phobic_word_count * 0.1

    return (modifier, max(message_values, key=message_values.get))

def generate_response(openai_client, messages, target_message_id, persona, instruction):
    """
    tbd
    """
    # TODO: add relationship history and user summaries in the mix.

    scene = []

    messages.sort(key=lambda x: float(x["timestamp"]), reverse=False) # ascending

    message_history_as_str = ""

    for message in messages:
        username = message["user_name"]
        # Use server nick if present.
        if message["user_nick"] != "":
            username = message["user_nick"]

        message_history_as_str += f"{username}:{message["content"]}\n"



    key_message = list(filter(lambda x: x["id"] == target_message_id, messages))[0]

    instruction = instruction.replace("chat_history", message_history_as_str)
    instruction = instruction.replace("target_message", key_message["content"])

    prompt = instruction + persona

    token_count = num_tokens_from_string(prompt)

    scene.append({"role": "system", "content": prompt})

    token_count += num_tokens_from_string('role')
    token_count += num_tokens_from_string('system')
    token_count += num_tokens_from_string('content')


    try:
        chat_completion = openai_client.chat.completions.create(
            messages=scene,
            max_tokens=(MAX_TOTAL_TOKEN_LENGTH - (token_count + TOKEN_SLOP)),
            model="gpt-3.5-turbo",
            temperature=1,  # 0-2 # vary this by if being asked for real info or not
            n=1,
            user=key_message["user_name"],
        )

        print(chat_completion)

        return chat_completion
    except Exception as error: # FIXME: too permissive.
        print(error)
        return None
