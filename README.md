# WalkingPad API

A Flask-based REST API for controlling and managing KingSmith WalkingPad devices. This application provides a comprehensive interface for device control, exercise tracking, and data management.

## Features

### Device Control
- Real-time device status monitoring
- Speed and mode control (Manual/Auto)
- Device calibration and preferences
- Bluetooth connection management

### Exercise Tracking
- Session management (start/stop/pause)
- Real-time statistics (speed, distance, steps)
- Historical data recording
- Progress analytics

### Goal Management
- Custom exercise targets
- Progress tracking
- Achievement system
- Activity streaks

### Data Management
- PostgreSQL database integration
- Exercise history
- User preferences
- Device settings

## Project Structure

```
walkingpad/
├── api/
│   ├── controllers/      # Route handlers
│   ├── models/          # Data models
│   ├── services/        # Business logic
│   ├── utils/           # Helper functions
│   └── config/          # Configuration
├── scripts/             # Utility scripts
├── logs/                # Application logs
├── tests/               # Test suites
└── docs/                # Documentation
```

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Bluetooth support
- pip and virtualenv

## Installation

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create configuration:
```bash
cp config.sample.yaml config.yaml
# Edit config.yaml with your settings
```

4. Set up the database:
```bash
python scripts/setup_db.py
```

## Configuration

Create a `.env` file in the project root:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=walkingpad
DB_USER=your_user
DB_PASSWORD=your_password
DEVICE_ADDRESS=XX:XX:XX:XX:XX:XX
```

## Device Connection

1. Scan for WalkingPad devices:
```bash
python scripts/scan.py
```

2. Note the MAC address and update your configuration

3. Test the connection:
```bash
python scripts/test_connection.py
```

## Running the Server

Start the API server:
```bash
python app.py
```

The server will start on `http://localhost:5678` by default.

## API Documentation

### Device Control

#### Get Status
```http
GET /api/device/status
```

#### Change Mode
```http
POST /api/device/mode?new_mode=manual
```
Modes: `standby`, `manual`, `auto`

#### Set Speed
```http
POST /api/device/speed?speed=30
```
Speed is in km/h × 10 (e.g., 30 = 3.0 km/h)

### Exercise Sessions

#### Start Session
```http
POST /api/exercise/start
```

#### End Session
```http
POST /api/exercise/end
```

#### Get History
```http
GET /api/exercise/history?page=1&per_page=10
```

### Settings & Preferences

#### Update Preferences
```http
POST /api/settings/preferences
```
Parameters:
- `max_speed`: Maximum speed limit (10-60)
- `start_speed`: Starting speed (10-30)
- `sensitivity`: Sensitivity level (1=high, 2=medium, 3=low)
- `child_lock`: Enable/disable child lock (true/false)
- `units_miles`: Use miles instead of kilometers (true/false)

### Targets & Goals

#### Set Target
```http
POST /api/targets
Content-Type: application/json

{
    "type": "distance",
    "value": 5.0,
    "end_date": "2024-12-31"
}
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black api/
pylint api/
```

### Debugging
Logs are stored in `logs/` directory with daily rotation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Troubleshooting

### Common Issues

1. **Bluetooth Connection**
   - Ensure Bluetooth is enabled
   - Check device pairing status
   - Verify MAC address format

2. **Database Connection**
   - Check PostgreSQL service status
   - Verify connection credentials
   - Ensure database exists

3. **Device Communication**
   - Reset WalkingPad if unresponsive
   - Check Bluetooth signal strength
   - Verify device firmware version

## License

[MIT License](LICENSE)

## Acknowledgments

- [ph4-walkingpad](https://github.com/ph4r05/ph4-walkingpad) for the base controller
- [KingSmith](https://www.kingsmith.com/) for the WalkingPad device


----
# Todo
- Add a check on the device if an exercise was not saved, before start a new one (start session)
