from fastapi import FastAPI, APIRouter, Request, HTTPException
import uvicorn
import logging

from dotenv import load_dotenv

from backend.projectmanagement.runtime import Runtime

from backend.server import Server

from backend.games.ark import Game_Ark
from backend.games.satisfactory import Game_Satisfactory

from backend.datenbank.db_utils import DB_Pool

from backend.api.middleware import API_Keys

import os

# from api.api_minecraft import MinecraftServer

# Zugangsdaten laden
load_dotenv()

api_keys = API_Keys(r"/opt/mngmnt_server/code/api_gameserver/api/API_KEYS.env")
https_app = FastAPI()
# MinecraftServer.register_routes(https_app, api_keys)
Game_Ark.register_routes(https_app, api_keys)
Game_Satisfactory.register_routes(https_app, api_keys)
Server.register_routes(https_app, api_keys)

if __name__ == "__main__":

    DB_Pool.set_db_pool(DB_Pool(1, 5, os.getenv["DB_DATABASE"], os.getenv["DB_USER"], os.getenv["DB_PASSWORD"], os.getenv["DB_HOST"], os.getenv["DB_PORT"]))

    # Runtime.set_idle()
    server = Server(600)
    server.start()

    # Logger für Uvicorn und FastAPI anpassen
    logging.getLogger("uvicorn").setLevel(logging.CRITICAL)   
    logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)  
    logging.getLogger("fastapi").setLevel(logging.CRITICAL)    

    Server.set_current(server)
    Game_Ark.set_current(server)
    Game_Satisfactory.set_current(server)
    
    @https_app.get("/")
    def read_root():
        print("Anfrage")
        return {"message": "Hello, HTTPS World!"}

    if __name__ == "__main__":
        uvicorn.run(
            "main:https_app",
            host="0.0.0.0",
            port=3001,
            ssl_keyfile="backend/cert/key.pem",
            ssl_certfile="backend/cert/cert.pem"
        )