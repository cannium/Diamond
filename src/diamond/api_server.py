from diamond.utils.config import load_config
from flask import Flask, jsonify

app = Flask('Diamond API Server')

class DiamondAPI(object):
    def __init__(self, config_file, enable_queue, disable_queue):
        self.config_file = config_file
        self.config = load_config(self.config_file)
        self.enable_queue = enable_queue
        self.disable_queue = disable_queue
        app.run()

    @app.route('/', methods=['GET'])
    def hello_world(self):
        return jsonify({'hello': 'diamond'})

    @app.route('/collector', methods=['GET'])
    def show_enabled_collectors(self):
        enabled_collectors = []
        for collector, config in self.config['collectors'].iteritems():
            if config.get('enabled', False) is True:
                enabled_collectors.append(collector)
        return jsonify(enabled_collectors)
