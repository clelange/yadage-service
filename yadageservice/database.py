import redis
import os
import hashlib
import uuid
import base64
import json
def database():
   return redis.StrictRedis(
                host = os.environ.get('YADAGE_JOBDB_REDIS_HOST','localhost'),
                db   = os.environ.get('YADAGE_JOBDB_REDIS_DB',0),
                port = os.environ.get('YADAGE_JOBDB_REDIS_PORT',6379),
)

db = database()

def register_job(workflow_id, resultdir):
	db.set('yadagesvc:{}:resultdir'.format(workflow_id),resultdir)

def resultdir(workflow_id):
	return db.get('yadagesvc:{}:resultdir'.format(workflow_id))

def register_user(user,b64data):
    db.set('yadagesvc:{}:b64data'.format(user),b64data)

def user_data(user):
    data = db.get('yadagesvc:{}:b64data'.format(user))
    if not data: return
    return json.loads(base64.b64decode(data))

def generate_apikey(username):
    apikey = hashlib.sha1(str(uuid.uuid4())).hexdigest()
    db.set('yadagesvc:{}:user'.format(apikey),username)
    db.rpush('yadagesvc:{}:apikeys'.format(username),apikey)
    return apikey

def apikeys(username):
    return db.lrange('yadagesvc:{}:apikeys'.format(username), 0,-1)

def apikey_user(apikey):
    return db.get('yadagesvc:{}:user'.format(apikey))
