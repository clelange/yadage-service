from gevent import monkey
monkey.patch_all()

import socketio
import logging
import time
import os
import msgpack
import json
import jobdb
import requests

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask.ext.autoindex import AutoIndex

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

import wflowapi
import submission


logging.basicConfig(level = logging.INFO)
log = logging.getLogger(__name__)
sio = socketio.Server(logger=True, async_mode='gevent')
app = Flask(__name__)
app.debug = True
app.wsgi_app = socketio.Middleware(sio, app.wsgi_app)
app.config['SECRET_KEY'] = 'secret!'


def background_thread():
    """Example of how to send server generated events to clients."""
    log.info('starting background thread')
    for m in wflowapi.log_msg_stream():
        log.info('got message from wflow api %s', m)
        time.sleep(0.01)
        if m['type'] == 'message':
            sio.emit('join_ack', {'data': 'got a message from wflowapi','msg':m} , room='testroom', namespace='/test')
            data = msgpack.unpackb(m['data'])[0]
            extras = msgpack.unpackb(m['data'])[1]
            if(data['nsp'] == '/monitor'):
                if(extras['rooms']):
                    for room in extras['rooms']:
                        try:
                            msg_endpoint, msg_data = data['data'] # msg_endpoint usuall room_msg, msg_data = {'type':XXX, 'msg': YYY}
                            sio.emit('room_msg', msg_data, room=room, namespace='/test')
                        except:
                            log.exception('something went wrong in message handling')
                            pass
                        finally:
                            pass



############################################
############################################

def user_data(access_token):
    r = requests.get(
        'https://oauthresource.web.cern.ch/api/Me',
        headers={'Authorization': 'Bearer {}'.format(access_token)}
    )
    return r.json()

def extract_user_info(userdata):
    userjson = {'experiment': 'unaffiliated'}

    egroup_to_expt = {
        'cms-members': 'CMS',
        'alice-member': 'ALICE',
        'atlas-active-members-all': 'ATLAS',
        'lhcb-general': 'LHCb'
    }

    for x in userdata:
        if x['Type'] == 'http://schemas.xmlsoap.org/claims/Firstname':
            userjson['firstname'] = x['Value']
        if x['Type'] == 'http://schemas.xmlsoap.org/claims/Lastname"':
            userjson['lastname'] = x['Value']
        if x['Type'] == 'http://schemas.xmlsoap.org/claims/CommonName':
            userjson['username'] = x['Value']
        if x['Type'] == 'http://schemas.xmlsoap.org/claims/Group':
            if x['Value'] in egroup_to_expt:
                userjson['experiment'] = egroup_to_expt[x['Value']]
    return userjson

from flask_oauth import OAuth
oauth = OAuth()
oauth_app = oauth.remote_app('oauth_app',
                             base_url=None,
                             request_token_url=None,
                             access_token_url=os.environ['YADAGE_OAUTH_TOKENURL'],
                             authorize_url=os.environ[
                                 'YADAGE_OAUTH_AUTHORIZEURL'],
                             consumer_key=os.environ[
                                 'YADAGE_OAUTH_APPID'],
                             consumer_secret=os.environ[
                                 'YADAGE_OAUTH_SECRET'],
                             request_token_params={
                                 'response_type': 'code', 'scope': 'bio'},
                             access_token_params={
                                 'grant_type': 'authorization_code'},
                             access_token_method='POST'
                             )

@app.route(os.environ.config['YADAGE_OAUTH_REDIRECT_ROUTE'])
@oauth_app.authorized_handler
def oauth_redirect(resp):
    next_url = request.args.get('next') or url_for('home')
    if resp is None:
        return redirect(next_url)

    data = user_data(resp['access_token'])
    session['user'] = extract_user_info(data)
    return redirect(next_url)

@app.route('/login')
def login():
    redirect_uri = os.environ['YADAGE_BASEURL'] + url_for('oauth_redirect')
    return oauth_app.authorize(callback=redirect_uri)


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/')


############################################
############################################


@app.route('/workflow_submit', methods=['POST'])
def sandbox_submit():
    data = request.json
    log.info('workflow submission requested with data %s', data)

    data['outputs'] = data['outputs'].split(',')
    spec = submission.submit_spec(**data)

    processing_id = wflowapi.workflow_submit(spec)
    jobdb.register_job(processing_id,spec['shipout_spec']['location'])
    return jsonify({'jobguid': processing_id})

@app.route('/results/<jobguid>')
@app.route('/results/<jobguid>/<path:path>')
def results(jobguid, path = "."):
    basepath = jobdb.resultdir(jobguid)
    basepath = basepath.split(os.environ['YADAGE_RESULTBASE'],1)[-1].strip('/')
    return redirect(url_for('autoindex', path = os.path.join(basepath,path)))

idx = AutoIndex(app, os.environ['YADAGE_RESULTBASE'], add_url_rules=False)
@app.route('/resultfiles')
@app.route('/resultfiles/<path:path>')
def autoindex(path='.'):
    return idx.render_autoindex(path)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/submit')
def submit():
    presets = {}
    presets['toplevel'] = request.args.get('toplevel', None)
    presets['workflow'] = request.args.get('workflow', None)
    presets['outputs'] = request.args.get('outputs', None)
    presets['archive'] = request.args.get('archive', None)
    presets['pars'] = json.dumps(json.loads(request.args.get('pars', '{}')))
    presets = {k: v for k, v in presets.iteritems() if v is not None}
    return render_template('submit.html', presets = presets)

@app.route('/monitor/<identifier>')
def monitor(identifier):
    return render_template('monitor.html', jobguid=identifier)

@app.route('/joboverview')
def joboverview():
    all_jobs = wflowapi.all_jobs()
    job_info = [{'jobguid':jid, 'details':{'status':stat}} for stat,jid in zip(wflowapi.workflow_status(all_jobs),all_jobs)]
    return render_template('joboverview.html', job_info = job_info)

@sio.on('connect', namespace='/test')
def connect(sid, environ):
    print('Client connected')


@sio.on('join', namespace='/test')
def enter(sid, data):
    print('data', data)
    print('Adding Client {} to room {}'.format(sid, data['room']))
    sio.enter_room(sid, data['room'], namespace='/test')


    latest_state = None
    stored_messages = wflowapi.get_stored_messages(data['room'])
    for msg in stored_messages:
        old_msg_data = json.loads(msg)
        if old_msg_data['type'] == 'yadage_stage':
            latest_state = old_msg_data
            continue
        else:
            sio.emit('room_msg', old_msg_data, room=data['room'], namespace='/test')
    if latest_state:
        sio.emit('room_msg', latest_state, room=data['room'], namespace='/test')


    for msg in stored_messages:
        sio.emit('join_ack', {'note':'just for you', 'msg': msg}, room = sid, namespace='/test')

@sio.on('roomit', namespace='/test')
def roomit(sid, data):
    print('Emitting to Room: {}'.format(data['room']))
    sio.emit('join_ack', {'data':'Welcome a new member to the room {}'.format(data['room'])}, room=data['room'], namespace='/test')

@sio.on('disconnect', namespace='/test')
def disconnect(sid):
    print('Client disconnected')


if __name__ == '__main__':
    sio.start_background_task(background_thread)
    pywsgi.WSGIServer(('0.0.0.0', 5000), app,
                      handler_class = WebSocketHandler,
                      keyfile = os.environ.get('YADAGE_SSL_KEY','server.key'),
                      certfile = os.environ.get('YADAGE_SSL_CERT','server.crt')
                      ).serve_forever()
