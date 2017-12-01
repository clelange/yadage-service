import logging
import os
import requests
import json
import redis
import time
import database
from sqlalchemy import desc


log = logging.getLogger(__name__)

WFLOW_SERVER = os.environ.get('YADAGE_WORKFLOW_SERVER','http://localhost')

def all_wflows(username = None, details = False, status = False):
    if username:
        query = database.YadageServiceWorkflow.query.filter(
                    database.YadageServiceWorkflow.user.has(user=username)
                ).order_by(
                    desc(database.YadageServiceWorkflow.sub_date)
                ).limit(200)
    else:
        query = database.YadageServiceWorkflow.query.order_by(
            desc(database.YadageServiceWorkflow.sub_date)
        )
    wflows = query.all()
    if not details:
        return [w.wflow_id for w in wflows]
    wflows_info = []
    wflows_status = workflow_status([w.wflow_id for w in wflows])
    for w,stat in zip(wflows,wflows_status):
        details = dict(status = stat, user = w.user.user, date = w.sub_date)
        wflows_info.append({
            'jobguid': w.wflow_id,
            'details': details,
            'user_details': w.detail_data
        })
    return wflows_info

def register_job(username, workflow_id, resultdir, details):
    user = database.YadageServiceUser.query.filter_by(user=username).first()
    wflow = database.YadageServiceWorkflow(
        user = user,
        wflow_id = workflow_id,
        result_dir = resultdir,
        detail_data = details
    )
    database.db.session.add(wflow)
    database.db.session.commit()

def resultdir(workflow_id):
    wflow = database.YadageServiceUser.query.filter_by(wflow_id=workflow_id).first()
    return wflow.result_dir

def workflow_submit(username, workflow_spec):
    # return ['2314t1234']
    log.info('submitting to workflow server: %s',workflow_spec)
    resp = requests.post(WFLOW_SERVER+'/workflow_submit',
    					 headers = {'content-type': 'application/json'},
    					 data = json.dumps(workflow_spec),
            )
    processing_id = resp.json()['id']

    register_job(
        username,
        processing_id,
        workflow_spec['shipout_spec']['location'],
        details = workflow_spec.get('meta_details',{})
    )
    return processing_id

def workflow_status(workflow_ids):
    resp = requests.get(WFLOW_SERVER+'/workflow_status',
    					 headers = {'content-type': 'application/json'},
    					 data = json.dumps({'workflow_ids': workflow_ids}),
            )
    return resp.json()['status_codes']

def get_workflow_messages(workflow_id, topic):
    resp = requests.get(WFLOW_SERVER+'/workflow_msgs',
                         headers = {'content-type': 'application/json'},
                         data = json.dumps({'workflow_id': workflow_id, 'topic': topic}),
            )
    return resp.json()['msgs']

def subjob_messages(subjob_id, topic):
    resp = requests.get(WFLOW_SERVER+'/subjob_msgs',
                        headers = {'content-type': 'application/json'},
                        data = json.dumps({'subjob_id': subjob_id, 'topic': topic})
    ).json()
    return resp['msgs']

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
        if message and message['type'] == 'message':
            message_data = message['data']
            log.info('yielding message %s', message_data)
            yield json.loads(message_data)
        time.sleep(0.001)  # be nice to the system :)
