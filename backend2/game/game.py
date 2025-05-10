from abc import ABC, abstractmethod
from fastapi import Request
from backend2.state import ServerState
import asyncio

class Game(ABC):

    def __init__(self, name, router, server):

        self.name = name
        self.router = router
        self.server = server
        self._state = ServerState.OFF
        self._state_lock = asyncio.Lock()

        # Routen hinzufügen
        self.register_routes()

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def register_specific_routes(self):
        pass

    def register_routes(self):

        self.register_specific_routes()

        @self.router.get("/save")
        async def get_info(request: Request):
            print("Speichern")

        @self.router.get("/stop")
        async def get_info(request: Request):
            async with self._state_lock:

                if self._state == ServerState.RUNNING:
                    self._state = ServerState.OFF
                    print("gestoppt")

        @self.router.get("/start")
        async def get_info(request: Request):
            async with self._state_lock:

                if self._state == ServerState.OFF:
                    self._state = ServerState.RUNNING
                    print("gestartet")

        

