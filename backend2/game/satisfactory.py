from backend2.game.game import Game
from fastapi import APIRouter, Request

class Satisfactory(Game):

    def __init__(self, server):

        super().__init__(name=f"Satisfactory", router=APIRouter(prefix="/api/satisfactory"), server=server)

    def save(self):
        print("Spiel speichert")

    def register_specific_routes(self):
        
        @self.router.get("/save2")
        async def get_info(request: Request):
            self.save()

