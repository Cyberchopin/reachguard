"""Start the local microphone page with the local .env credential."""
import os
from pathlib import Path
import uvicorn


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[1] / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.startswith("ASSEMBLYAI_API_KEY="):
                os.environ["ASSEMBLYAI_API_KEY"] = line.split("=",1)[1].strip()
    uvicorn.run("callgate.api:app",host="127.0.0.1",port=8765,ws_max_size=32768,access_log=False)
