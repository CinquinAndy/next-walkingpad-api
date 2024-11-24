# WalkingPad Mobile Application Specifications

## Overview
The WalkingPad Mobile Application is designed to provide a comprehensive interface for controlling your WalkingPad and tracking your fitness progress. The application features three main tabs: Home, Profile, and Goals, each offering distinct functionalities for an enhanced user experience.

## Core Features

### 1. Home Tab 🏠

#### Daily Statistics Display
- Current day's walking distance (km)
- Calories burned (kcal)
- Steps taken
- Total walking duration
- Live updates during active sessions

#### Main Control Center
- **Pad Visualization**
  - Visual representation of the WalkingPad
  - Real-time speed indicator
  - Current operational status

- **Primary Controls**
  - Large "GO" button for quick start
  - Speed control slider/buttons
  - Emergency stop function

- **Target Setting**
  - Time-based goals
  - Distance targets
  - Calorie burning objectives
  - Custom combinations of targets

#### Quick Settings
- Access to pad configuration
- Speed preferences
- Safety controls
- Connection status indicator

### 2. Profile Tab 👤

#### User Profile Management
- Profile picture upload/edit
- Personal Information:
  - First name
  - Last name
  - Age
  - Height (cm)
  - Weight (kg)
  - BMI calculation

#### Exercise History
- Detailed activity log
- Individual session details:
  - Date and time
  - Duration
  - Distance covered
  - Steps taken
  - Calories burned
  - Average speed

#### Statistics Dashboard
**Cumulative Statistics**
- Total lifetime:
  - Distance walked
  - Steps taken
  - Calories burned
  - Active hours

**Time-Based Analysis**
- Daily summaries
- Weekly reports
- Monthly statistics
- Yearly overview

**Progress Charts**
- Activity trends
- Performance metrics
- Goal achievement rates

### 3. Goals Tab 🎯

#### Daily Objectives
- Customizable daily targets:
  - Step goals
  - Distance goals
  - Active time goals
  - Calorie goals

#### Activity Calendar
- GitHub-style activity grid
- Color-coded intensity levels:
  - Grey: No activity
  - Light green: Minimal activity
  - Medium green: Moderate activity
  - Dark green: High activity

#### Progress Tracking
- Daily goal completion status
- Streak counting
- Achievement badges
- Monthly challenge tracking

## Technical Specifications

### Database Schema

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    age INTEGER,
    height FLOAT,
    weight FLOAT,
    profile_picture_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Exercise sessions table
CREATE TABLE exercise_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    date DATE,
    duration INTEGER, -- in seconds
    distance FLOAT,  -- in kilometers
    steps INTEGER,
    calories INTEGER,
    avg_speed FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily goals table
CREATE TABLE daily_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    step_goal INTEGER,
    distance_goal FLOAT,
    duration_goal INTEGER,
    calorie_goal INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Activity streaks table
CREATE TABLE activity_streaks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    start_date DATE,
    end_date DATE,
    streak_days INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints

#### User Management
```http
GET /api/users/{id}
POST /api/users
PUT /api/users/{id}
DELETE /api/users/{id}
```

#### Exercise Sessions
```http
GET /api/sessions
POST /api/sessions
GET /api/sessions/{id}
GET /api/sessions/stats/daily
GET /api/sessions/stats/weekly
GET /api/sessions/stats/monthly
GET /api/sessions/stats/yearly
```

#### Goals
```http
GET /api/goals
POST /api/goals
PUT /api/goals/{id}
GET /api/goals/progress
GET /api/goals/streaks
```

#### Pad Control
```http
POST /api/pad/start
POST /api/pad/stop
POST /api/pad/speed
GET /api/pad/status
POST /api/pad/target
```

## User Interface Guidelines

### Color Scheme
- Primary: #007AFF (Blue)
- Secondary: #5856D6 (Purple)
- Success: #34C759 (Green)
- Warning: #FF9500 (Orange)
- Error: #FF3B30 (Red)
- Background: #F2F2F7 (Light Gray)

### Typography
- Headings: SF Pro Display
- Body: SF Pro Text
- Monospace: SF Mono (for statistics)

### Activity Intensity Colors
- No activity: #EBEDF0
- Low activity: #9BE9A8
- Medium activity: #40C463
- High activity: #216E39

## Required Permissions
- Bluetooth access
- Local storage access
- Camera access (for profile pictures)
- Background processing (for session tracking)

## Future Enhancements
1. Social features
2. Workout programs
3. Integration with health apps
4. Voice commands
5. Advanced analytics
6. Multi-device support

## Security Considerations
- Secure user data storage
- Encrypted Bluetooth communication
- Regular security updates
- GDPR compliance
- Data backup and recovery

This specification provides a comprehensive outline for developing the WalkingPad mobile application. Implementation should follow these guidelines while maintaining flexibility for future improvements and user feedback.