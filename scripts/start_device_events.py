"""Start only the isolated inbox, on WSL loopback. No credentials in logs."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("callgate.device_events:from_env", factory=True, host="127.0.0.1",
                port=8780, access_log=False)
