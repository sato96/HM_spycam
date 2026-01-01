import json, os
from src.logger_config import setup_logger
from flask import Flask
from src.CameraModule import spycam
from src.WsCam import init_routes

def create_app(config_path=None):
    # default path project_root/config/config.json
    if config_path is None:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        config_path = os.path.join(project_root, 'config', 'config.json')

    try:
        with open(config_path) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

    service = cfg.get('service', 'cameraModule')
    port = int(os.environ.get('PORT', cfg.get('port', 5004)))

    logger = setup_logger()

    app = Flask('Cam')
    app.config['SERVICE'] = service
    app.config['PORT'] = port

    cam = spycam()

    app.extensions = getattr(app, 'extensions', {})
    app.extensions['cam'] = cam

    init_routes(app, cam, logger)
    return app