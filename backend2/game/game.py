from abc import ABC, abstractmethod
from fastapi import Request
from backend2.state import ServerState
from backend2.runtime import ProjectRuntime
import asyncio
from backend2.process import Process

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from io import BytesIO
import zipstream
import os

class Game(ABC):

    def __init__(self, name, router, server):

        self.name = name
        self.router = router
        self.server = server

        # Path-Mapping
        self.config_path_mapping = {}
        self.savegame_path_mapping = {}

        # Pfade
        self.config_path = ""
        self.savegame_path = ""

        self.process = Process(f"python3 test_process.py", "python3", "test_process.py")
        self.runtime = ProjectRuntime(15, server.runtime, 1)

        self._state = ServerState.OFF
        self._state_lock = asyncio.Lock()

        # Routen hinzufügen
        self.register_routes()

    def getSavegamePathMapping(self):
        return self.savegame_path_mapping
    
    def getConfigPathMapping(self):
        return self.config_path_mapping
    
    def getSavegamePath(self):
        return self.savegame_path
    
    def getConfigPath(self):
        return self.config_path

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
        
        @self.router.get("/download2")
        async def download_zip(request: Request):

            print("Download2 angefordert")
            folder_to_zip = Path('/home/luca/gameserver/test_zip')
            zip_filename = "download.zip"

            z = zipstream.ZipFile(mode="w", compression=zipstream.ZIP_DEFLATED)

            for path in folder_to_zip.rglob("*"):
                if path.is_file():
                    z.write(path, arcname=path.relative_to(folder_to_zip))

            return StreamingResponse(
                z,
                media_type='application/zip',
                headers={
                    "Content-Disposition": f"attachment; filename={zip_filename}"
                }
            )





        

