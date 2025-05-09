from backend2.game.game import Game
from fastapi import APIRouter, Request

class Satisfactory(Game):

    def __init__(self):

        super().__init__(f"Satisfactory", APIRouter(prefix="/api/satisfactory"))

    def save(self):
        print("Spiel speichert")

    def register_specific_routes(self):
        
        @self.router.get("/save")
        async def get_info(request: Request):
            self.save()

