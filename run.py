import uvicorn
from backend import config

if __name__ == "__main__":
    print(f"Abre http://{config.HOST}:{config.PORT}")
    uvicorn.run("backend.app:app", host=config.HOST, port=config.PORT, reload=True)
