from abc import ABC, abstractmethod
from fastapi import Request

class Game(ABC):

    def __init__(self, name, router):

        self.name = name
        self.router = router

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
            print("Game speichert")

