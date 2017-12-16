import os
import uuid

def yadage_spec(request_json):
    return {
        'wflowtype': 'yadage',
        'interactive': True if int(request_json['interactive']) else False,
        'workflow': request_json['workflow'],
        'toplevel': request_json['toplevel'],
        'fixed_pars': request_json['preset_pars'],
        'resultlist': ['_adage', '_yadage', '**/*.log'] + request_json['outputs'].split(','),
    }

def submit_spec(request_json):
    uniqstub = str(uuid.uuid4()).split('-')[-1]

    spec = yadage_spec(request_json)
    common_pars = {
        'wflowconfigname': request_json['wflowname'],
        'shipout_spec': {
            'host': os.environ['YADAGE_SHIPTARGET_HOST'],
            'location': os.path.join(os.environ['YADAGE_RESULTBASE'],uniqstub,request_json['wflowname']),
            'user': os.environ['YADAGE_SHIPTARGET_USER'],
            'port': os.environ['YADAGE_SHIPTARGET_PORT'],
        },
        'meta_details': request_json.get('meta_details',{}),
        'queue': os.environ['YADAGE_WORKFLOW_QUEUE'],
        'inputURL': request_json['archive'],
        'inputAuth': request_json.get('inputAuth',False),
    }
    spec.update(**common_pars)
    return  spec
