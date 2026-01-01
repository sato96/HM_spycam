import base64, json, threading, logging
from io import BytesIO
from flask import request
from HM_response import MsgResponse

def init_routes(app, cam, logger=None):
    logger = logger or logging.getLogger(__name__)

    @app.route('/')
    def hello_world():
        return 'Hello from Flask!!'

    @app.route('/pic', methods=['GET'])
    def pic():
        try:
            image = cam.pic()
            buf = BytesIO()
            image.save(buf, 'JPEG')
            img_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
            code = 200
            r = MsgResponse('ok', data={}, img_base64=img_b64, status_code=code)
        except Exception as e:
            logger.error(e)
            r = MsgResponse('ko', data={}, response='Error ' + str(e), status_code=500)
        return r.flask_response()

    @app.route('/parameters', methods=['GET'])
    def parameters():
        code = 200
        status = 'ok'
        try:
            resp = cam.getConfig()
        except Exception as e:
            logger.error(e)
            code = 500
            resp = 'Error ' + str(e)
            status = 'ko'
        return MsgResponse(status, data = {}, response=resp, status_code=code).flask_response()


    @app.route('/start', methods=['POST'])
    def start():
        code = 200
        try:

            t0 = threading.Thread(target=cam.start)
            t0.start()
            resp = 'ok'
            status = 'ok'
        except Exception as e:
            logger.error(e)
            code = 500
            resp = 'Error ' + str(e)
            status = 'ko'
        r = MsgResponse(status, data = {}, response=resp, status_code=code)
        print(r.dict())
        print(r.status_code)
        return r.flask_response()


    @app.route('/stop', methods=['POST', 'GET'])
    def stop():
        code = 200
        try:

            cam.stop()
            resp = 'ok'
            status = 'ok'
        except Exception as e:
            logger.error(e)
            code = 500
            resp = 'Error ' + str(e)
            status = 'ko'
        return MsgResponse(status, data = {}, response=resp, status_code=code).flask_response()


    @app.route('/tresh', methods=['POST'])
    def tresh():
        code = 200
        try:

            body = request.data
            dati = json.loads(body.decode('utf-8'))
            b = dati['threshold']
            cam.thresh = b
            resp = str(b)
            status = 'ok'
        except Exception as e:
            logger.error(e)
            code = 500
            resp = 'Error ' + str(e)
            status = 'ko'
        return MsgResponse(status, data = {}, response=resp, status_code=code).flask_response()


    @app.route('/reload', methods=['POST'])
    def realod():
        code = 200
        try:
            cam.realodConfig()
            resp = 'ok'
            status = 'ok'
        except Exception as e:
            logger.error(e)
            code = 500
            resp = 'Error ' + str(e)
            status = 'ko'
        return MsgResponse(status, data = {}, response=resp, status_code=code).flask_response()
