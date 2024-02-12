"""
Bot admin
"""
from datetime import datetime, timedelta
#
from flask import Flask, render_template
from redis import Redis

app = Flask(
    __name__,
    template_folder="admin/templates",
    static_folder="admin/templates/static")

@app.template_filter()
def format_timestamp(value):
    """
    tbd
    """
    return datetime.fromtimestamp(float(value)).strftime("%b %a %-d, %-H:%M")

redis_client = Redis(host="redis", port=6379, decode_responses=True)

# ------------------------------------------------------------------------------

@app.route('/channel/<channel_id>')
def channel(channel_id):
    """
    tbd
    """
    target_channel = redis_client.hgetall("channel:"+channel_id)

    history_cutoff = (datetime.now() - timedelta(hours=48))
    messages = []
    for message_id in redis_client.zrangebyscore(
            "channel:"+channel_id+":messages",
            history_cutoff.timestamp(), '+inf'):

        message = redis_client.hgetall("message:"+message_id)
        messages.append(message)

    users = []
    for user_id in redis_client.smembers("channel:"+channel_id+":users"):
        users.append(redis_client.hgetall("user:"+user_id))

    return render_template('channel.html', channel=target_channel,messages=messages, users=users)

@app.route('/user/<user_id>')
def user(user_id):
    """
    tbd
    """
    target_user = redis_client.hgetall("user:"+user_id)

    history_cutoff = (datetime.now() - timedelta(hours=24*7))
    messages = []
    for message_id in redis_client.zrangebyscore(
            "user:"+user_id+":messages",
            history_cutoff.timestamp(), '+inf'):

        message = redis_client.hgetall("message:"+message_id)
        messages.append(message)

    messages.sort(key=lambda x: x["timestamp"], reverse=True)
    return render_template('user.html', user=target_user, messages=messages)

@app.route('/server/<server_id>')
def server(server_id):
    """
    tbd
    """
    target_server = redis_client.hgetall("server:"+server_id)

    channels = []

    for channel_id in redis_client.lrange("server:"+server_id+":channels", 0, -1):
        channels.append(redis_client.hgetall("channel:"+channel_id))

    server_users = []
    for user_id in redis_client.smembers("server:"+server_id+":users"):
        server_users.append(redis_client.hgetall("user:"+user_id))

    history_cutoff = (datetime.now() - timedelta(hours=24*7))
    messages = []
    for message_id in redis_client.zrangebyscore(
        "server:"+server_id+":messages",
        history_cutoff.timestamp(), '+inf'):

        message = redis_client.hgetall("message:"+message_id)
        messages.append(message)

    return render_template('server.html', channels=channels,server=target_server,
        messages=messages, users=server_users)

@app.route('/')
def index():
    """
    tbd
    """
    servers = []
    for server_id in redis_client.lrange("servers", 0, -1):
        servers.append(redis_client.hgetall("server:"+server_id))

    all_users = []
    for user_id in redis_client.lrange("users", 0, -1):
        all_users.append(redis_client.hgetall("user:"+user_id))

    return render_template('index.html', servers=servers,users=all_users)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=7777, debug=True)
