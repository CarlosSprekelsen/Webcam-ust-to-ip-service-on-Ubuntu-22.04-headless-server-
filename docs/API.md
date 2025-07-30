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