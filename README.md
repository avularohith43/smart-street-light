# Smart Street Light

The Flask dashboard supports simulation and can also communicate with Raspberry Pi GPIO hardware. The Pi sends its sensor readings to the web app and polls for the desired light state; it does not need to accept incoming internet connections.

For complete wiring, deployment, setup, and troubleshooting instructions, see [RASPBERRY_PI_GUIDE.md](RASPBERRY_PI_GUIDE.md).

## Deploy the web app

Deploy this repository to Render using the included `render.yaml` Blueprint. It installs dependencies and starts the app with Gunicorn on Render's assigned port. During setup, Render generates a private `DEVICE_API_KEY`; copy its value from the Render service's environment settings for the Pi configuration below.

After deployment, open the service's public URL and check that `<service-url>/healthz` returns `{"status":"ok"}`. The Raspberry Pi must use that exact public service URL, for example `https://your-service.onrender.com` (do not add `/api`).

## Run locally on a shared Wi-Fi/LAN

To connect without cloud deployment, run the app on a computer on the same network as the Pi:

```sh
python app.py
```

Find that computer's LAN IPv4 address, then use `http://<computer-lan-ip>:5000` as `SMART_STREETLIGHT_URL` on the Pi. Do not use `localhost` or `127.0.0.1` on the Pi: those addresses refer to the Pi itself. The computer's firewall must allow inbound TCP port 5000 from the local network. Set `DEVICE_API_KEY` to the same private value in the app's environment before starting it.

## Raspberry Pi setup

By default, connect the LDR module's digital output to GPIO 17, the PIR output to GPIO 27, and the light/LED driver input to GPIO 22. Use a suitable resistor/driver for the light; never connect a street-light load directly to a GPIO pin. Sensor outputs must use 3.3 V logic. Change the pin environment variables if your wiring differs.

Install the Pi dependencies and configure the URL and shared key:

```sh
python3 -m pip install requests gpiozero
export SMART_STREETLIGHT_URL="https://your-service.onrender.com"
export DEVICE_API_KEY="the-same-private-key-as-the-web-service"
python3 raspberry_pi.py
```

The Pi checks `/healthz` at startup before accessing the GPIO pins. If it cannot connect, verify the URL, that the service is running, and that the Pi has network access. You can test the URL directly from the Pi with `curl -i "$SMART_STREETLIGHT_URL/healthz"`.

The LDR digital output is treated as HIGH in darkness by default; set `LDR_DARK_LEVEL=0` if the module reports LOW in darkness. Optional pin settings are `LDR_PIN`, `PIR_PIN`, and `LED_PIN`; `POLL_INTERVAL_SECONDS` defaults to `1`.

The Raspberry Pi posts readings to `POST /api/device/sensors` and polls `GET /api/device/state`. Both endpoints require the `X-Device-Key` header. The simulation controls and dashboard routes remain available.