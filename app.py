# =============================================================
# Smart Street Light System - Flask backend
# =============================================================
# This file has TWO separate parts:
#   PART 1: Sensor functions (simulated now, real Raspberry Pi later)
#   PART 2: Application logic + Flask API (does not change later)
#
# Later, only PART 1 needs to be replaced with real hardware code.
# =============================================================

import hmac
import os

from flask import Flask, jsonify, request, render_template
from werkzeug.exceptions import HTTPException

app = Flask(__name__)


# =============================================================
# PART 1: SENSOR LAYER (SIMULATED)
# =============================================================
# These variables pretend to be the sensors.
# The dashboard's "Simulation / Testing Controls" change them.

simulated_sensors = {
    "light_condition": "DAY",   # "DAY" or "NIGHT"  (LDR sensor later)
    "motion_detected": False,   # True or False     (PIR sensor later)
}


def read_light_condition():
    """Return 'DAY' or 'NIGHT'. Later: read the real LDR sensor here."""
    return simulated_sensors["light_condition"]


def read_motion_detected():
    """Return True/False. Later: read the real PIR sensor here."""
    return simulated_sensors["motion_detected"]


def write_street_light(is_on):
    """Switch the street light. Later: turn the real LED on/off here.
    For now it does nothing, because the light is only shown on screen."""
    pass


def set_simulated_light_condition(value):
    """Used only by the simulation controls. Remove when using real hardware."""
    simulated_sensors["light_condition"] = value


def set_simulated_motion(value):
    """Used only by the simulation controls. Remove when using real hardware."""
    simulated_sensors["motion_detected"] = value


# =============================================================
# PART 2: APPLICATION LOGIC
# =============================================================

# The state of the system (kept in memory, no database)
system_state = {
    "light_condition": "DAY",
    "motion_detected": False,
    "street_light": "OFF",   # "ON" or "OFF"
    "mode": "AUTO",          # "AUTO" or "MANUAL"
}


def update_system():
    """Read the sensors and update the street light.

    AUTO mode rules:
        DAY                  -> light OFF
        NIGHT + NO MOTION    -> light OFF
        NIGHT + MOTION       -> light ON

    MANUAL mode: the light is not changed here. Only the
    LIGHT ON / LIGHT OFF buttons change it.
    """
    # Always read the latest sensor values
    system_state["light_condition"] = read_light_condition()
    system_state["motion_detected"] = read_motion_detected()

    # Only apply the automatic rules in AUTO mode
    if system_state["mode"] == "AUTO":
        if system_state["light_condition"] == "NIGHT" and system_state["motion_detected"]:
            system_state["street_light"] = "ON"
        else:
            system_state["street_light"] = "OFF"

    # Send the result to the (future) real light
    write_street_light(system_state["street_light"] == "ON")


def get_status():
    """Update everything and return the current status as a dictionary."""
    update_system()
    return {
        "light_condition": system_state["light_condition"],
        "motion_detected": system_state["motion_detected"],
        "street_light": system_state["street_light"],
        "mode": system_state["mode"],
    }


def success_response(message):
    """Standard JSON reply for a successful POST request."""
    return jsonify({"success": True, "message": message, "status": get_status()})


def error_response(message, code=400):
    """Standard JSON reply when something is wrong."""
    return jsonify({"success": False, "error": message}), code


