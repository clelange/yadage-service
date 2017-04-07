from gevent import monkey
monkey.patch_all()

import socketio
import logging
import time
import msgpack
import json
from flask import Flask, render_template, request, jsonify
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

@app.route('/workflow_submit', methods=['POST'])
def sandbox_submit():
    data = request.json
    log.info('workflow submission requested with data %s', data)

    data['outputs'] = data['outputs'].split(',')
    spec = submission.submit_spec(**data)

    processing_id = wflowapi.workflow_submit(spec)
    return jsonify({'jobguid': processing_id})

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
    pywsgi.WSGIServer(('0.0.0.0', 5000), app, handler_class = WebSocketHandler).serve_forever()