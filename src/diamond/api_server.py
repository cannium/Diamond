from diamond.utils.config import load_config
from flask import Flask, jsonify

app = Flask('Diamond API Server')

config_file = None
enable_queue = None
disable_queue = None
config = None


@app.route('/', methods=['GET'])
def hello_world():
    return jsonify({'hello': 'diamond'})

@app.route('/collector', methods=['GET'])
def show_enabled_collectors():
    enabled_collectors = []
    for collector, collector_config in config['collectors'].iteritems():
        if config.get('enabled', False) is True:
            enabled_collectors.append(collector)
    return jsonify(enabled_collectors)

def start(config_file_path, collector_enable_queue, collector_disable_queue):
    global config_file, config, enable_queue, disable_queue
    config_file = config_file_path
    config = load_config(config_file)
    enable_queue = collector_enable_queue
    disable_queue = collector_disable_queue
    app.run(debug=True)

