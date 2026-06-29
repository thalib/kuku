import uvicorn
from app.config import APP_HOST, APP_PORT, print_config
from app.main import app

if __name__ == "__main__":
    print_config()
    uvicorn.run("app.main:app", host=APP_HOST, port=APP_PORT, reload=False)
