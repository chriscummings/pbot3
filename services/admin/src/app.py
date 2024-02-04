# pbot admin app

from flask import Flask
# from redis import Redis

app = Flask(__name__)

redis_client = Redis(host="redis", port=6379, decode_responses=True)

@app.route('/')
def hello():

    redis_client.get("")






    return "Welcome to this webpage!, This webpage has been viewed time(s)"






if __name__ == '__main__':
    app.run(host="0.0.0.0", port=7777, debug=True)
