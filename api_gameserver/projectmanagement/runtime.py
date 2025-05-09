from datetime import datetime
import threading
import time

from datenbank.db_utils import DB_Pool

class Runtime():

    # Liste aller laufenden Games
    active = []

    # Leerlaufzeitmessung
    idle = None

    def __init__(self, interval, project_nr=0, idle=False):

        # Startzeit der Messung (0 bedeutet noch nicht gemessen)
        self.start_time = 0

        # Ist es eine Leerlaufmessung?
        self.idle = idle

        # Projektnummer, um die Laufzeit anzupassen
        self.project_nr = project_nr
        
        # Intervall
        self._running = False
        self._thread = None
        self.interval = interval

        # Idle Objekt als Leerlaufobjekt der Klasse setzen
        if idle:

            print(idle)
            self.start_interval()

    # Startet die Laufzeitmessung im Intervall
    def _run(self):

        # Solange das Auto-Backup eingeschaltet ist
        while self._running:

            # Backup erstellen
            self.update_time()

            # Intervall abwarten
            time.sleep(self.interval)

    # Schreibt die Laufzeit in die Datenbank
    def _update_db(self, diff_time):

        pool = DB_Pool.get_db_pool()

        conn = pool.get_connection()

        cursor = conn.cursor()

        try:

            if self.idle:
    
                # Serverlaufzeit Update
                print(f"Server-Leerlaufzeit wird um {diff_time} erhöht.")
                cursor.execute('UPDATE idle SET Laufzeit = Laufzeit + %s WHERE device = %s', (diff_time, "server"))
            
            else:

                print(f"Projekt-Laufzeit {self.project_nr} wird um {diff_time} erhöht.")
                cursor.execute('UPDATE projekte SET Laufzeit = Laufzeit + %s WHERE ProjektID = %s', (diff_time, self.project_nr))

            conn.commit()

        except Exception as e:

            print(f"Fehler beim aktualisieren von Laufzeiten: {e}")
            conn.rollback()

        finally:

            # Cursor und Verbindung schließen
            cursor.close()

            pool.return_connection(conn)

    def get_db(self):

        print(f"Das Projekt {self.project_nr} läuft seit xx:xxh")

    # Laufzeit-Messungs Intervall starten
    def start_interval(self):

    
        # Nur, wenn noch kein Backup-Intervall läuft
        if not self._running:

            print(f"Starte Intervall {self.project_nr}; Idle: {self.idle}; Active: {Runtime.active}")

            if not self.idle:

                Runtime.idle.stop_interval()
                Runtime.active.append(self)

            # Thread starten, welcher _run ausführt
            print("Starte Laufzeit-Intervall")
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()


    # Laufzeit-Messungs Intervall beenden
    def stop_interval(self):

        print(f"Stoppe Laufzeit Intervall {self.project_nr}; Idle: {self.idle}; Active: {Runtime.active}")

        if self._running:

            if not self.idle:

                print(self.idle)

                print(self.project_nr)
                Runtime.active.remove(self)

                if len(Runtime.active) == 0:

                    Runtime.idle.start_interval()

            # Thread beenden
            self._running = False
            self._thread = None

            self.update_time()

            self.start_time = 0

    def update_time(self):

        # Aktuelle Zeit
        endtime = datetime.now()

        diff_time_seconds = 0
        if self.start_time != 0:

            # Differenz zur letzten Messung
            diff_time =  endtime - self.start_time
            diff_time_seconds = diff_time.total_seconds()

        # Differenz in die Datenbank schreiben
        self._update_db(diff_time_seconds)

        # Alten Enzeitpunkt zum neuen Startzeitpunkt für die nächste Messung machen
        self.start_time = endtime

    def __del__(self):

        if self._running:
            self.stop_interval()

    def set_idle(time):

        Runtime.idle = Runtime(time, idle=True)

    def get_idle():

        return Runtime.idle
    

    

    