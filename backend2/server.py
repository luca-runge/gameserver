from backend2.runtime import IdleRuntime
import asyncio
from backend2.state import ServerState
import time
import psutil
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import os
from backend2.game.game import Game

class Server:

    def __init__(self, interval):

        # CheckUse [vorherige Prüfung] -> Muss vorm Stoppen 2 mal in Folge nicht in Verwendung sein
        self.in_use = True

        # Lock für Server-Zustand
        self._lock = asyncio.Lock()

        # Zustand
        self._state = ServerState.RUNNING

        # Intervall: CheckUse
        self._running = False

        # Intervall-Dauer: CheckUse
        self.interval = interval

        # Alle auf dem Server registrierten Spiele
        self.games = []

        # Runtime
        self.runtime = IdleRuntime(10)

        # API-Anfrgen
        self.router = APIRouter(prefix="/api/server")
        self.register_routes()


    # Server starten
    def start(self):

        self.start_checkUse()

    # Server beenden
    async def stop(self):

        self._state = ServerState.STOPPING
        
        await self.runtime.stop()

        self.stop_checkUse()
        print(f"Der Hardwareserver stoppt in 20s")

        # Event-Loop wird zusätzlich blockiert, sodass in den 20s keine Anfragen angenommen werden
        time.sleep(20)

        # os.system("sudo shutdown -h now")

    # Spiel registrieren
    def addGame(self, game):

        # Nur Objekte der Klasse Game + Subklassen -> Nur Spiele
        if isinstance(game, Game):

            # In Array speichern
            self.games.append(game)
            print(f"{game.name} hinzugefügt!")

        else:
            raise TypeError("Kein Game!")

    # Prüfen, ob der Server in verwendung ist: Ansonsten stoppen.
    async def checkUse(self):

        # Ergebnis
        in_use = False

        # Server-Zustand sperren
        async with self._lock:

            # Zustand-Locks der Spiele
            locks = [game._state_lock for game in self.games]

            # Zustände aller Spiele sperren
            for lock in locks:
                await lock.acquire()

            # Kritischer Bereich
            try:

                # SMB oder SHH in Verwendung
                if self.shh_or_smb():

                    # In Verwendung
                    in_use = True

                # Über Spiele iterieren
                for game in self.games:

                    # Spiel-Server nicht ausgeschaltet 
                    if game._state != ServerState.OFF:

                        # In Verwendung
                        print(f"{game.name} wird verwendet.")
                        in_use = True

                # Diese und letzte Prüfung negativ (2 in Folge negativ)
                if not in_use and not self.in_use:

                    self._state = ServerState.STOPPING
                    await self.stop()

                # Ergebnis für die nächste Runde (2 in Folge negativ)
                self.in_use = in_use

            except Exception as e:
                
                print(f"Fehler bei CheckUse-Ermittlung: {e}")

            finally:

                # Alle Objekte entsperren
                for lock in locks:
                    lock.release()
            
    # Startet das checkUse im Intervall
    async def _checkUse_interval(self):

        # Intervall abwarten
        await asyncio.sleep(self.interval)

        # Solange das Auto-Backup eingeschaltet ist
        while self._running:

            await self.checkUse()

            # Intervall abwarten
            await asyncio.sleep(self.interval)

    # Intervall starten
    def start_checkUse(self):
    
        # Intervall läuft nicht
        if not self._running:

            # Task ausführen
            print("Starte SERVER Check-In-Use Intervall")
            self._running = True
            asyncio.create_task(self._checkUse_interval())


    # Intervall beenden
    def stop_checkUse(self):

        # Intervall läuft
        if self._running:

            print("Stoppe SERVER Check-In-Use Intervall")

            # Intervall beenden
            self._running = False

    # Verbindung auf einem Port zum Server prüfen (TCP)
    def get_active_connections(self, ports):

        # Verbindungen
        connections = []
        
        # Verbindungen
        for conn in psutil.net_connections(kind='inet'):
            # Hergestellte Verbindungen 
            if conn.laddr and conn.raddr and conn.status == "ESTABLISHED":
                # Nur angegebener Port
                if conn.laddr.port in ports:
                    # Speichert die Client-IP-Adresse
                    connections.append(conn.raddr.ip)  
        
        # Anzahl und IP-Adressen zum angegebenen Port
        return {"count": len(connections), "clients": connections}

    # Prüfen, ob SHH oder SMB in Verwendung ist
    def shh_or_smb(self):
        
        # Ergebnis
        result = False
        
        # Verbindungen zum jeweiligen Port
        ssh = self.get_active_connections({22})  # SSH (Port 22)
        smb =  self.get_active_connections({445, 139})  # SMB (Ports 445 & 139)

        # SSH in Verwendung
        if ssh["count"] > 0:
            print("SSH wird verwendet!")
            result = True

        # SMB in Verwendung
        if smb["count"] > 0:
            print("SMB wird verwendet!")
            result = True

        # Ergebnis zurückgeben
        return result
    
    # Router für API-Anfragen
    def register_routes(self):

        @self.router.get("/online")
        async def get_info(request: Request):

            response_data = {"online": True}
            return JSONResponse(content=response_data, status_code=200)
        
        @self.router.get("/status")
        async def get_info(request: Request):

            ssh = self.get_active_connections({22})  # SSH (Port 22)
            smb =  self.get_active_connections({445, 139})  # SMB (Ports 445 & 139)

            response_data = {"online": True, "ssh": ssh, "smb":smb}
            return JSONResponse(content=response_data, status_code=200)
