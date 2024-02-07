# pbot admin app

from flask import Flask, render_template
from redis import Redis
from datetime import datetime, timedelta

app = Flask(__name__,template_folder="admin/templates")

@app.template_filter()
def format_timestamp(value):
	return datetime.fromtimestamp(float(value)).strftime("%b %a %-d, %-H:%M")

redis_client = Redis(host="redis", port=6379, decode_responses=True)

@app.route('/channel/<channel_id>')
def channel(channel_id):
	channel = redis_client.hgetall("channel:"+channel_id)

	history_cutoff = (datetime.now() - timedelta(hours=48))
	messages = []
	for message_id in redis_client.zrangebyscore("channel:"+channel_id+":activity", history_cutoff.timestamp(), '+inf'):
		message = redis_client.hgetall("msg:"+message_id)
		messages.append(message)

	user_ids = redis_client.smembers("channel:"+channel_id+":users")
	users = []
	for user_id in user_ids:
		user = redis_client.hgetall("user:"+user_id)
		users.append(user)

	return render_template('channel.html', channel=channel,messages=messages, users=users)


@app.route('/user/<user_id>')
def user(user_id):
	user = redis_client.hgetall("user:"+user_id)

	history_cutoff = (datetime.now() - timedelta(hours=24*7))
	messages = []
	for message_id in redis_client.zrangebyscore("user:"+user_id+":activity", history_cutoff.timestamp(), '+inf'):
		message = redis_client.hgetall("msg:"+message_id)
		messages.append(message)

	messages.sort(key=lambda x: x["timestamp"], reverse=True)
	return render_template('user.html', user=user, messages=messages)




@app.route('/server/<server_id>')
def server(server_id):
	server = redis_client.hgetall("server:"+server_id)
	channels = []

	channel_ids = redis_client.lrange("server:"+server_id+":channels", 0, -1)
	for channel_id in channel_ids:
		channel = redis_client.hgetall("channel:"+channel_id)
		channels.append(channel)

	user_ids = redis_client.smembers("server:"+server_id+":users")
	users = []
	for user_id in user_ids:
		user = redis_client.hgetall("user:"+user_id)
		users.append(user)

	history_cutoff = (datetime.now() - timedelta(hours=24*7))
	messages = []
	for message_id in redis_client.zrangebyscore("server:"+server_id+":activity", history_cutoff.timestamp(), '+inf'):
		message = redis_client.hgetall("msg:"+message_id)
		messages.append(message)



	return render_template('server.html', channels=channels,server=server,messages=messages, users=users)


@app.route('/')
def hello():

	server_ids = redis_client.lrange("servers", 0, -1)
	servers = []
	for server_id in server_ids:
		server = redis_client.hgetall("server:"+server_id)
		servers.append(server)

	user_ids = redis_client.lrange("users", 0, -1)
	users = []
	for user_id in user_ids:
		user = redis_client.hgetall("user:"+user_id)
		users.append(user)



	return render_template('index.html', servers=servers,users=users)






if __name__ == '__main__':
	app.run(host="0.0.0.0", port=7777, debug=True)
