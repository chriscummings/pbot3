"""
tbd
"""

def process_msg(redis_client, message, read_at=None):
    """
    tbd
    """
    # Handle new author.
    if not redis_client.exists("user:"+str(message.author.id)):
        redis_client.lpush("users", message.author.id)
        redis_client.hset("user:"+str(message.author.id), mapping={
            "id":message.author.id,
            "name":message.author.name
        })

    # Handle new server
    if redis_client.exists("server:"+str(message.guild.id)) == 0:
        redis_client.lpush("servers", message.guild.id)
        redis_client.hset("server:"+str(message.guild.id), mapping={
            "id":message.guild.id,
            "name":message.guild.name
        })

    # Handle a new channel.
    if not redis_client.exists("channel:"+str(message.channel.id)):
        redis_client.lpush("server:"+str(message.guild.id)+":channels", message.channel.id)
        redis_client.lpush("channels", message.channel.id)
        redis_client.hset("channel:"+str(message.channel.id), mapping={
            "id":message.channel.id,
            "name":message.channel.name,
            "server_id":message.guild.id
        })

    # Relations
    redis_client.sadd("server:"+str(message.guild.id)+":users", str(message.author.id))
    redis_client.sadd("channel:"+str(message.channel.id)+":users", str(message.author.id))

    # Don't process existing messages.
    if redis_client.exists("message:"+str(message.id)):
        return

    redis_client.zadd("user:"+str(message.author.id)+":messages",
        {str(message.id):message.created_at.timestamp()})
    redis_client.zadd("channel:"+str(message.channel.id)+":messages",
        {str(message.id):message.created_at.timestamp()})
    redis_client.zadd("server:"+str(message.guild.id)+":messages",
        {str(message.id):message.created_at.timestamp()})
    redis_client.zadd('messages', {
        f"{message.guild.id}.{message.channel.id}-{message.id}":
            message.created_at.timestamp()})

    read_value= ""
    if read_at:
        read_value = read_at

    redis_client.hset(f"message:{message.id}", mapping={
        "id":message.id,
        "bot":int(message.author.bot),
        "server_id":message.guild.id,
        "server_name":message.guild.name,
        "channel_id":message.channel.id,
        "channel_name":message.channel.name,
        "user_id":message.author.id,
        "user_name":message.author.name,
        "user_nick":message.author.nick if hasattr(message.author, "nick") and
            message.author.nick else "",
        "content":message.clean_content,
        "timestamp":message.created_at.timestamp(),
        "created":message.created_at.strftime("%Y%m%d"),
        "response_id":"",
        "read_at":read_value,
        "refusal":"",
        "refusal_msg":""
    })
