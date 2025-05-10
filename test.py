from fastapi import FastAPI, APIRouter
import uvicorn
from backend2.game.satisfactory import Satisfactory
from backend2.server import Server

if __name__ == "test":

    # Server
    server = Server(10)

    # Spiele
    satisfactory = Satisfactory(server)

    # Spiele zum Server hinzufügen (CheckUse)
    server.addGame(satisfactory)

    server.start()

    # Webserver und Router
    app = FastAPI()
    app.include_router(server.router)
    app.include_router(satisfactory.router)
    
# Webserver starten
if __name__ == "__main__":
    uvicorn.run("test:app", host="127.0.0.1", port=8000, reload=True)