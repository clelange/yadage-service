import redis
import os
def wflow_job_db():
   return redis.StrictRedis(
                host = os.environ['YADAGE_JOBDB_REDIS_HOST'],
                db   = os.environ['YADAGE_JOBDB_REDIS_DB'],
                port = os.environ['YADAGE_JOBDB_REDIS_PORT'],
)

db = wflow_job_db()

def register_job(jobguid, resultdir):
	db.set('yadagesvc:{}:resultdir'.format(jobguid),resultdir)

def resultdir(jobguid):
	return db.get('yadagesvc:{}:resultdir'.format(jobguid))
