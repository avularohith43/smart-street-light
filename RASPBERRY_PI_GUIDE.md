# Raspberry Pi Connection Guide

This guide connects the Smart Street Light web dashboard to a Raspberry Pi
running the project's `raspberry_pi.py` bridge. The Pi reads the LDR and PIR
sensors, sends their readings to the web app, and polls the app for the light
state. The Pi makes outbound network requests; it does not need to accept
incoming internet connections.

## What you need

- A Raspberry Pi running Raspberry Pi OS, with network access.
- An LDR module with a digital output (DO) and a PIR motion sensor.
- A low-voltage LED for a bench test, or a suitable driver/relay for a lamp.
- Jumper wires and a breadboard.
- The Smart Street Light project files.

Do not connect a mains-powered or high-current street light directly to a
Raspberry Pi GPIO pin. Use an appropriately rated, isolated driver and get
qualified help with mains wiring. Raspberry Pi GPIO is 3.3 V logic and is not
5 V tolerant. Check each sensor's specifications before wiring it.

## 1. Wire the sensors and test light

The defaults in `raspberry_pi.py` use BCM GPIO numbering:

| Device connection | Raspberry Pi signal | Physical header pin |
| --- | --- | --- |
| LDR module digital output (DO) | GPIO 17 | Pin 11 |
| PIR sensor output (OUT) | GPIO 27 | Pin 13 |
| LED/driver control input | GPIO 22 | Pin 15 |
| Sensor and driver ground | GND | For example, pin 6 |

Connect each sensor's ground to a Pi GND pin. Power the sensors only at a
voltage supported by both the sensor and its output interface; make sure the
signal sent to each GPIO is no higher than 3.3 V. For a small test LED, use a
current-limiting resistor and an appropriate transistor/driver rather than
powering it directly from a GPIO. Follow the driver's wiring and isolation
requirements for any larger light.

The LDR module must provide a digital output. The bridge interprets a HIGH
output as darkness by default. If your module outputs LOW in darkness, set
`LDR_DARK_LEVEL=0` in step 3. The bridge uses gpiozero's default pin numbering,
which is BCM.

## 2. Make the web app available

Choose one of these options:

### Option A: Deploy the web app to Render

1. Deploy this repository to Render using its included `render.yaml` Blueprint.
2. In the Render service's environment settings, find the generated
   `DEVICE_API_KEY`. Keep it private; you will enter the same value on the Pi.
3. Copy the service's public base URL, for example
   `https://your-service.onrender.com`. Do not append `/api`.
4. Check that `https://your-service.onrender.com/healthz` returns
   `{"status":"ok"}`.

### Option B: Run the web app on a computer on the same LAN

1. On the computer hosting the app, set `DEVICE_API_KEY` to a private key and
   start the app with `python app.py`.
2. Find that computer's LAN IPv4 address and use
   `http://<computer-lan-ip>:5000` as the Pi's base URL. Do not use
   `localhost` or `127.0.0.1` on the Pi; those addresses point back to the Pi.
3. Allow inbound TCP port 5000 through the host computer's firewall for your
   local network only.
4. From the Pi, verify the connection with
   `curl -i http://<computer-lan-ip>:5000/healthz`.

For example, set the host's key before launching the app in a Linux/macOS
terminal:

```sh
export DEVICE_API_KEY="replace-with-a-long-private-value"
python app.py
```

## 3. Install the bridge on the Pi

Copy or clone the project onto the Pi. If you are cloning it, install Git first
if needed, then run:

```sh
git clone <repository-url>
cd SmartStreetLight
```

Install the bridge dependencies. On Raspberry Pi OS, the OS packages work with
the system Python and avoid installing packages into a system-managed Python:

```sh
sudo apt update
sudo apt install -y python3-gpiozero python3-requests
```

Confirm that the script is present:

```sh
ls raspberry_pi.py
```

## 4. Configure the URL and shared key

In the same Pi terminal, set the base URL from step 2 and the exact same
`DEVICE_API_KEY` value configured on the web app:

```sh
export SMART_STREETLIGHT_URL="https://your-service.onrender.com"
export DEVICE_API_KEY="the-same-private-key-as-the-web-service"
```

For a LAN deployment, replace the URL with
`http://<computer-lan-ip>:5000`. Never commit the key to source control or put
it in a public file. These `export` settings last only for the current terminal
session.

Optional settings can be changed in the same way before starting the script:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LDR_PIN` | `17` | BCM GPIO pin connected to the LDR digital output |
| `PIR_PIN` | `27` | BCM GPIO pin connected to the PIR output |
| `LED_PIN` | `22` | BCM GPIO pin connected to the light driver input |
| `LDR_DARK_LEVEL` | `1` | Set to `0` if the LDR output is LOW in darkness |
| `POLL_INTERVAL_SECONDS` | `1` | Delay between successful sensor updates |

For example, to change the LDR polarity and poll every two seconds:

```sh
export LDR_DARK_LEVEL="0"
export POLL_INTERVAL_SECONDS="2"
```

## 5. Start the Pi bridge

From the project directory on the Pi, run:

```sh
python3 raspberry_pi.py
```

The bridge checks `/healthz` before opening GPIO devices. Once connected, it
repeatedly posts sensor readings to `POST /api/device/sensors`, then retrieves
the requested light state from `GET /api/device/state`. Both device endpoints
require the `X-Device-Key` header, which the bridge sets from
`DEVICE_API_KEY`. Keep the process running while the hardware is in use. Press
Ctrl+C to stop it.

## 6. Verify operation

1. Open the web app dashboard and select **AUTO** mode.
2. Cover the LDR or adjust the lighting so its digital output indicates
   darkness. Trigger the PIR sensor.
3. Confirm the dashboard shows **NIGHT** and motion detected. In AUTO mode,
   the light state should become **ON** while it is dark and motion is
   detected.
4. Stop triggering the PIR sensor or expose the LDR to light; confirm the
   light state becomes **OFF**.
5. Select **MANUAL** mode on the dashboard and use its light controls. The Pi
   polls the returned state and drives the GPIO output accordingly.

The API stores state in the web app process's memory. For this deployment,
keep the app running as a single instance if consistent device state is
required.

## Troubleshooting

- **Startup says the URL is missing or invalid:** Set
  `SMART_STREETLIGHT_URL` to the complete `http://` or `https://` base URL,
  without `/api`.
- **Startup cannot reach `/healthz`:** From the Pi, run
  `curl -i "$SMART_STREETLIGHT_URL/healthz"`. Check the service status, Pi
  network access, LAN IP, firewall, and URL.
- **API returns unauthorized:** Ensure `DEVICE_API_KEY` on the Pi exactly
  matches the web service setting. Restart the app if you changed its
  environment variable.
- **GPIO permission or pin error:** Check that the script runs on the Pi,
  that sensor wires use BCM GPIO 17 and 27 by default, and that no other
  process is using those pins.
- **Day/night appears inverted:** Set `LDR_DARK_LEVEL` to `0` or `1` to match
  the LDR module's actual digital output in darkness.
- **Light output does not change:** Confirm dashboard mode and state first,
  then check the driver input wiring and active polarity. Some driver boards
  are active-low and may need a suitable interface or code adjustment.
- **Sensor values are unstable:** Verify shared ground, sensor supply voltage,
  output logic levels, and wiring. Use sensor-module guidance for calibration
  and warm-up behavior.

See `README.md` for the shorter project overview and deployment notes.
