from datetime import datetime
import asyncio
import time
from abc import ABC, abstractmethod
from backend2.database import getAsyncDatabaseConnection

class Runtime(ABC):

    def __init__(self, interval):

        # Startzeit der Messung (0: noch nicht gemessen)
        self.start_time = 0

        # Intervall
        self._running = False
        self.interval = interval

    # Zeit in Datenbank anpassen
    @abstractmethod
    async def _database_update(self, seconds):
        pass

    # Laufzeitmessung starten
    def start(self):

        # Intervall läuft nicht
        if not self._running:

            # Task ausführen
            self._running = True
            asyncio.create_task(self.update_interval())

    # Laufzeitmessung beenden
    async def stop(self):

        # Intervall läuft
        if self._running:

            # Intervall beenden
            self._running = False

            # Update
            await self.update()

            # Nicht aktive Messung
            self.start_time = 0

    # Intervall
    async def update_interval(self):

        # Solange das Auto-Backup eingeschaltet ist
        while self._running:

            # Backup erstellen
            await self.update()

            # Intervall abwarten
            await asyncio.sleep(self.interval)

    # Zeit anpassen
    async def update(self):

        # Aktuelle Zeit
        endtime = datetime.now()

        # Noch nicht gemessen?
        if self.start_time != 0:


            diff_time_seconds = 0

            # Differenz zur letzten Messung
            diff_time =  endtime - self.start_time
            diff_time_seconds = diff_time.total_seconds()

            # Differenz in die Datenbank schreiben
            await self._database_update(diff_time_seconds)

        # Alten Enzeitpunkt zum neuen Startzeitpunkt für die nächste Messung machen
        self.start_time = endtime

class IdleRuntime(Runtime):

    def __init__(self, interval):

        # Runtime
        super().__init__(interval)

        # Aktive Projekt-Runtimes
        self.active = []

        # Laufzeitmessung im Leerlauf starten
        self.start()

    # Laufzeit eines Projektes stoppen
    async def deactivate(self, runtime):

        # Nur Objekte der Klasse ProjectRuntime -> Nur Laufzeit aktiver Projekte
        if isinstance(runtime, ProjectRuntime):

            # Wenn Laufzeit des Projekts zurzeit aktiv ist
            if runtime in self.active:

                # Runtime stoppen
                await runtime.stop()
                self.active.remove(runtime)

                # Keine aktive Projekt-Runtime aktiv: Leerlaufmessung (Idle) startet
                if(len(self.active) == 0):
                    self.start()

        else:
            raise TypeError("Kein Game!")
    
    # Laufzeit eines Projektes starten
    async def activate(self, runtime):
            
        # Nur Objekte der Klasse ProjectRuntime -> Nur Laufzeit aktiver Projekte
        if isinstance(runtime, ProjectRuntime):

            # Wenn Laufzeit des Projekts zurzeit inaktiv ist
            if runtime not in self.active:

                # Zurzeit in Leerlaufmessung (Idle): Leerlaufmessung wird beendet
                if(len(self.active) == 0):
                    await self.stop()

                # Runtime starten
                self.active.append(runtime)
                runtime.start()

        else:
            raise TypeError("Kein Game!")
        
    # Schreibt die Laufzeit in die Datenbank
    async def _database_update(self, seconds):

        # conn = await getAsyncDatabaseConnection()

        try:

            print(f"Server-Leerlaufzeit wird um {seconds} erhöht.")
            # await conn.execute('UPDATE idle SET Laufzeit = Laufzeit + $1 WHERE device = $2', seconds, "server")

        except Exception as e:

            print(f"Fehler beim Aktualisieren von Server-Leerlaufzeit: {e}")

        finally:

            # Cursor und Verbindung schließen
            # await conn.close()
            pass
    
class ProjectRuntime(Runtime):

    def __init__(self, interval, idle, project_nr):

        # Runtime
        super().__init__(interval)

        # Projektnummer, um die Laufzeit anzupassen
        self.project_nr = project_nr

        # Leerlauf-Messung
        self.idle = idle

    async def start_runtime(self):

        # Starten der Projekt-Laufzeitmessung
        await self.idle.activate(self)

    async def stop_runtime(self):

        # Stoppen der Projekt-Laufzeitmessung
        await self.idle.deactivate(self)

    # Schreibt die Laufzeit in die Datenbank
    async def _database_update(self, seconds):

        # conn = await getAsyncDatabaseConnection()

        try:

            print(f"Projekt-Laufzeit {self.project_nr} wird um {seconds} erhöht.")
            # await conn.execute('UPDATE projekte SET Laufzeit = Laufzeit + $1 WHERE ProjektID = $2', seconds, self.project_nr)

        except Exception as e:

            print(f"Fehler beim Aktualisieren von Projekt-Laufzeit: {e}")

        finally:

            # Cursor und Verbindung schließen
            # await conn.close()
            pass


    

    