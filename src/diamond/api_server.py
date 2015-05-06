# coding=utf-8

import ast
import configobj
import logging
import json
from os import listdir, kill
from os.path import isdir, join, abspath
import signal

from diamond.utils.config import load_config
from flask import Flask, jsonify, request, abort

log = logging.getLogger('diamond')

ENABLE = 'enable'
DISABLE = 'disable'

class Collector(object):

    def __init__(self, name, config, enabled=False):
        self.name = name
        self.config = config
        self.enabled = enabled

    @staticmethod
    def from_request_json(request):
        # The request json should be in format:
        # {"enable"/"disable": [{"name": "someCollector",
        #                       "config": {"parameter1": "value",
        #                                  "parameter2": "value"}
        #                        },
        #                        ...]}
        collectors = []
        request = json.loads(request)
        if ENABLE in request:
            enable = True
            action = ENABLE
        elif DISABLE in request:
            enable = False
            action = DISABLE
        else:
            raise Exception("Invalid request %s" % (request))

        for c in request[action]:
            collectors.append(Collector(name=c['name'],
                                        config=c['config'],
                                        enabled=enable))
        return collectors


app = Flask('Diamond API Server')

config_file = None      # config file path
config = None           # config file object(configobj object)
manager_pid = None      # pid of the manager process, i.e. where
                        # diamond.server.Server.run() runs in
all_collectors = []     # all collectors installed


def start(config_file_path, main_process_pid):
    global config_file, config, manager_pid, all_collectors

    config_file = config_file_path
    config = load_config(config_file)

    manager_pid = main_process_pid

    # collector modules are organized as:
    #
    # collector_path
    # ├── cpu
    # │   └── cpu.py
    # └── memory
    #     └── memory.py
    #
    # And in cpu.py we have a class CPUCollector which inherits
    # diamond.collector.Collector
    collector_path = config['server']['collectors_path']
    collector_module_files = []
    try:
        collector_module_files = [join(collector_path, f, f+'.py') for f
                                  in listdir(collector_path) if
                                  isdir(join(collector_path, f))]
    except OSError:
        log.warning('collectors_path %s might not be configured properly.' %
                    collector_path)
    for file in collector_module_files:
        with open(file, 'r') as f:
            for p in ast.parse(f.read()).body:
                # check if is a class definition and is a subclass
                # of Collector
                try:
                    if isinstance(p, ast.ClassDef) and \
                            p.bases[0].attr == 'Collector':
                        all_collectors.append(p.name)
                except AttributeError as e:
                    log.debug('In file %s: %s' % (file, e))

    app.run(debug=True)

@app.route('/', methods=['GET'])
def hello():
    return jsonify({'hello': 'diamond'})

@app.route('/collector/enabled', methods=['GET'])
def show_enabled_collectors():
    enabled_collectors = []
    for collector, collector_config in config['collectors'].iteritems():
        if collector_config.get('enabled', False) is True:
            enabled_collectors.append(collector)
    return jsonify({'enabled_collectors': enabled_collectors})

@app.route('/collector/all', methods=['GET'])
def show_all_collectors():
    return jsonify({'installed_collectors': all_collectors})

def write_config(path, collector):
    path = abspath(path)
    config = configobj.ConfigObj(path)
    config['enabled'] = collector.enabled
    for k, v in collector.config.iteritems():
        config[k] = v
    config.write()

@app.route('/collector/enabled', methods=['POST', 'DELETE'])
def config_collectors():
    try:
        collectors = Collector.from_request_json(request.get_json())
    except Exception as e:
        log.warning('Bad request: ', e)
        abort(400)

    collectors_config_path = config['server']['collectors_config_path']
    enabled, disabled, not_installed = [], [], []
    for c in collectors:
        if c.name not in all_collectors:
            not_installed.append(c.name)
        else:
            path = join(collectors_config_path, c.name+'.conf')
            write_config(path, c)
            if c.enabled:
                enabled.append(c.name)
            else:
                disabled.append(c.name)
    global config
    config = load_config(config_file)
    # Send SIGHUP to manager process so it would reload config
    kill(manager_pid, signal.SIGHUP)

    return jsonify({'enabled': enabled,
                    'disabled': disabled,
                    'not_installed': not_installed})
