import os
import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.app:app", host="127.0.0.1", port=int(os.getenv("CULTURE_DESK_PORT", "8000")))
