from flask import Flask, request
from ph4_walkingpad import pad
from ph4_walkingpad.pad import WalkingPad, Controller
from ph4_walkingpad.utils import setup_logging
import asyncio
import yaml
import psycopg2
from datetime import date

app = Flask(__name__)

# minimal_cmd_space does not exist in the version we use from pip, thus we define it here.
# This should be removed once we can take it from the controller
minimal_cmd_space = 0.69

log = setup_logging()
pad.logger = log
ctler = Controller()

last_status = {
    "steps": None,
    "distance": None,
    "time": None
}


def on_new_status(sender, record):

    distance_in_km = record.dist / 100
    print("Received Record:")
    print('Distance: {0}km'.format(distance_in_km))
    print('Time: {0} seconds'.format(record.time))
    print('Steps: {0}'.format(record.steps))

    last_status['steps'] = record.steps
    last_status['distance'] = distance_in_km
    last_status['time'] = record.time


def store_in_db(steps, distance_in_km, duration_in_seconds):
    db_config = load_config()['database']
    if not db_config['host']:
        return

    try:
        conn = psycopg2.connect(host=db_config['host'], port=db_config['port'],
                                dbname=db_config['dbname'], user=db_config['user'], password=db_config['password'])
        cur = conn.cursor()

        date_today = date.today().strftime("%Y-%m-%d")
        # default data to test purpose
        duration = int(duration_in_seconds / 60)

        cur.execute("INSERT INTO exercise VALUES ('{0}', {1}, {2}, {3})".format(
            date_today, steps, duration, distance_in_km))
        conn.commit()

    finally:
        cur.close()
        conn.close()


def load_config():
    with open("config.yaml", 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)


def save_config(config):
    with open('config.yaml', 'w') as outfile:
        yaml.dump(config, outfile, default_flow_style=False)


async def connect():
    address = load_config()['address']
    print("Connecting to {0}".format(address))
    await ctler.run(address)
    await asyncio.sleep(minimal_cmd_space)


async def disconnect():
    await ctler.disconnect()
    await asyncio.sleep(minimal_cmd_space)


@app.route("/config/address", methods=['GET'])
def get_config_address():
    config = load_config()
    return str(config['address']), 200


@app.route("/config/address", methods=['POST'])
def set_config_address():
    address = request.args.get('address')
    config = load_config()
    config['address'] = address
    save_config(config)

    return get_config_address()


@app.route("/mode", methods=['GET'])
async def get_pad_mode():
    try:
        await connect()

        await ctler.ask_stats()
        await asyncio.sleep(minimal_cmd_space)
        stats = ctler.last_status
        mode = stats.manual_mode

        if (mode == WalkingPad.MODE_STANDBY):
            return "standby"
        elif (mode == WalkingPad.MODE_MANUAL):
            return "manual"
        elif (mode == WalkingPad.MODE_AUTOMAT):
            return "auto"
        else:
            return "Mode {0} not supported".format(mode), 400
    finally:
        await disconnect()

    return "Error", 500

@app.route("/mode", methods=['POST'])
async def change_pad_mode():
    new_mode = request.args.get('new_mode')
    print("Got mode {0}".format(new_mode))

    if (new_mode.lower() == "standby"):
        pad_mode = WalkingPad.MODE_STANDBY
    elif (new_mode.lower() == "manual"):
        pad_mode = WalkingPad.MODE_MANUAL
    elif (new_mode.lower() == "auto"):
        pad_mode = WalkingPad.MODE_AUTOMAT
    else:
        return "Mode {0} not supported".format(new_mode), 400

    try:
        await connect()

        await ctler.switch_mode(pad_mode)
        await asyncio.sleep(minimal_cmd_space)
    finally:
        await disconnect()

    return new_mode

@app.route("/status", methods=['GET'])
async def get_status():
    try:
        await connect()

        await ctler.ask_stats()
        await asyncio.sleep(minimal_cmd_space)
        stats = ctler.last_status
        mode = stats.manual_mode
        belt_state = stats.belt_state

        if (mode == WalkingPad.MODE_STANDBY):
            mode = "standby"
        elif (mode == WalkingPad.MODE_MANUAL):
            mode = "manual"
        elif (mode == WalkingPad.MODE_AUTOMAT):
            mode = "auto"

        if (belt_state == 5):
            belt_state = "standby"
        elif (belt_state == 0):
            belt_state = "idle"
        elif (belt_state == 1):
            belt_state = "running"
        elif (belt_state >=7):
            belt_state = "starting"

        dist = stats.dist / 100
        time = stats.time
        steps = stats.steps
        speed = stats.speed / 10

        return { "dist": dist, "time": time, "steps": steps, "speed": speed, "belt_state": belt_state }
    finally:
        await disconnect()


@app.route("/history", methods=['GET'])
async def get_history():
    try:
        await connect()

        await ctler.ask_hist(0)
        await asyncio.sleep(minimal_cmd_space)
    finally:
        await disconnect()

    return last_status

@app.route("/save", methods=['POST'])
def save():
    store_in_db(10, 25, 35)
    # store_in_db(last_status['steps'], last_status['distance'], last_status['time'])

