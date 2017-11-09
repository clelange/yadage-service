import os
import json
import base64
import database
from flask_login import LoginManager, UserMixin

class User(UserMixin):
    def __init__(self,user,first,last,expt):
        self.first = first
        self.last = last
        self.user = user
        self.experiment = expt
        if not database.user_data(self.user):
            database.register_user(self.user,self.get_id())

    def get_id(self):
        return base64.b64encode(json.dumps({
        'first':self.first,
        'last':self.last,
        'user':self.user,
        'expt':self.experiment
        },sort_keys=True))

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User(**json.loads(base64.b64decode(user_id)))

@login_manager.request_loader
def load_user_from_request(request):
    api_key = request.headers.get('Authorization')
    if api_key:
        api_key = api_key.replace('Bearer ', '', 1)
        user = database.apikey_user(api_key)
        if user:
            return User(**database.user_data(user))
