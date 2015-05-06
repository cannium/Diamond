# coding=utf-8

import ast
import logging
from os import listdir
from os.path import isdir, join

from diamond.utils.config import load_config
from flask import Flask, jsonify

log = logging.getLogger('API server')

app = Flask('Diamond API Server')

config_file = None      # config file path
config = None           # config file object(configobj object)
enable_queue = None     # inter-process queue for enabling new collectors
disable_queue = None    # inter-process queue for disabling collectors
all_collectors = []     # all collectors installed


def start(config_file_path, collector_enable_queue, collector_disable_queue):
    global config_file, config, enable_queue, disable_queue, all_collectors

    config_file = config_file_path
    config = load_config(config_file)

    enable_queue = collector_enable_queue
    disable_queue = collector_disable_queue

    # collector modules are organized as:
    #
    # collector_path
    # ├── cpu
    # │   └── cpu.py
    # ├── memory
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
        log.warning('collectors_path %s might not be correct.' %
                    collector_path)
    for file in collector_module_files:
        with open(file, 'r') as f:
            for p in ast.parse(f.read()):
                # check if is a class definition and is a subclass
                # of Collector
                if isinstance(p, ast.ClassDef) and \
                        p.bases[0].attr == 'Collector':
                    all_collectors.append(p.name)

    app.run(debug=True)

@app.route('/', methods=['GET'])
def hello_world():
    return jsonify({'hello': 'diamond'})

@app.route('/collector', methods=['GET'])
def show_enabled_collectors():
    enabled_collectors = []
    for collector, collector_config in config['collectors'].iteritems():
        if collector_config.get('enabled', False) is True:
            enabled_collectors.append(collector)
    return jsonify({'enabled_collectors': enabled_collectors})

@app.route('/collector/all', methods=['GET'])
def show_all_collectors():
    return jsonify({'installed_collectors': all_collectors})


