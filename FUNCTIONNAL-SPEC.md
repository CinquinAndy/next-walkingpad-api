# WalkingPad API - Functional Specifications

## 1. API Endpoints

### Device Control `/api/device`

#### GET `/status`
Gets the current state of the WalkingPad.
```json
{
  "mode": "manual|auto|standby",
  "belt_state": "idle|running|starting|standby",
  "speed": 3.5,
  "distance": 1.2,
  "steps": 1500,
  "time": 600,
  "calories": 50,
  "connected": true
}
```

#### POST `/mode`
Changes the operating mode.
- Query params: `mode=manual|auto|standby`
```json
{
  "success": true,
  "mode": "manual"
}
```

#### POST `/speed`
Adjusts the belt speed.
- Query params: `speed=35` (3.5 km/h = 35)
```json
{
  "success": true,
  "current_speed": 3.5
}
```

#### POST `/start`
Starts the belt.
- Query params: `speed` (optional)
```json
{
  "success": true,
  "status": "running"
}
```

#### POST `/stop`
Stops the belt.
```json
{
  "success": true,
  "status": "stopped"
}
```

### Exercise Sessions `/api/exercise`

#### POST `/start`
Starts a new exercise session.
```json
{
  "message": "Session started successfully",
  "session_id": 123
}
```

#### POST `/end`
Ends the current session.
```json
{
  "message": "Session ended successfully",
  "data": {
    "id": 123,
    "duration_seconds": 600,
    "distance_km": 1.2,
    "steps": 1500,
    "calories": 50,
    "average_speed": 3.5
  }
}
```

#### GET `/history`
Retrieves session history.
- Query params: `page=1&per_page=10`
```json
{
  "sessions": [{
    "id": 123,
    "start_time": "2024-01-01T10:00:00Z",
    "end_time": "2024-01-01T10:30:00Z",
    "duration_seconds": 1800,
    "distance_km": 2.5,
    "steps": 3000,
    "calories": 150,
    "average_speed": 3.5
  }],
  "total": 50,
  "page": 1,
  "pages": 5
}
```

#### GET `/stats`
Gets exercise statistics.
- Query params: `period=daily|weekly|monthly`
```json
{
  "total_sessions": 10,
  "total_distance": 25.5,
  "total_steps": 30000,
  "total_duration": 18000,
  "total_calories": 1500,
  "average_speed": 3.5,
  "period": "daily"
}
```

### Goals & Targets `/api/targets`

#### GET `/`
Lists current goals.
- Query params: `active=true|false`
```json
[{
  "id": 1,
  "type": "distance|steps|calories|duration",
  "value": 5.0,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "completed": false
}]
```

#### POST `/`
Creates a new goal.
// Request
```json
{
  "type": "distance",
  "value": 5.0,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```
// Response
```json
{
  "id": 1,
  "type": "distance",
  "value": 5.0,
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "completed": false
}
```

#### GET `/progress`
Tracks goal progress.
```json
{
  "target": {
    "id": 1,
    "type": "distance",
    "value": 5.0
  },
  "current_value": 2.5,
  "progress": 50.0,
  "completed": false
}
```

### Settings `/api/settings`

#### GET `/preferences`
Retrieves device preferences.
```json
{
  "max_speed": 6.0,
  "start_speed": 2.0,
  "sensitivity": 2,
  "child_lock": false,
  "units_miles": false
}
```

#### POST `/preferences`
Updates preferences.
- Query params:
  - `max_speed`: 10-60 (1.0-6.0 km/h)
  - `start_speed`: 10-30 (1.0-3.0 km/h)
  - `sensitivity`: 1-3
  - `child_lock`: true|false
  - `units_miles`: true|false

## 2. Data Management

### Exercise Sessions
- Automatic session recording
- Calorie calculation based on distance and duration
- Real-time statistics tracking
- Complete session history

### Goals
- Multiple goal types (distance, steps, calories, duration)
- Automatic progress tracking
- Configurable start and end dates
- Automatically updated completion status

### User Preferences
- Customizable speed settings
- Safety options (child lock)
- Unit choice (km/miles)
- Adjustable belt sensitivity

### Real-time Data
- Current speed
- Distance covered
- Step count
- Exercise duration
- Belt status
- Operating mode

## 3. Key Features

1. **Device Control**
   - Safe start/stop
   - Precise speed control
   - Mode switching (manual/auto)
   - Belt calibration

2. **Exercise Tracking**
   - Timed sessions
   - Automatic metric calculation
   - Detailed history
   - Aggregated statistics

3. **Goal Management**
   - Custom goal creation
   - Progress tracking
   - Completion notifications
   - Achievement history

4. **Settings and Configuration**
   - User preferences
   - Device configuration
   - Safety options
   - Unit customization

