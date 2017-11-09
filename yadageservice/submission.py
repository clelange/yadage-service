import os
import uuid

def yadage_loading_spec(request_json):
    return {
        'wflowtype': 'yadage',
        'workflow': request_json['workflow'],
        'toplevel': request_json['toplevel'],
        'fixed_pars': request_json['preset_pars']
    }

def submit_spec(request_json):
    uniqstub = str(uuid.uuid4()).split('-')[-1]

    spec = yadage_spec(request_json)
    common_pars = {
        'wflowconfigname': request_json['wflowname'],
        'shipout_spec': {
            'host': os.environ['YADAGE_SHIPTARGET_HOST'],
            'location': os.path.join(os.environ['YADAGE_RESULTBASE'],uniqstub,wflowname),
            'user': os.environ['YADAGE_SHIPTARGET_USER'],
            'port': os.environ['YADAGE_SHIPTARGET_PORT'],
        },
        'queue': os.environ['YADAGE_WORKFLOW_QUEUE'],
        'resultlist': ['_adage', '_yadage', '**/*.log'] + data['outputs'].split(','),
        'inputURL': request_json['inputURL'],
    }
    spec.update(**common_pars)
    return  spec
