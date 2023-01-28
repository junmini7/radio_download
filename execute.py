import uvicorn

uvicorn.run(
    "download:app",
    port=8012,
    host="0.0.0.0",
    ssl_keyfile="/etc/ssl/woowakgood.live.key",
    ssl_certfile="/etc/ssl/woowakgood.live.crt",
)
