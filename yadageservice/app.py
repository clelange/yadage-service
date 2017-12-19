from gevent import monkey
monkey.patch_all()

import socketio
import logging
import time
import os
import json
import click
import database

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, Response
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

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('YADAGE_JOBDB_URI','postgres://localhost')
database.db.init_app(app)



def background_thread():
    """Example of how to send server generated events to clients."""
    log.info('starting background thread')
    for msg in wflowapi.log_msg_stream():
        time.sleep(0.01)
        if msg['msg_type'] in ['wflow_log','wflow_state']:
            try:
                sio.emit('room_msg', msg, room=msg['wflowguid'], namespace='/wflow')
            except:
                log.exception('something went wrong in message handling')
                pass
        if msg['msg_type'] == 'simple_log':
            sio.emit('log_message', msg, room = msg['jobguid'], namespace = '/subjobmon')

############################################
############################################

import cern_oauth
cern_oauth.init_app(app)

############################################
############################################

@app.route('/workflow_submit', methods=['POST'])
@cern_oauth.login_required
def sandbox_submit():
    log.info('workflow submission requested with data %s', request.json)

    spec = submission.submit_spec(request.json)
    processing_id = wflowapi.workflow_submit(cern_oauth.current_user.user, spec, request.json)

    return jsonify({'jobguid': processing_id})

@app.route('/results/<workflow_id>')
@app.route('/results/<workflow_id>/<path:path>')
@cern_oauth.login_required
def results(workflow_id, path = "."):
    basepath = wflowapi.resultdir(workflow_id)
    basepath = basepath.split(os.environ['YADAGE_RESULTBASE'],1)[-1].strip('/')
    return redirect(url_for('autoindex', path = os.path.join(basepath,path)))

idx = AutoIndex(app, os.environ['YADAGE_RESULTBASE'], add_url_rules=False)
@app.route('/resultfiles')
@app.route('/resultfiles/<path:path>')
@cern_oauth.login_required
def autoindex(path='.'):
    return idx.render_autoindex(path)


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/examples')
def examples():
    return render_template('examples.html')


@app.route('/register', methods = ['POST'])
@cern_oauth.login_required
def register():
    database.generate_apikey(cern_oauth.current_user.user)
    return redirect(url_for('profile'))

@app.route('/profile')
@cern_oauth.login_required
def profile():
    apikeys = database.apikeys(cern_oauth.current_user.user)
    return render_template('profile.html',
        apikeys = apikeys,
        job_info = wflowapi.all_wflows(username = cern_oauth.current_user.user,
        details = True)
    )

@app.route('/submit')
@cern_oauth.login_required
def submit():
    presets = {}
    presets['toplevel'] = request.args.get('toplevel', None)
    presets['workflow'] = request.args.get('workflow', None)
    presets['outputs'] = request.args.get('outputs', None)
    presets['archive'] = request.args.get('archive', None)
    presets['pars'] = json.dumps(json.loads(request.args.get('pars', '{}')))
    presets = {k: v for k, v in presets.iteritems() if v is not None}
    return render_template('submit.html', presets = presets)

@app.route("/upload", methods=["POST"])
@cern_oauth.login_required
def upload():
    import uuid
    import werkzeug
    filename = str(uuid.uuid4()).replace('-','')
    log.warning('uploading!')

    full_path = os.path.join(os.environ['YADAGE_UPLOADBASE'],filename)


    def custom_stream_factory(total_content_length, filename, content_type, content_length=None):
        target_file = open(full_path,'wb')
        log.info("start receiving file ... filename => " + str(target_file))
        return target_file

    stream,form,files = werkzeug.formparser.parse_form_data(request.environ, stream_factory=custom_stream_factory)

    return jsonify({'file_id':filename})

@app.route("/workflow_input/<filename>", methods=["GET"])
@cern_oauth.login_required
def workfow_input(filename):
    return send_from_directory(os.environ['YADAGE_UPLOADBASE'],filename)


