"""Bridge Raspberry Pi GPIO sensors and light to the deployed Flask API."""

import os
import time
from urllib.parse import urlsplit

import requests
from gpiozero import DigitalInputDevice, LED


BASE_URL = os.environ.get("SMART_STREETLIGHT_URL", "").strip().rstrip("/")
DEVICE_KEY = os.environ.get("DEVICE_API_KEY", "").strip()
LDR_PIN = int(os.environ.get("LDR_PIN", "17"))
PIR_PIN = int(os.environ.get("PIR_PIN", "27"))
LED_PIN = int(os.environ.get("LED_PIN", "22"))
LDR_DARK_LEVEL = bool(int(os.environ.get("LDR_DARK_LEVEL", "1")))
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "1"))

if not BASE_URL:
    raise SystemExit("Set SMART_STREETLIGHT_URL to the deployed app URL or the computer's LAN URL.")
parsed_url = urlsplit(BASE_URL)
if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
    raise SystemExit("SMART_STREETLIGHT_URL must be a full http:// or https:// URL.")
if not DEVICE_KEY:
    raise SystemExit("Set DEVICE_API_KEY to the same private key configured for the web service.")
if POLL_INTERVAL_SECONDS <= 0:
    raise SystemExit("POLL_INTERVAL_SECONDS must be greater than zero.")

session = requests.Session()
session.headers.update({"X-Device-Key": DEVICE_KEY})

for attempt in range(5):
    try:
        response = session.get(BASE_URL + "/healthz", timeout=10)
        response.raise_for_status()
        health = response.json()
        if not isinstance(health, dict) or health.get("status") != "ok":
            raise ValueError("Unexpected response from /healthz.")
        print("Connected to Smart Street Light API:", BASE_URL)
        break
    except (requests.RequestException, ValueError) as error:
        if attempt == 4:
            print("Could not reach Smart Street Light API at", BASE_URL)
            print("Check that the URL is correct, the service is running, and the Pi has network access.")
            raise SystemExit(str(error)) from error
        print("API not ready; retrying connection:", error)
        time.sleep(5)

with DigitalInputDevice(LDR_PIN, pull_up=False) as light_sensor, \
        DigitalInputDevice(PIR_PIN, pull_up=False) as motion_sensor, \
        LED(LED_PIN) as street_light:
    while True:
        light_level = bool(light_sensor.value)
        payload = {
            "light_condition": "NIGHT" if light_level == LDR_DARK_LEVEL else "DAY",
            "motion_detected": motion_sensor.is_active,
        }

        try:
            response = session.post(
                BASE_URL + "/api/device/sensors", json=payload, timeout=5
            )
            response.raise_for_status()

            response = session.get(BASE_URL + "/api/device/state", timeout=5)
            response.raise_for_status()
            state_response = response.json()
            state = state_response.get("status") if isinstance(state_response, dict) else None
            if not isinstance(state, dict) or state.get("street_light") not in ("ON", "OFF"):
                raise ValueError("Invalid device state returned by the API.")
            light_is_on = state["street_light"] == "ON"
            street_light.value = light_is_on
            time.sleep(POLL_INTERVAL_SECONDS)
        except (requests.RequestException, ValueError) as error:
            print("Smart Street Light API unavailable:", error)
            street_light.off()
            time.sleep(5)