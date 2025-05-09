from projectmanagement.games import Game
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header, Request
from fastapi.responses import JSONResponse
from api.middleware import berechtigung_pruefen
from games.communication.rcon import RCON

from satisfactory_api_client import SatisfactoryAPI
from satisfactory_api_client.data import MinimumPrivilegeLevel

import asyncio
import time

import re

class Game_Satisfactory:

    NAME = "Satisfactory"
    COMMAND = r"/Gameserver/satisfactory_server/FactoryServer.sh -log -unattended"
    CONFIG_PATH_MAPPING = r"/mnt/data/gameserver/satisfactory/backup/config_path_mapping.json"
    SAVED_PATH_MAPPING = r"/mnt/data/gameserver/satisfactory/backup/saved_path_mapping.json"
    CONFIG_AUTOSAVE_INTERVAL =  1800
    SAVED_AUTOSAVE_INTERVAL = 900
    CONFIG_STATE_ZERO = r"/mnt/data/gameserver/satisfactory/template/state_zero_config.json"
    SAVED_STATE_ZERO = r"/mnt/data/gameserver/satisfactory/template/state_zero_saves.json"

    SEARCH_NAME = "FactoryServer-Linux-Shipping"
    SEARCH_CMDLINE = "/Gameserver/satisfactory_server/Engine/Binaries/Linux/FactoryServer-Linux-Shipping"

    LAST_PLAYERS_ONLINE = []

    HOST = "luca-server.fritz.box"
    TOKEN = "ewoJInBsIjogIkFQSVRva2VuIgp9.93E38A49F8FC8A778D167FB170029C7A77356FCF510BF071DC56F98E819294D3FAD1F71A8CDA68F7A0CDD49D785E377A3443D2E80F836914069FDF49D77EA77B"
    current = None

    def set_current(server):

        Game_Satisfactory.current = Game(Game_Satisfactory.NAME, Game_Satisfactory.COMMAND, Game_Satisfactory.SEARCH_NAME, Game_Satisfactory.SEARCH_CMDLINE, Game_Satisfactory.CONFIG_PATH_MAPPING, Game_Satisfactory.SAVED_PATH_MAPPING , Game_Satisfactory.CONFIG_AUTOSAVE_INTERVAL, Game_Satisfactory.SAVED_AUTOSAVE_INTERVAL, Game_Satisfactory.CONFIG_STATE_ZERO, Game_Satisfactory.SAVED_STATE_ZERO, Game_Satisfactory.save, Game_Satisfactory.stop, Game_Satisfactory.send_message, Game_Satisfactory.check_player_online, None, Game_Satisfactory.before_start, None, server)

    def save():

        print("Speichere Satisfactory")

        try:
            api = SatisfactoryAPI(host=Game_Satisfactory.HOST, auth_token=Game_Satisfactory.TOKEN)
            response = api.save_game(Game_Satisfactory.current.project.project_name)
        except Exception as e:

            print("Fehler beim Speichern von Satisfactory")

    def player_count():
        
        player = 0
        try:

            api = SatisfactoryAPI(host=Game_Satisfactory.HOST, auth_token=Game_Satisfactory.TOKEN)

            response = api.query_server_state()

            if response.success:

                player = response.data["serverGameState"]["numConnectedPlayers"]

                print(f"Verbundene Spieler: {player}")

        except Exception as e:

            print("Fehler bei der Abfrage verbundener Spieler in Satisfactory")

        return player

    def check_player_online():

        player_online = False

        player = Game_Satisfactory.player_count()

        if player > 0:

            print(player_online)

            # Check-Methode
            player_online = True
        
        return player_online

    async def stop():

        print("Satisfactory stopt mit quit")

        try:
            api = SatisfactoryAPI(host=Game_Satisfactory.HOST, auth_token=Game_Satisfactory.TOKEN)
            response = await asyncio.to_thread(api.shutdown)

        except Exception as e:

            print("Fehler beim Shutdown-Command and Satisfactory!")

    async def send_message(message):

        print(f"Ingame Nachricht senden")


    def before_start():

        print("Before Start: MaxPlayer setzen")

        maxplayers, _ = Game_Satisfactory.current.project.get_whitelist()

        if maxplayers < 1:

            maxplayers = 1

        Game.change_config("/Script/Engine.GameSession", "MaxPlayers", maxplayers, r"/Gameserver/satisfactory_server/FactoryGame/Saved/Config/LinuxServer/Game.ini")

        time.sleep(5)


    def after_start():

        print("After Start")

    @staticmethod
    def register_routes(app, api_keys):

        router = APIRouter(prefix="/api/satisfactory")

        @router.post("/start")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            body = await request.json()
            UserID = body.get("userid")
            berechtigung_pruefen(['Satisfactory Admin', 'Satisfactory'], UserID)

            print("Starbefehl erhalten")
            result = await Game_Satisfactory.current.async_start()

            message = ""
            if result:

                message = "Satisfactory wurde gestartet!"

            else:

                message = "Satisfactory konnte nicht gestartet werden!"

            response_data = {"message": message}
            return JSONResponse(content=response_data, status_code=200)

        @router.post("/stop")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            body = await request.json()
            UserID = body.get("userid")
            berechtigung_pruefen(['Satisfactory Admin'], UserID)

            print("Stopbefehl erhalten")
            result = await Game_Satisfactory.current.async_stop()

            if result:

                message = "Satisfactory wurde gestoppt!"

            else:

                message = "Satisfactory kann nicht gestoppt werden!"

            response_data = {"message": message}
            return JSONResponse(content=response_data, status_code=200)
        
        @router.post("/player")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            body = await request.json()
            UserID = body.get("userid")
            berechtigung_pruefen(['Satisfactory Admin', 'Satisfactory'], UserID)

            message = ""

            if Game_Satisfactory.current.running():

                anz_player = await asyncio.to_thread(Game_Satisfactory.player_count)

                if anz_player == 0:

                    message = f"Es ist aktuell keine Spieler in Satisfactory online."

                elif anz_player == 1:

                    message = f"Es ist aktuell ein Spieler in Satisfactory online."

                else:

                    message = f"Es sind aktuell {anz_player} Spieler in Satisfactory online."

            else:

                message = "Satisfactory läuft zurzeit nicht."


            print(message)

            response_data = {"message": message}
            return JSONResponse(content=response_data, status_code=200)
        
        @router.post("/crash")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            body = await request.json()
            UserID = body.get("userid")
            berechtigung_pruefen(['Satisfactory', 'Satisfactory Admin'], UserID)

            message = ""

            if Game_Satisfactory.current.running():

                crash = await Game_Satisfactory.current.async_crash_handler()

                if crash:

                    message = f"Der Satisfactory-Server ist abgestürzt und wurde neu gestartet."

                else:

                    message = f"Es konnte kein Crash ermittelt werden."

            else:

                message = "Satisfactory läuft zurzeit nicht."


            print(message)

            response_data = {"message": message}
            return JSONResponse(content=response_data, status_code=200)

        @router.post("/load")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            print("Projekt laden")

            body = await request.json()
            UserID = body.get("userid")
            berechtigung_pruefen(['Satisfactory Admin'], UserID)

            payload = body["body"]
            project = payload["project"]

            result = await Game_Satisfactory.current.async_load_project(project)
            
            message = ""
            if result:

                message = f"Projekt {project} wurde geladen!"

            else:

                message = f"Projekt {project} konnte nicht geladen werden!"

            response_data = {"message": message}
            return JSONResponse(content=response_data, status_code=200)

        app.include_router(router)
