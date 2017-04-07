import os
import uuid

# {
#   'wflowname': 'check', 
#   'workflow': 'madgraph_delphes.yml',
#   'toplevel': 'from-github/phenochain',
#   'outputs': 'delphes/output.lhco', 
#   'inputURL': u'',
#   'preset_pars': {'nevents': 100}
# }


def submit_spec(wflowname, workflow, toplevel, outputs, inputURL, preset_pars):
    uniqstub = str(uuid.uuid4()).split('-')[-1]
    return  {
        'wflowtype': 'yadage',
        'wflowconfigname': wflowname,
        'workflow': workflow,
        'toplevel': toplevel,
        'resultlist': ['_adage', '_yadage', '**/*.log'] + outputs,
        'inputURL': inputURL,
        'fixed_pars': preset_pars,
        'shipout_spec': {
            'host': os.environ['YADAGE_SHIPTARGET_HOST'],
            'location': os.path.join(os.environ['YADAGE_RESULTBASE'],uniqstub,wflowname),
            'user': os.environ['YADAGE_SHIPTARGET_USER'],
            'port': os.environ['YADAGE_SHIPTARGET_PORT']
        },
        'queue': os.environ['YADAGE_WORKFLOW_QUEUE'],
    }
