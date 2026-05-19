@echo off
setlocal
if "%CCB_BASE_URL%"=="" set CCB_BASE_URL=http://127.0.0.1:3000

echo --^> GET  %CCB_BASE_URL%/api/health
curl -fsS "%CCB_BASE_URL%/api/health"
echo.

if "%CCB_API_TOKEN%"=="" (
  echo CCB_API_TOKEN not set ^-^- skipping /api/notify. Send /start to the bot to get one. 1^>^&2
  exit /b 0
)

echo --^> GET  %CCB_BASE_URL%/api/whoami
curl -fsS -H "Authorization: Bearer %CCB_API_TOKEN%" "%CCB_BASE_URL%/api/whoami"
echo.

echo --^> POST %CCB_BASE_URL%/api/notify
curl -fsS -X POST "%CCB_BASE_URL%/api/notify" -H "Content-Type: application/json" -H "Authorization: Bearer %CCB_API_TOKEN%" -d "{\"text\":\"Demo notification from bin/demo\",\"session_id\":\"demo\",\"kind\":\"info\"}"
echo.
