from abc import ABC, abstractmethod
from fastapi import Request
from backend2.state import ServerState
from backend2.runtime import ProjectRuntime
import asyncio
from backend2.process import Process

class Game(ABC):

    def __init__(self, name, router, server):

        self.name = name
        self.router = router
        self.server = server

        self.process = Process(f"python3 test_process.py", "python3", "test_process.py")
        self.runtime = ProjectRuntime(15, server.runtime, 1)

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
            re = await self.process.async_Reattach()
            if re:
                async with self._state_lock:

                    if self._state == ServerState.OFF:
                        self._state = ServerState.RUNNING

                        await self.runtime.start_runtime()
                        print("reattach")



        @self.router.get("/stop")
        async def get_info(request: Request):
            async with self._state_lock:

                if self._state == ServerState.RUNNING:
                    self._state = ServerState.OFF

                    await self.process.async_StopProcess()
                    await self.runtime.stop_runtime()
                    print("gestoppt")



        @self.router.get("/start")
        async def get_info(request: Request):
            async with self._state_lock:

                if self._state == ServerState.OFF:
                    self._state = ServerState.RUNNING

                    await self.runtime.start_runtime()
                    await self.process.async_StartDetached()
                    self.process.findChildProcesses()
                    print("gestartet")




        

