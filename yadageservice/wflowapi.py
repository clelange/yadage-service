import logging
import os
import requests
import json
import redis
import time

log = logging.getLogger(__name__)

WFLOW_SERVER = os.environ.get('YADAGE_WORKFLOW_SERVER','http://localhost')

def workflow_submit(workflow_spec):
    # return ['2314t1234']
    log.info('submitting to workflow server: %s',workflow_spec)
    resp = requests.post(WFLOW_SERVER+'/workflow_submit',
    					 headers = {'content-type': 'application/json'},
    					 data = json.dumps(workflow_spec),
            )
    processing_id = resp.json()['id']
    return processing_id

def workflow_status(workflow_ids):
    resp = requests.get(WFLOW_SERVER+'/workflow_status',
    					 headers = {'content-type': 'application/json'},
    					 data = json.dumps({'workflow_ids': workflow_ids}),
            )
    return resp.json()['status_codes']

def get_workflow_messages(workflow_id, topic):
    # return ['one','two','three']
    resp = requests.get(WFLOW_SERVER+'/workflow_msgs',
                         headers = {'content-type': 'application/json'},
                         data = json.dumps({'workflow_id': workflow_id, 'topic': topic}),
            )
    return resp.json()['msgs']

def subjob_messages(subjob_id, topic):
    logdata = requests.get(WFLOW_SERVER+'/subjob_msgs',
                        headers = {'content-type': 'application/json'},
                        data = json.dumps({'subjob_id': subjob_id, 'topic': topic})
    ).json()
    return [x['msg'] for x in logdata['msgs']]

def all_wflows():
    return requests.get(WFLOW_SERVER+'/wflows').json()['wflows']

def logpubsub():
    server_data = requests.get(WFLOW_SERVER+'/pubsub_server').json()
    red = redis.StrictRedis(host = server_data['host'],
                              db = server_data['db'],
                            port = server_data['port'],)
    pubsub = red.pubsub()
    pubsub.subscribe(server_data['channel'])
    return pubsub

def log_msg_stream(breaker = None):
    pubsub = logpubsub()
    while True:
        if breaker and breaker():
            return
        message = pubsub.get_message()
        if message:
            log.info('yielding message %s', message)
            yield message      
        time.sleep(0.001)  # be nice to the system :)    
