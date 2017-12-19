import hashlib
import uuid
import base64
from datetime import datetime
import json

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class YadageServiceWorkflow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    wflow_id   = db.Column(db.String(36), unique=True, nullable=False)
    result_dir = db.Column(db.String(), nullable=False)
    sub_date = db.Column(db.DateTime, nullable=False,default=datetime.utcnow)
    user_id  = db.Column(db.Integer, db.ForeignKey('yadage_service_user.id'),nullable=False)
    detail_data = db.Column(db.JSON(), nullable=False, default = {})
    submission_data = db.Column(db.JSON(), nullable=False, default = {})


class YadageServiceUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first = db.Column(db.String(), nullable=True)
    last = db.Column(db.String(), nullable=True)
    user = db.Column(db.String(), nullable=False)
    expt = db.Column(db.String(), nullable=False)
    api_keys = db.relationship('YadageServiceAPIKey', backref='user', lazy=True)
    wflow_submissions = db.relationship('YadageServiceWorkflow', backref='user', lazy=True)

class YadageServiceAPIKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('yadage_service_user.id'),nullable=False)

def register_user(user,b64data):
    user_data = json.loads(base64.b64decode(b64data))
    user = YadageServiceUser(**user_data)
    db.session.add(user)
    db.session.commit()

def user_data(user):
    user = YadageServiceUser.query.filter_by(user=user).first()
    if not user: return
    return {
        'first': user.first,
        'expt': user.expt,
        'last': user.last,
        'user': user.user
    }

def generate_apikey(username):
    apikey = hashlib.sha1(str(uuid.uuid4())).hexdigest()
    user = YadageServiceUser.query.filter_by(user=username).first()
    if not user:
        raise RuntimeError('unknown user requested API key')

    key = YadageServiceAPIKey(key=apikey, user = user)
    user.api_keys.append(key)
    db.session.add(user)
    db.session.add(key)
    db.session.commit()
    return key.key

def apikeys(username):
    user = YadageServiceUser.query.filter_by(user=username).first()
    if not user:
        raise RuntimeError('unknown user requested API key')
    return [k.key for k in user.api_keys]

def apikey_user(apikey):
    key = YadageServiceAPIKey.query.filter_by(key=apikey).first()
    return key.user.user