@app.route("/startwalk", methods=['POST'])
async def start_walk():
    try:
        await connect()
        await ctler.switch_mode(WalkingPad.MODE_STANDBY) # Ensure we start from a known state, since start_belt is actually toggle_belt
        await asyncio.sleep(minimal_cmd_space)
        await ctler.switch_mode(WalkingPad.MODE_MANUAL)
        await asyncio.sleep(minimal_cmd_space)
        await ctler.start_belt()
        await asyncio.sleep(minimal_cmd_space)
        await ctler.ask_hist(0)
        await asyncio.sleep(minimal_cmd_space)
    finally:
        await disconnect()
    return last_status

@app.route("/finishwalk", methods=['POST'])
async def finish_walk():
    try:
        await connect()
        await ctler.switch_mode(WalkingPad.MODE_STANDBY)
        await asyncio.sleep(minimal_cmd_space)
        await ctler.ask_hist(0)
        await asyncio.sleep(minimal_cmd_space)
        store_in_db(last_status['steps'], last_status['distance'], last_status['time'])
    finally:
        await disconnect()

    return last_status


@app.route("/speed", methods=['POST'])
async def change_pad_speed():
    """Change the walking pad's speed.

    Query Parameters:
    - speed: Integer value representing speed in km/h multiplied by 10 (e.g., 30 = 3.0 km/h)

    Returns:
    - JSON object with the new speed value
    """
    try:
        speed = int(request.args.get('speed', 0))
        if speed < 0 or speed > 60:  # Maximum 6 km/h
            return "Speed must be between 0 and 60 (0-6.0 km/h)", 400

        await connect()
        await ctler.change_speed(speed)
        await asyncio.sleep(minimal_cmd_space)

        return {"speed": speed / 10}
    finally:
        await disconnect()


@app.route("/stop", methods=['POST'])
async def stop_pad():
    """Stop the walking pad immediately.

    Returns:
    - Success message
    """
    try:
        await connect()
        await ctler.stop_belt()
        await asyncio.sleep(minimal_cmd_space)
        return {"message": "Walking pad stopped successfully"}
    finally:
        await disconnect()


@app.route("/preferences", methods=['POST'])
async def set_preferences():
    """Set various walking pad preferences.

    Query Parameters:
    - max_speed: Maximum speed limit (10-60, representing 1.0-6.0 km/h)
    - start_speed: Starting speed (10-30, representing 1.0-3.0 km/h)
    - sensitivity: Sensitivity level (1=high, 2=medium, 3=low)
    - child_lock: Enable/disable child lock (true/false)
    - units_miles: Use miles instead of kilometers (true/false)

    Returns:
    - JSON object with updated preferences
    """
    try:
        await connect()
        updates = {}

        if 'max_speed' in request.args:
            speed = int(request.args.get('max_speed'))
            if 10 <= speed <= 60:
                await ctler.set_pref_max_speed(speed)
                updates['max_speed'] = speed / 10

        if 'start_speed' in request.args:
            speed = int(request.args.get('start_speed'))
            if 10 <= speed <= 30:
                await ctler.set_pref_start_speed(speed)
                updates['start_speed'] = speed / 10

        if 'sensitivity' in request.args:
            sensitivity = int(request.args.get('sensitivity'))
            if sensitivity in [1, 2, 3]:
                await ctler.set_pref_sensitivity(sensitivity)
                updates['sensitivity'] = sensitivity

        if 'child_lock' in request.args:
            child_lock = request.args.get('child_lock').lower() == 'true'
            await ctler.set_pref_child_lock(child_lock)
            updates['child_lock'] = child_lock

        if 'units_miles' in request.args:
            units_miles = request.args.get('units_miles').lower() == 'true'
            await ctler.set_pref_units_miles(units_miles)
            updates['units_miles'] = units_miles

        await asyncio.sleep(minimal_cmd_space)
        return updates

    finally:
        await disconnect()


@app.route("/target", methods=['POST'])
async def set_target():
    """Set a target for the walking session.

    Query Parameters:
    - type: Target type (0=none, 1=distance, 2=calories, 3=time)
    - value: Target value (distance in meters, calories in kcal, time in minutes)

    Returns:
    - JSON object with the set target
    """
    try:
        target_type = int(request.args.get('type', 0))
        target_value = int(request.args.get('value', 0))

        if target_type not in [WalkingPad.TARGET_NONE, WalkingPad.TARGET_DIST,
                               WalkingPad.TARGET_CAL, WalkingPad.TARGET_TIME]:
            return "Invalid target type", 400

        await connect()
        await ctler.set_pref_target(target_type, target_value)
        await asyncio.sleep(minimal_cmd_space)

        return {
            "target_type": target_type,
            "target_value": target_value
        }
    finally:
        await disconnect()


@app.route("/calibrate", methods=['POST'])
async def calibrate_pad():
    """Calibrate the walking pad. This should be done while the pad is stopped.

    Returns:
    - Success message
    """
    try:
        await connect()
        # Send calibration command (0x07)
        await ctler.cmd_162_3_7()
        await asyncio.sleep(minimal_cmd_space)
        return {"message": "Calibration initiated"}
    finally:
        await disconnect()

ctler.handler_last_status = on_new_status

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5678, processes=1, threaded=False)
