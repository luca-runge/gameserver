from projectmanagement.runtime import Runtime
import asyncio
from games.ark import Game_Ark
from games.satisfactory import Game_Satisfactory
from projectmanagement.state import ServerState
import threading
import time
import psutil
from fastapi import APIRouter, HTTPException, Query, Body, Depends, Header, Request
from fastapi.responses import JSONResponse
from api.middleware import berechtigung_pruefen
import os

class Server:

    current = None

    def __init__(self, interval):

        self.in_use = True
        self._lock = asyncio.Lock()
        self._state = ServerState.RUNNING
        self._running = False
        self.interval = interval

    def set_current(server):

        Server.current = server

    def start(self):

        Runtime.set_idle(300)
        self.start_check_use_interval()

    def stop(self):

        self._state = ServerState.STOPPING
        Runtime.idle.stop_interval()
        self.stop_check_use_interval()
        print(f"Der Hardwareserver stoppt in 20s")

        time.sleep(20)

        os.system("sudo shutdown -h now")


    async def check_online(self):

        in_use = False

        async with self._lock:

            # Überprüfe ARK
            async with Game_Ark.current._state_lock:

                if self.shh_or_smb():

                    in_use = True

                if Game_Ark.current._state != ServerState.OFF:

                    print("Ark wird verwendet.")
                    in_use = True

                if Game_Satisfactory.current._state != ServerState.OFF:

                    print("Satisfactory wird verwendet.")
                    in_use = True

            if not in_use and not self.in_use:

                self._state = ServerState.STOPPING

                self.stop()

            self.in_use = in_use

        print(f"Ist der Server ist in Gebrauch? {in_use}")

        return in_use

    
        # Startet das Backup im Intervall
    def _run(self):

        # Intervall abwarten
        time.sleep(self.interval)

        # Solange das Auto-Backup eingeschaltet ist
        while self._running:

            asyncio.run(self.check_online())

            # Intervall abwarten
            time.sleep(self.interval)

    def start_check_use_interval(self):
    
        # Nur, wenn noch kein Backup-Intervall läuft
        if not self._running:

            # Thread starten, welcher _run ausführt
            print("Starte SERVER Check-In-Use Intervall")
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    # Backup Intervall beenden
    def stop_check_use_interval(self):

        if self._running:

            print("Stoppe SERVER Check-In-Use Intervall")

            # Thread beenden
            self._running = False
            self._thread = None

    

    def get_active_connections(self, ports):
        connections = []
        
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.raddr and conn.status == "ESTABLISHED":
                if conn.laddr.port in ports:
                    connections.append(conn.raddr.ip)  # Speichert die Client-IP-Adresse
        
        return {"count": len(connections), "clients": connections}

    def shh_or_smb(self):
         
        result = False
        
        ssh = self.get_active_connections({22})  # SSH (Port 22)
        smb =  self.get_active_connections({445, 139})  # SMB (Ports 445 & 139)

        if ssh["count"] > 0:
            print("SSH wird verwendet!")
            result = True

        if smb["count"] > 0:
            print("SMB wird verwendet!")
            result = True

        return result
    
    @staticmethod
    def register_routes(app, api_keys):

        router = APIRouter(prefix="/api/server")

        @router.get("/online")
        async def get_info(request: Request):

            response_data = {"online": True}
            return JSONResponse(content=response_data, status_code=200)
        
        @router.get("/status")
        async def get_info(request: Request):

            ssh = Server.current.get_active_connections({22})  # SSH (Port 22)
            smb =  Server.current.get_active_connections({445, 139})  # SMB (Ports 445 & 139)

            response_data = {"online": True, "ssh": ssh, "smb":smb}
            return JSONResponse(content=response_data, status_code=200)

        app.include_router(router)

    