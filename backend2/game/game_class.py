from abc import ABC, abstractmethod

class Game(ABC):

    def __init__(self, name, router):

        self.name = name
        self.router = router
        self.register_routes()

    @abstractmethod
    def save(self):
        pass

    @abstractmethod
    def register_routes(self):
        pass