@app.route('/monitor/<identifier>')
@cern_oauth.login_required
def monitor(identifier):
    status = wflowapi.workflow_status([identifier])[0]
    return render_template('monitor.html', workflow_id=identifier, status = status)

@app.route('/subjob_monitor/<identifier>')
@cern_oauth.login_required
def subjob_monitor(identifier):
    return render_template('subjobmonitor.html', subjobid = identifier)

@app.route('/subjob_logs/<identifier>')
@cern_oauth.login_required
def subjob_logs(identifier):
    topic = request.args.get('topic', 'run')
    def generate():
        for msg in wflowapi.subjob_messages(identifier, topic = topic):
            yield json.dumps(msg) + '\n'
    return Response(generate(), mimetype='text/plain')

@app.route('/wflow_logs/<identifier>')
@cern_oauth.login_required
def wflow_logs(identifier):
    topic = request.args.get('topic', 'log')
    def generate():
        for msg in wflowapi.get_workflow_messages(identifier,topic = topic):
            yield json.dumps(msg) + '\n'
    return Response(generate(), mimetype='text/plain')

@app.route('/jobstatus/<identifier>')
@cern_oauth.login_required
def jobstatus(identifier):
    return jsonify(wflowapi.workflow_status([identifier])[0])

@app.route('/joboverview')
@cern_oauth.login_required
def joboverview():
    return render_template('joboverview.html', job_info = wflowapi.all_wflows(details = True))

## /subjobmon namespace

@sio.on('join', namespace='/subjobmon')
def enter_sub(sid,data):
    historical_data = wflowapi.subjob_messages(data['room'], topic = 'run')
    # for this session, emit historical data
    for msg in historical_data[-3000:]:
        sio.emit('log_message',msg, room = sid, namespace = '/subjobmon')

    #subscribe to any future updates
    sio.enter_room(sid, data['room'], namespace='/subjobmon')
    sio.emit('join_ack',{'data':'joined subjobmon room {}'.format(data['room'])}, room = data['room'], namespace = '/subjobmon')

@sio.on('connect', namespace='/wflow')
def connect(sid, environ):
    print('Client connected to /wflow')


@sio.on('join', namespace='/wflow')
def enter(sid, data):
    print('data', data)

    states = wflowapi.get_workflow_messages(data['room'],topic = 'state')
    try:
        sio.emit('room_msg', states[-1], room=sid, namespace='/wflow')
    except IndexError:
        pass

    stored_messages = wflowapi.get_workflow_messages(data['room'], topic = 'log')
    for msg in stored_messages:
        sio.emit('room_msg', msg, room=sid, namespace='/wflow')

    print('Adding Client {} to room {}'.format(sid, data['room']))
    sio.enter_room(sid, data['room'], namespace='/wflow')

@sio.on('roomit', namespace='/wflow')
def roomit(sid, data):
    print('Emitting to Room: {}'.format(data['room']))
    sio.emit('join_ack', {'data':'Welcome a new member to the room {}'.format(data['room'])}, room=data['room'], namespace='/wflow')

@sio.on('disconnect', namespace='/wflow')
def disconnect(sid):
    print('Client disconnected')




@click.group()
def cli():
    pass

@cli.command()
@click.option('--create', default = True)
@click.option('--startbgthread', default = True)
def run_server(create,startbgthread):
    if create:
        with app.app_context():
            database.db.create_all()

    if startbgthread:
        sio.start_background_task(background_thread)
    port = int(os.environ.get('YADAGE_PORT',5000))
    log.info('serving on %s', port)
    pywsgi.WSGIServer(('0.0.0.0', port), app,
                      handler_class = WebSocketHandler,
                      keyfile = os.environ.get('YADAGE_SSL_KEY','server.key'),
                      certfile = os.environ.get('YADAGE_SSL_CERT','server.crt')
                      ).serve_forever()

@cli.command()
@click.option('--recreate', default = True)
def drop_db(recreate):
    with app.app_context():
        database.db.drop_all()
        if recreate:
            database.db.create_all()


if __name__ == '__main__':
    cli()
