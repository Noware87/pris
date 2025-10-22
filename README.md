# Tuya Flask Server (Render.com Free)

Endpoints:
- `/ac/on`  -> turn device ON
- `/ac/off` -> turn device OFF
- `/ac/status` -> device datapoints

Set env vars on Render:
- TUYA_CLIENT_ID (Access ID)
- TUYA_CLIENT_SECRET (Access Secret)
- TUYA_DEVICE_ID (from Cloud Project -> Devices)
- TUYA_REGION (eu/us/cn/in)
- TUYA_DP_CODE (switch/switch_1/power)

Deploy: New Web Service -> Upload this folder (or connect repo)
