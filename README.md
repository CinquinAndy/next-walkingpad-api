# WalkingPad REST Api
This application is connecting to the KingSmith WalkingPad via the [ph4-walkingpad controller](https://github.com/ph4r05/ph4-walkingpad). It was tested with the WalkingPad A1 but might work with other versions too.

Currently you can switch the modes of the pad (to Standby or Manual) and collect the data from the last session. The data includes the steps, time (in seconds) and distance (in km).
There is also a method to store the latest status read in a database. This was tested with a postgres database and the data is stored in a table with 4 columns:
- The current date (YYYY-MM-dd)
- Steps
- Distance
- Time

This can be used then as a source for visualizing, for example in a Grafana Dashboard.

The REST API can easily be extended, for more details on actions that can be done check the [ph4-walkingpad controller](https://github.com/ph4r05/ph4-walkingpad) repo.

## Limitations
Currently the REST API does not seem to work on OSX Monterrey. Check [this issue](https://github.com/huserben/walkingpad/issues/7#issuecomment-1019125291) for updates on the topic.

## Run Server
Install a venv:
`python -m venv venv`
Activate the venv:
`source venv/bin/activate` (Linux) or `venv\Scripts\activate` (Windows)
Install dependencies:
`pip install -r requirements.txt`

Create initial config by renaming the *sample_config.yaml* to *config.yaml*. (if you want to use the database functionality, 
make sure to add the database connection details to the config file and if you haven't the mac address of the WalkingPad, 
run the *scan.py* script to find it [see below](#connect-to-walkingpad))

Then run the application:
`python restserver.py`

## Connect to WalkingPad
You need bluetooth to connect to the WalkingPad, so make sure to execute the application on a device that supports bluetooth. If you have connected other devices (e.g. your smartphone) with the pad, make sure to disable bluetooth on this phone and restart the WalkingPad - once a device is paired you have to turn it off and on again that it can pair with a new device.

In order to connect to the WalkingPad you need to know the MacAddress of it. To figure this out just run the *scan.py* script. This will scan for nearby devices. You should see a device named "WalkingPad":

![Scanning for Devices](https://raw.githubusercontent.com/huserben/walkingpad/main/Images/scan.jpg)

The connection settings are read from a config file. Rename the existing *sample_config.yaml* to *config.yaml* and change the *address* to the Mac Address you just read.

## Testing Connection
Once you've added the proper mac address you can test out whether it works.
Execute a `POST` request to *http://<ServerIP>:5678/mode?new_mode=manual* - this should change the pad from Standby to Manual mode. To switch it back to standby, run *http://<ServerIP>:5678/mode?new_mode=standby*.

If the status is changing on your WalkingPad you're good to go.

## REST API Endpoints
# WalkingPad REST API

This application connects to the KingSmith WalkingPad via the [ph4-walkingpad controller](https://github.com/ph4r05/ph4-walkingpad). It was tested with the WalkingPad A1 but might work with other versions too.

## Available Endpoints

### Basic Controls
- `GET /status` - Get current pad status (speed, steps, distance, etc.)
- `GET /history` - Get data from the last session
- `POST /mode?new_mode=<mode>` - Change pad mode (standby/manual/auto)
- `POST /startwalk` - Start walking session
- `POST /finishwalk` - End walking session and save data
- `POST /save` - Save current session data manually

### Speed Control
- `POST /speed?speed=<speed>` - Change walking speed
  - Speed is in km/h × 10 (e.g., 30 = 3.0 km/h)
  - Valid range: 0-60 (0-6.0 km/h)
- `POST /stop` - Stop the walking pad immediately

### Preferences
- `POST /preferences` - Configure pad settings
  - `max_speed`: Maximum speed limit (10-60)
  - `start_speed`: Starting speed (10-30)
  - `sensitivity`: Sensitivity level (1=high, 2=medium, 3=low)
  - `child_lock`: Enable/disable child lock (true/false)
  - `units_miles`: Use miles instead of kilometers (true/false)

### Target Setting
- `POST /target` - Set exercise targets
  - `type`: Target type (0=none, 1=distance, 2=calories, 3=time)
  - `value`: Target value (distance in meters, calories in kcal, time in minutes)

### Maintenance
- `POST /calibrate` - Initiate pad calibration
  - Should be performed while pad is stopped
  - Helps maintain accurate speed readings

## Installation and Setup
[Previous installation instructions remain the same...]

## Example Usage

Start a walking session at 3.0 km/h:
```bash
# Start pad in manual mode
curl -X POST http://localhost:5678/mode?new_mode=manual

# Set speed to 3.0 km/h
curl -X POST http://localhost:5678/speed?speed=30

# Start the walking session
curl -X POST http://localhost:5678/startwalk
```

Configure pad preferences:
```bash
# Set maximum speed to 4.0 km/h and enable child lock
curl -X POST "http://localhost:5678/preferences?max_speed=40&child_lock=true"
```

Set a target:
```bash
# Set a target of 30 minutes
curl -X POST "http://localhost:5678/target?type=3&value=30"
```

## Notes
- All speed values are multiplied by 10 (e.g., 35 = 3.5 km/h)
- Always stop the pad before changing modes
- Allow a short delay between commands for reliable operation
- The pad must be in manual mode to change speed

## Error Handling
The API will return appropriate HTTP status codes:
- 200: Success
- 400: Invalid parameters
- 500: Server/device error

----
Todo : 
- [ ] add endpoints
  - [ ] change speed
  - [ ] stop the pad
- [ ] fix the code
- [ ] add cleaner readme