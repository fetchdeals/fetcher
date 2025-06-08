import redis
import json
import os

client = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'), port=6379, db=0)

def get(key):
    try:
        data = client.get(key)
        return json.loads(data) if data else None
    except:
        return None

def set(key, value, ttl=3600):
    try:
        client.setex(key, ttl, json.dumps(value))
    except:
        pass