## 4. Error Handling

Each endpoint returns standardized errors:
```json
{
  "error": "Error description",
  "details": "Optional technical details"
}
```

HTTP Codes used:
- 200: Success
- 400: Bad Request
- 404: Resource Not Found
- 500: Server Error

## 5. Security

- Input validation on all endpoints
- Speed limit verification
- Protection against invalid commands
- Secure disconnection handling

This API provides a complete interface for controlling the WalkingPad and managing exercise sessions, with emphasis on security and ease of use.

## 6. Data Flows and Usage Scenarios

### Scenario 1: Typical Exercise Session

1. **Session Start**
```http
POST /api/exercise/start
```
- Initializes new session
- Activates metric tracking
- Returns unique session ID

2. **Treadmill Control**
```http
POST /api/device/mode?mode=manual
POST /api/device/speed?speed=30  // 3.0 km/h
```
- Sets desired mode
- Adjusts initial speed

3. **Real-time Monitoring**
```http
GET /api/device/status
```
```json
{
  "mode": "manual",
  "belt_state": "running",
  "speed": 3.0,
  "distance": 0.5,
  "steps": 750,
  "time": 300,
  "calories": 25
}
```

4. **Session End**
```http
POST /api/exercise/end
```
- Saves final statistics
- Stops treadmill
- Generates session summary

### Scenario 2: Goal Management

1. **Goal Creation**
```http
POST /api/targets
Content-Type: application/json

{
  "type": "distance",
  "value": 100.0,
  "end_date": "2024-12-31"
}
```

2. **Progress Tracking**
```http
GET /api/targets/progress
```
```json
{
  "targets": [
    {
      "id": 1,
      "type": "distance",
      "target_value": 100.0,
      "current_value": 45.2,
      "progress": 45.2,
      "remaining": 54.8,
      "days_left": 120
    }
  ]
}
```

## 7. Detailed Data Formats

### Exercise Session
```json
{
  "id": 123,
  "user_id": 1,
  "start_time": "2024-01-01T10:00:00Z",
  "end_time": "2024-01-01T10:30:00Z",
  "metrics": {
    "duration_seconds": 1800,
    "distance_km": 2.5,
    "steps": 3000,
    "calories": 150,
    "average_speed": 3.5,
    "max_speed": 4.0,
    "min_speed": 2.5
  },
  "segments": [
    {
      "timestamp": "2024-01-01T10:00:00Z",
      "speed": 3.0,
      "distance": 0.0
    },
    {
      "timestamp": "2024-01-01T10:15:00Z",
      "speed": 3.5,
      "distance": 1.25
    }
  ]
}
```

### Aggregated Statistics
```json
{
  "daily": {
    "date": "2024-01-01",
    "sessions": 2,
    "total_distance": 5.0,
    "total_steps": 6000,
    "total_calories": 300,
    "active_minutes": 60
  },
  "weekly": {
    "week_number": 1,
    "year": 2024,
    "sessions": 10,
    "total_distance": 25.0,
    "total_steps": 30000,
    "total_calories": 1500,
    "active_minutes": 300,
    "days_active": 5
  }
}
```

## 8. Monitoring and Diagnostics

### System Status
```http
GET /api/health
```
```json
{
  "status": "healthy",
  "components": {
    "database": "connected",
    "device": "connected",
    "bluetooth": "active"
  },
  "metrics": {
    "active_sessions": 1,
    "connected_devices": 1,
    "api_latency": "45ms"
  }
}
```

### Activity Logs
```http
GET /api/logs
```
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T10:00:00Z",
      "level": "INFO",
      "event": "session_started",
      "details": {
        "session_id": 123,
        "initial_speed": 3.0
      }
    }
  ]
}
```

## 9. Frontend Integration

### WebSocket Events
```javascript
// WebSocket Connection
const ws = new WebSocket('ws://api/events');

// Available Events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch(data.type) {
    case 'speed_change':
      updateSpeedDisplay(data.speed);
      break;
    case 'stats_update':
      updateStats(data.stats);
      break;
    case 'target_achieved':
      showAchievement(data.target);
      break;
  }
};
```

### Recommended Polling
- Device status: 1 second
- Session statistics: 5 seconds
- Goal progress: 30 seconds

## 10. Limits and Constraints

1. **Performance**
   - Max 10 requests/second per client
   - Maximum payload size: 1MB
   - 1000 stored sessions limit

2. **Security**
   - Session timeout: 30 minutes
   - Max 5 login attempts
   - IP-based rate limiting

3. **Data**
   - Data retention: 12 months
   - Data export limited to 10000 entries
   - Maximum file size: 50MB

This documentation provides a comprehensive view of the API capabilities and practical usage. Would you like additional details about any specific aspect?