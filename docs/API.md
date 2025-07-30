# docs/API.md
## JSON-RPC Methods

### get_server_info
- Description: Get server and system information
- Parameters: None
- Returns: Server details, system info, resource usage

### get_camera_list
- Description: Get all connected cameras
- Parameters: None
- Returns: Array of camera objects with status

### get_camera_status
- Description: Get specific camera details
- Parameters: 
  - device: string (e.g., "/dev/video0")
- Returns: Detailed camera information

### capture_snapshot
- Description: Capture a snapshot from the specified camera device
- Parameters:
  - device: string (e.g., "/dev/video0") **required**
  - format: string (e.g., "jpeg") *(optional, default: "jpeg")*
- Returns: Snapshot metadata (snapshot_id, filename, device, timestamp)

### start_recording
- Description: Start recording video from the specified camera device
- Parameters:
  - device: string (e.g., "/dev/video0") **required**
  - format: string (e.g., "mp4") *(optional, default: "mp4")*
  - duration: integer (seconds, optional)
- Returns: Recording metadata (recording_id, filename, device, started_at)

### stop_recording
- Description: Stop a running recording by its ID
- Parameters:
  - recording_id: string **required**
- Returns: Stop status (recording_id, status, stopped_at)

### schedule_recording
- Description: Schedule a recording at a future time
- Parameters:
  - device: string (e.g., "/dev/video0") **required**
  - start_time: string (ISO8601, e.g., "2025-07-30T15:00:00") **required**
  - duration: integer (seconds) **required**
  - format: string (e.g., "mp4") *(optional, default: "mp4")*
- Returns: Schedule metadata (device, scheduled_for, duration, format, status)

### echo
- Description: Echo back the provided message
- Parameters:
  - message: string **required**
- Returns: The same message

### get_supported_methods
- Description: Get list of all supported RPC methods
- Parameters: None
- Returns: Array