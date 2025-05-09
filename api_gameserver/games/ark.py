from projectmanagement.games import Game
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header, Request
from fastapi.responses import JSONResponse
from api.middleware import berechtigung_pruefen
from games.communication.rcon import RCON

import re

class Game_Ark:

    NAME = "Ark: Survival Evolved"
    COMMAND = r"/Gameserver/ark_server/ShooterGame/Binaries/Linux/ShooterGameServer %ZUSATZ% -exclusivejoin -server -log"
    CONFIG_PATH_MAPPING = r"/mnt/data/gameserver/ark/backup/config_path_mapping.json"
    SAVED_PATH_MAPPING = r"/mnt/data/gameserver/ark/backup/saved_path_mapping.json"
    CONFIG_AUTOSAVE_INTERVAL =  600
    SAVED_AUTOSAVE_INTERVAL = 180
    CONFIG_STATE_ZERO = r"/mnt/data/gameserver/ark/template/state_zero_config.json"
    SAVED_STATE_ZERO = r"/mnt/data/gameserver/ark/template/state_zero_saves.json"

    SEARCH_NAME = "ShooterGameServer"
    SEARCH_CMDLINE = "/Gameserver/ark_server/ShooterGame/Binaries/Linux/ShooterGameServer"

    LAST_PLAYERS_ONLINE = []

    RCON_PORT = 27020
    HOST = "luca-server.fritz.box"
    RCON_PASSWORD = "hallo2"
    current = None

    def set_current(server):

        Game_Ark.current = Game(Game_Ark.NAME, Game_Ark.COMMAND, Game_Ark.SEARCH_NAME, Game_Ark.SEARCH_CMDLINE, Game_Ark.CONFIG_PATH_MAPPING, Game_Ark.SAVED_PATH_MAPPING , Game_Ark.CONFIG_AUTOSAVE_INTERVAL, Game_Ark.SAVED_AUTOSAVE_INTERVAL, Game_Ark.CONFIG_STATE_ZERO, Game_Ark.SAVED_STATE_ZERO, Game_Ark.save, None, Game_Ark.send_message, Game_Ark.check_player_online, None, None, None, server)

    def save():

        rcon = RCON(Game_Ark.HOST, Game_Ark.RCON_PORT, Game_Ark.RCON_PASSWORD)

        # Verbinden
        if rcon.sync_connect():

            # Befehl mit Antwort
            response = rcon.sync_send_command(f"serverchat Ark wird gespeichert.")

            print(f"RCON sagt: {response}")

            response = rcon.sync_send_command(f"saveworld")

            print(f"RCON sagt: {response}")

        # Verbindung schließen
        rcon.close()

    def check_player_online():

        rcon = RCON(Game_Ark.HOST, Game_Ark.RCON_PORT, Game_Ark.RCON_PASSWORD)
        response = rcon.sync_connect_send_close("listplayers")
        print(f"RCON sagt: {response}")

        player_count = 0
        current_connected = []

        # Prüfen, ob keine Spieler online.
        if not "No Players Connected" in response:
            
            # Steam64-ID ist genau 17 Ziffern lang
            rex_steam64 = r"\b\d{17}\b"

            current_connected = re.findall(rex_steam64, response)
            player_count = len(current_connected)

        player_joined = [player for player in current_connected if player not in Game_Ark.LAST_PLAYERS_ONLINE]
        player_left = [player for player in Game_Ark.LAST_PLAYERS_ONLINE if player not in current_connected]

        print(f"Es sind folgende Spieler beigetreten: {", ".join(player_joined)}")
        print(f"Es haben folgende Spieler verlassen: {", ".join(player_left)}")

        player_online = False

        if player_count > 0:

            player_online = True

        Game_Ark.LAST_PLAYERS_ONLINE = current_connected

        return player_online

    async def stop():

        rcon = RCON(Game_Ark.HOST, Game_Ark.RCON_PORT, Game_Ark.RCON_PASSWORD)
        response = await rcon.async_connect_send_close("doexit")
        print(f"RCON sagt: {response}")

    async def send_message(message):

        rcon = RCON(Game_Ark.HOST, Game_Ark.RCON_PORT, Game_Ark.RCON_PASSWORD)
        response = await rcon.async_connect_send_close(f"serverchat {message}")
        print(f"RCON sagt: {response}")


    def before_start():

        Game_Ark.LAST_PLAYERS_ONLINE = []

        player_count, whitelist = Game_Ark.current.project.get_whitelist()

        print(player_count)
        print(whitelist)

    @staticmethod
    def register_routes(app, api_keys):

        router = APIRouter(prefix="/api/ark")

        @router.post("/start")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            print("Starbefehl erhalten")
            
            await Game_Ark.current.async_start()

            #body = await request.json()

            #UserID = body.get("userid")

            #berechtigung_pruefen(['Administrator'], UserID)
            
            #return f"Dies ist ein Server {UserID}"

            response_data = {"message": "Ark wurde gestartet!"}
            return JSONResponse(content=response_data, status_code=200)

        @router.post("/stop")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            print("Stopbefehl erhalten")
            
            await Game_Ark.current.async_stop()

            #body = await request.json()

            #UserID = body.get("userid")

            #berechtigung_pruefen(['Administrator'], UserID)
            
            #return f"Dies ist ein Server {UserID}"

            response_data = {"message": "Ark wurde gestoppt!"}
            return JSONResponse(content=response_data, status_code=200)

        @router.post("/load")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            print("Projekt laden")

            await Game_Ark.current.async_load_project("ark_test_01")
            
            #Game_Ark.current.stop()

            #body = await request.json()

            #UserID = body.get("userid")

            #berechtigung_pruefen(['Administrator'], UserID)
            
            #return f"Dies ist ein Server {UserID}"

        @router.post("/load2")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            print("Projekt laden 2")

            await Game_Ark.current.async_load_project("ark_test_02")
            
            #Game_Ark.current.stop()

            #body = await request.json()

            #UserID = body.get("userid")

            #berechtigung_pruefen(['Administrator'], UserID)
            
            #return f"Dies ist ein Server {UserID}"

        @router.post("/wl")
        async def get_info(request: Request, api_key: str = Depends(api_keys.check_https_api_key)):

            body = await request.json()

            UserID = body.get("userid")
            berechtigung_pruefen(['Administrator'], UserID)

            response_data = {"message": "Dies ist eine Testnachricht!"}
            return JSONResponse(content=response_data, status_code=200)

        app.include_router(router)