def get_json_data():
    """Read the JSON body of a request. Returns None if it is missing/invalid."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None
    return data


# =============================================================
# ROUTES (API)
# =============================================================

@app.route("/")
def home():
    """Show the dashboard page."""
    return render_template("index.html")


@app.route("/healthz", methods=["GET"])
def health_check():
    """Return a lightweight response that deployment platforms can probe."""
    return jsonify({"status": "ok"})


@app.route("/api/status", methods=["GET"])
def api_status():
    """Return the current status."""
    return jsonify(get_status())


@app.route("/api/simulation/light", methods=["POST"])
def api_simulation_light():
    """Change simulated light condition. Body: {"light_condition": "DAY"} or "NIGHT"."""
    data = get_json_data()
    if data is None:
        return error_response("Request body must be valid JSON.")

    value = data.get("light_condition")
    if not isinstance(value, str) or value.upper() not in ("DAY", "NIGHT"):
        return error_response("light_condition must be 'DAY' or 'NIGHT'.")

    set_simulated_light_condition(value.upper())
    return success_response("Simulated light condition set to " + value.upper() + ".")


@app.route("/api/simulation/motion", methods=["POST"])
def api_simulation_motion():
    """Change simulated motion. Body: {"motion_detected": true} or false."""
    data = get_json_data()
    if data is None:
        return error_response("Request body must be valid JSON.")

    value = data.get("motion_detected")
    if not isinstance(value, bool):
        return error_response("motion_detected must be true or false.")

    set_simulated_motion(value)
    if value:
        return success_response("Simulated motion: MOTION DETECTED.")
    return success_response("Simulated motion: NO MOTION.")


@app.route("/api/mode", methods=["POST"])
def api_mode():
    """Switch between AUTO and MANUAL. Body: {"mode": "AUTO"} or "MANUAL"."""
    data = get_json_data()
    if data is None:
        return error_response("Request body must be valid JSON.")

    value = data.get("mode")
    if not isinstance(value, str) or value.upper() not in ("AUTO", "MANUAL"):
        return error_response("mode must be 'AUTO' or 'MANUAL'.")

    system_state["mode"] = value.upper()
    return success_response("Operating mode set to " + value.upper() + ".")


@app.route("/api/light/on", methods=["POST"])
def api_light_on():
    """Turn the street light ON (manual mode only)."""
    if system_state["mode"] != "MANUAL":
        return error_response("Switch to MANUAL mode first.", 409)

    system_state["street_light"] = "ON"
    return success_response("Street light turned ON manually.")


@app.route("/api/light/off", methods=["POST"])
def api_light_off():
    """Turn the street light OFF (manual mode only)."""
    if system_state["mode"] != "MANUAL":
        return error_response("Switch to MANUAL mode first.", 409)

    system_state["street_light"] = "OFF"
    return success_response("Street light turned OFF manually.")


def authorize_device_request():
    """Require the shared device key for Raspberry Pi API calls."""
    device_key = os.environ.get("DEVICE_API_KEY")
    if not device_key:
        return error_response("Device API is not configured.", 503)

    supplied_key = request.headers.get("X-Device-Key", "")
    if not hmac.compare_digest(supplied_key, device_key):
        return error_response("Unauthorized device.", 401)
    return None


@app.route("/api/device/sensors", methods=["POST"])
def api_device_sensors():
    """Accept real sensor readings from the Raspberry Pi."""
    authorization_error = authorize_device_request()
    if authorization_error is not None:
        return authorization_error

    data = get_json_data()
    if data is None:
        return error_response("Request body must be valid JSON.")

    light_condition = data.get("light_condition")
    motion_detected = data.get("motion_detected")
    if not isinstance(light_condition, str) or light_condition.upper() not in ("DAY", "NIGHT"):
        return error_response("light_condition must be 'DAY' or 'NIGHT'.")
    if not isinstance(motion_detected, bool):
        return error_response("motion_detected must be true or false.")

    simulated_sensors["light_condition"] = light_condition.upper()
    simulated_sensors["motion_detected"] = motion_detected
    return jsonify({"success": True, "message": "Device sensors updated."})


@app.route("/api/device/state", methods=["GET"])
def api_device_state():
    """Return the computed light state for the Raspberry Pi to apply."""
    authorization_error = authorize_device_request()
    if authorization_error is not None:
        return authorization_error
    return jsonify({"status": get_status()})


# =============================================================
# ERROR HANDLERS (always reply with JSON, never crash)
# =============================================================

@app.errorhandler(HTTPException)
def handle_http_error(error):
    """Handles 404 (not found), 405 (wrong method), etc."""
    return jsonify({"success": False, "error": error.description}), error.code


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Handles any unexpected error so the server keeps running."""
    return jsonify({"success": False, "error": "Internal server error."}), 500


# =============================================================
# START THE SERVER
# =============================================================

if __name__ == "__main__":
    update_system()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
