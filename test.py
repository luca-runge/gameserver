from fastapi import FastAPI, APIRouter
import uvicorn
from backend2.game.satisfactory import Satisfactory

class MyHandler:
    def __init__(self):
        print("Objekt erstellt")
        self.router = APIRouter(prefix="/route")
        self.router.add_api_route("/", self.handle_root, methods=["GET"])

    async def handle_root(self):
        raise KeyError
        return {"message": "Hello from MyHandler"}

# Objekt und Router außerhalb der main-Abfrage erstellen

print(__name__)
if __name__ == "test":

    game = Satisfactory()
    app = FastAPI()
    app.include_router(game.router)
    
# Optional: Nur zum Starten mit `python my_app.py`
if __name__ == "__main__":

    uvicorn.run("test:app", host="127.0.0.1", port=8000, reload=True)