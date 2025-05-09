import queue
import requests


# Senden von API Anfragen an andere Geräte
class API_Send:

    def __init__(self, host, queue_json_path=None):

        # Zustand, ob das Gerät erreichbar ist
        self.online = True

        # Host
        self.host = host

        # Warteschlange JSON
        # self.queue = queue.Queue()

    def queue_abarbeiten(self):

        status = self.ist_online()

        while self.queue.not_empty:

            req = self.queue.get()

            url = req['url']
            methode = req['methode']
            header = req['header']
            data = req['data']

    def ist_online(self):

        status = False
        
        try:
            response = requests.get(self.host, timeout=1) 
            
            if response.status_code == 200:
                status = True

        finally:

            return status


    


