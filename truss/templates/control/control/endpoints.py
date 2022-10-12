import requests
from flask import Blueprint, Response, current_app, jsonify, request
from requests.exceptions import ConnectionError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_fixed

INFERENCE_SERVER_START_WAIT_SECS = 60


control_app = Blueprint("control", __name__)


@control_app.route("/")
def index():
    return jsonify({})


@control_app.route("/v1/<path:path>", methods=["GET", "POST"])
def proxy(path):
    inference_server_port = current_app.config["inference_server_port"]

    # Wait a bit for inference server to start
    for attempt in Retrying(
        retry=retry_if_exception_type(ConnectionError),
        stop=stop_after_attempt(INFERENCE_SERVER_START_WAIT_SECS),
        wait=wait_fixed(1),
    ):
        with attempt:
            resp = requests.request(
                method=request.method,
                url=f"http://localhost:{inference_server_port}/v1/{path}",
                data=request.get_data(),
                cookies=request.cookies,
            )

    headers = [(name, value) for (name, value) in resp.raw.headers.items()]
    response = Response(resp.content, resp.status_code, headers)
    return response


@control_app.route("/control/patch", methods=["POST"])
def patch():
    current_app.logger.info("Patch request received.")
    patch_request = request.get_json()
    current_app.config["inference_server_controller"].apply_patch(patch_request)
    current_app.logger.info("Patch applied successfully")
    return {"msg": "Patch applied successfully"}


@control_app.route("/control/truss_hash", methods=["GET"])
def truss_hash():
    t_hash = current_app.config["inference_server_controller"].truss_hash()
    return {"result": t_hash}


@control_app.route("/control/restart_inference_server", methods=["POST"])
def restart_inference_server():
    current_app.config["inference_server_controller"].restart()

    return {"msg": "Inference server started successfully"}


@control_app.route("/control/stop_inference_server", methods=["POST"])
def stop_inference_server():
    current_app.config["inference_server_controller"].stop()
    return {"msg": "Inference server stopped successfully"}