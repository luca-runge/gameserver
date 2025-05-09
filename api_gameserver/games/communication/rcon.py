import asyncio
import socket
import struct

######
# Danke ChatGPT
######

class RCON:
    
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.socket = None
        self.request_id = 0

    # Asynchrone Ausführung des Connects
    async def async_connect(self):
        
        return await asyncio.to_thread(self.sync_connect)
    
    def sync_connect_send_close(self, command):

        response = None

        # Verbinden
        if self.sync_connect():

            # Befehl mit Antwort
            response = self.sync_send_command(command)

        # Verbindung schließen
        self.close()

        # Rückgabe
        return response

    
    async def async_connect_send_close(self, command):

        response = None

        # Verbinden
        if await self.async_connect():

            # Befehl mit Antwort
            response = await self.async_send_command(command)

        # Verbindung schließen
        self.close()

        # Rückgabe
        return response
    
    # Synchrone Verbindung und Authentifizierung
    def sync_connect(self) -> bool:

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(3)
        try:
            self.socket.connect((self.host, self.port))
            return self._authenticate()
        except socket.error as e:
            print(f"RCON: Verbindungsfehler zum Server")
            return False

    # Authentifizierung 
    def _authenticate(self) -> bool:

        # Authentifizieren mit Password
        response = self._send_packet(3, self.password)  # 3 = Auth-Login

        # Erfolgreich, wenn ID ungleich -1
        connection_success = response.get("id", -1) != -1 

        # Rückgabe
        if connection_success:
            return True
        else:
            print(f"RCON-Authentifizierungsfehler")
            return False

    # Asynchron einen Befehl zum Server senden
    async def async_send_command(self, command: str) -> str:
        
        # Befehl an den Server senden und Rückgabe der Antwort
        return await asyncio.to_thread(self.sync_send_command, command)

    # Synchron einen Befehl zum Server senden
    def sync_send_command(self, command: str) -> str:
        
        # Befehl an den Server senden
        response = self._send_packet(2, command)  # 2 = Execute Command

        # Rückgabe der Antwort
        return response.get("body", "Fehler beim Abrufen der Antwort")

    def _send_packet(self, packet_type: int, body: str) -> dict:
        """Sendet ein RCON-Paket und gibt die Antwort als Dictionary zurück."""
        self.request_id += 1
        payload = struct.pack("<ii", self.request_id, packet_type) + body.encode() + b"\x00\x00"
        packet = struct.pack("<i", len(payload)) + payload

        self.socket.sendall(packet)

        # Antwort empfangen
        response_data = self._receive_packet()
        return response_data

    def _receive_packet(self) -> dict:
        """Empfängt und verarbeitet ein RCON-Paket."""
        try:
            size_data = self.socket.recv(4)
            if not size_data:
                return {}

            size = struct.unpack("<i", size_data)[0]
            data = self.socket.recv(size)

            if len(data) < 8:
                return {}

            req_id, packet_type = struct.unpack("<ii", data[:8])
            body = data[8:-2].decode(errors="ignore")

            return {"id": req_id, "type": packet_type, "body": body}

        except socket.timeout:
            return {"id": -1, "body": "Timeout beim Empfang"}
        except Exception as e:
            return {"id": -1, "body": f"Fehler: {e}"}

    # Verbindung schließen
    def close(self):
        if self.socket:
            self.socket.close()
            self.socket = None
