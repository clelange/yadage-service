import os
import requests
from flask import redirect, url_for, session, request
from flask_oauth import OAuth
from flask_login import login_user, logout_user, login_required
import login as login_module

def user_data(access_token):
    r = requests.get(
        'https://oauthresource.web.cern.ch/api/Me',
        headers={'Authorization': 'Bearer {}'.format(access_token)}
    )
    return r.json()

def extract_user_info(userdata):
    userjson = {'experiment': 'unaffiliated', 'lastname': None, 'firstname': None}

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

oauth = OAuth()
oauth_app = oauth.remote_app('oauth_app',
                             base_url=None,
                             request_token_url=None,
                             access_token_url=os.environ['CERN_OAUTH_TOKENURL'],
                             authorize_url=os.environ[
                                 'CERN_OAUTH_AUTHORIZEURL'],
                             consumer_key=os.environ[
                                 'CERN_OAUTH_APPID'],
                             consumer_secret=os.environ[
                                 'CERN_OAUTH_SECRET'],
                             request_token_params={
                                 'response_type': 'code', 'scope': 'bio'},
                             access_token_params={
                                 'grant_type': 'authorization_code'},
                             access_token_method='POST'
                             )

def oauth_redirect(resp):
    next_url = request.args.get('next') or url_for('home')
    if resp is None:
        return redirect(next_url)

    data = user_data(resp['access_token'])
    data = extract_user_info(data)
    login_user(login_module.User(
        data['username'],
        data['firstname'],
        data['lastname'],
        data['experiment'],
    ))
    return redirect(next_url)

def login():
    redirect_uri = os.environ['CERN_OAUTH_BASEURL'] + url_for('oauth_redirect')
    return oauth_app.authorize(callback=redirect_uri)

def logout():
    logout_user()
    return redirect('/')

def init_app(app):
    login_module.login_manager.init_app(app)
    global oauth_redirect
    global login
    global logout
    oauth_redirect = oauth_app.authorized_handler(oauth_redirect)
    oauth_redirect = app.route(os.environ['CERN_OAUTH_REDIRECT_ROUTE'])(oauth_redirect)
    login  = app.route('/login')(login)
    logout = app.route('/logout')(logout)
