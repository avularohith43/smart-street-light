// =============================================================
// Smart Street Light System - Frontend JavaScript
// Talks to the Flask backend using fetch() and JSON.
// =============================================================

// How often (in milliseconds) the dashboard asks for new data
const REFRESH_INTERVAL_MS = 1000;

// ---------- Get all the HTML elements we need (by their IDs) ----------
const connectionStatus = document.getElementById("connection-status");
const connectionText = document.getElementById("connection-text");
const messageBox = document.getElementById("message");

const cardLightCondition = document.getElementById("card-light-condition");
const lightConditionIcon = document.getElementById("light-condition-icon");
const lightConditionValue = document.getElementById("light-condition-value");

const cardMotion = document.getElementById("card-motion");
const motionIcon = document.getElementById("motion-icon");
const motionValue = document.getElementById("motion-value");

const cardStreetLight = document.getElementById("card-street-light");
const bulb = document.getElementById("bulb");
const streetLightValue = document.getElementById("street-light-value");

const cardMode = document.getElementById("card-mode");
const modeIcon = document.getElementById("mode-icon");
const modeValue = document.getElementById("mode-value");

const btnAuto = document.getElementById("btn-auto");
const btnManual = document.getElementById("btn-manual");
const btnLightOn = document.getElementById("btn-light-on");
const btnLightOff = document.getElementById("btn-light-off");

const btnDay = document.getElementById("btn-day");
const btnNight = document.getElementById("btn-night");
const btnMotion = document.getElementById("btn-motion");
const btnNoMotion = document.getElementById("btn-no-motion");


// ---------- Helper functions ----------

// Send a request to the backend and return the JSON reply.
async function apiRequest(url, method, body) {
    const options = {
        method: method,
        headers: { "Content-Type": "application/json" },
    };
    if (body !== undefined) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    const data = await response.json();

    // If the server replied with an error (400, 409, ...), throw it
    if (!response.ok) {
        throw new Error(data.error || "Request failed.");
    }
    return data;
}

// Set the colour class of a card/badge (removes old state-... classes first)
function setState(element, newState) {
    const oldClasses = Array.from(element.classList).filter(function (name) {
        return name.startsWith("state-");
    });
    oldClasses.forEach(function (name) {
        element.classList.remove(name);
    });
    element.classList.add("state-" + newState);
}

// Show a message under the cards
function showMessage(text, type) {
    messageBox.textContent = text;
    messageBox.className = "message " + type;
}

// Show Online / Offline in the header
function setConnection(isOnline) {
    if (isOnline) {
        connectionStatus.className = "connection online";
        connectionText.textContent = "Server Online";
    } else {
        connectionStatus.className = "connection offline";
        connectionText.textContent = "Server Offline";
    }
}


// ---------- Update the whole dashboard from a status object ----------
function updateDashboard(status) {

    // 1. Light condition: DAY / NIGHT
    if (status.light_condition === "NIGHT") {
        lightConditionIcon.textContent = "🌙";
        lightConditionValue.textContent = "NIGHT";
        setState(cardLightCondition, "night");
        setState(lightConditionValue, "night");
    } else {
        lightConditionIcon.textContent = "☀️";
        lightConditionValue.textContent = "DAY";
        setState(cardLightCondition, "day");
        setState(lightConditionValue, "day");
    }

    // 2. Motion status
    if (status.motion_detected) {
        motionIcon.textContent = "🏃";
        motionValue.textContent = "MOTION DETECTED";
        setState(cardMotion, "motion");
        setState(motionValue, "motion");
    } else {
        motionIcon.textContent = "🚶";
        motionValue.textContent = "NO MOTION";
        setState(cardMotion, "nomotion");
        setState(motionValue, "nomotion");
    }

    // 3. Street light: ON / OFF
    if (status.street_light === "ON") {
        bulb.classList.add("on");
        streetLightValue.textContent = "ON";
        setState(cardStreetLight, "on");
        setState(streetLightValue, "on");
    } else {
        bulb.classList.remove("on");
        streetLightValue.textContent = "OFF";
        setState(cardStreetLight, "off");
        setState(streetLightValue, "off");
    }

    // 4. Operating mode: AUTO / MANUAL
    if (status.mode === "MANUAL") {
        modeIcon.textContent = "🖐️";
        modeValue.textContent = "MANUAL";
        setState(cardMode, "manual");
        setState(modeValue, "manual");
    } else {
        modeIcon.textContent = "🤖";
        modeValue.textContent = "AUTO";
        setState(cardMode, "auto");
        setState(modeValue, "auto");
    }

    // 5. Highlight the selected buttons
    btnAuto.classList.toggle("active", status.mode === "AUTO");
    btnManual.classList.toggle("active", status.mode === "MANUAL");

    btnDay.classList.toggle("active", status.light_condition === "DAY");
    btnNight.classList.toggle("active", status.light_condition === "NIGHT");

    btnMotion.classList.toggle("active", status.motion_detected === true);
    btnNoMotion.classList.toggle("active", status.motion_detected === false);

    btnLightOn.classList.toggle("active", status.mode === "MANUAL" && status.street_light === "ON");
    btnLightOff.classList.toggle("active", status.mode === "MANUAL" && status.street_light === "OFF");

    // 6. LIGHT ON / LIGHT OFF only work in MANUAL mode
    const isManual = status.mode === "MANUAL";
    btnLightOn.disabled = !isManual;
    btnLightOff.disabled = !isManual;
}


// ---------- Get the latest status (runs every second) ----------
async function loadStatus() {
    try {
        const status = await apiRequest("/api/status", "GET");
        updateDashboard(status);
        setConnection(true);
    } catch (error) {
        setConnection(false);
    }
}


// ---------- Send a command (button click) ----------
async function sendCommand(url, body) {
    try {
        const data = await apiRequest(url, "POST", body);
        updateDashboard(data.status);   // show the new state immediately
        setConnection(true);
        showMessage(data.message, "success");
    } catch (error) {
        showMessage("⚠️ " + error.message, "error");
    }
}


// ---------- Connect buttons to the API ----------

// Mode buttons
btnAuto.addEventListener("click", function () {
    sendCommand("/api/mode", { mode: "AUTO" });
});
btnManual.addEventListener("click", function () {
    sendCommand("/api/mode", { mode: "MANUAL" });
});

// Manual light buttons
btnLightOn.addEventListener("click", function () {
    sendCommand("/api/light/on");
});
btnLightOff.addEventListener("click", function () {
    sendCommand("/api/light/off");
});

// Simulation buttons
btnDay.addEventListener("click", function () {
    sendCommand("/api/simulation/light", { light_condition: "DAY" });
});
btnNight.addEventListener("click", function () {
    sendCommand("/api/simulation/light", { light_condition: "NIGHT" });
});
btnMotion.addEventListener("click", function () {
    sendCommand("/api/simulation/motion", { motion_detected: true });
});
btnNoMotion.addEventListener("click", function () {
    sendCommand("/api/simulation/motion", { motion_detected: false });
});


// ---------- Start the live dashboard ----------
loadStatus();                                   // load once immediately
setInterval(loadStatus, REFRESH_INTERVAL_MS);   // then repeat every second
