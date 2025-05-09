import json
from datetime import datetime
import os
import shutil
from projectmanagement.state import ServerState

import threading
import time

class Game_Backup():

    def __init__(self, management_json_path, backup_path, game_path, path_mapping_path, backup_interval, gameserver_state_function, save_function=None, update_last_save_function=None ):

        self.gameserver_state_function = gameserver_state_function

        self.default_backup_management_path = r"/mnt/data/gameserver/management.json"

        # Pfad zur JSON, die die Backups verwaltet
        self.backup_management_path = management_json_path

        # Pfad zum Ordner, in dem die Backups gespeichert werden
        self.main_backup_dir_path = backup_path

        # Dateien und Ordner, die gebackupt werden sollen
        self.game_dir_path = game_path

        # Zuordnungen von Dateien und Verzeichnissen im Spielordner und im Backupordner
        self.dir_paths_mapping = self._read_path_mapping(path_mapping_path)["dirs"]
        self.file_paths_mapping = self._read_path_mapping(path_mapping_path)["files"]

        # Mit Einheit = 15min: 15min, 30min, 1h, 2h, 4h, 8h, 1d, 2d, 3d, 1w || An diesen Stellen brechen die Slots auf und würden durch neuere Backups ersetzt werden (Das Backup wird auch versucht auf den nächsten Slot zu schieben)
        self.backup_slots_breakpoints = [1, 2, 4, 8, 16, 32, 96, 192, 288, 672]

        # Backup-Intervall in Sekunden
        self.interval = backup_interval

        # Funktion, welche das Spiel vor dem Backup speichert
        self.save_function = save_function

        # Funktion, welche Last Save in der Datenbank aktualisiert
        self.update_last_save_function = update_last_save_function

        # Autobackups im Intervall
        self._running = False
        self._thread = None

    # rekuriver Slotwechsel in der Verwaltungsstruktur
    def _push_slot(self, management, slot_index):

        # Bis zum vorletzen Slot prüfen
        if slot_index + 1 < len(management):

            # Falls die vergangenen Backups (age) des nächsten Slots (+1) den Grenzwert überschreiten
            if management[slot_index+1]["age"] > self.backup_slots_breakpoints[slot_index+1]:

                # Versuchen für den nächsten Slot (+1) Platz zu machen: Falls der übernächste Slot (+2) den Grenzwert nicht überschreitet wird der nächste Slot (+1) entfernt
                self._push_slot(management, slot_index+1)

                # Aktuellen Slot (+0) auf nächsten Slot (+1) schieben
                management[slot_index+1]["age"] = management[slot_index]["age"]
                management[slot_index+1]["path"] = management[slot_index]["path"]

    # Neues Backup zur Verwaltung hinzufügen // Slots in der Verwaltungsstruktur aktualisieren
    def _add_backup_to_management(self, path):

        # Verwaltungsjson-Datei öffnen
        management = {}
        with open(self.backup_management_path, "r", encoding="utf-8") as file:
            management = json.load(file)

        # Alter inkrementieren
        for backup in management:
            backup["age"] = backup["age"] + 1

        # Neuen Pfad anhängen
        self._push_slot(management,  0)
        management[0]["age"] = 1
        management[0]["path"] = path

        # Aktuelle Backup-Ordner auslesen (um alte entfernen [nicht mehr verwendete] löschen zu können)
        paths = [backup["path"] for backup in management if backup["path"] != ""]

        # Änderungen speichern
        with open(self.backup_management_path, "w", encoding="utf-8") as file:
            json.dump(management, file, indent=4, ensure_ascii=False)

        # Aktuelle Backup-Ordner zurückgeben
        return paths
    
    # Neues Backup in Backupstruktur erstellen
    def _add_backup(self):

        # Ordner mit aktueller Zeit vorbereiten
        new_dir_name = datetime.now().strftime("%d.%m.%Y_%H-%M-%S")
        new_dir_path = os.path.join(self.main_backup_dir_path, new_dir_name)

        # Ordner im Backup-Pfad erstellen, falls noch nicht vorhanden
        if not os.path.exists(new_dir_path):  
            os.mkdir(new_dir_path)  

            # print("Ordner erstellt")

            # Backup zur Verwaltung hinzufügen & Verwaltung aktualisieren
            current_backup_paths = self._add_backup_to_management(new_dir_path)

            # Nicht mehr verwendete Backups löschen
            self._delete_old_backup_dirs(current_backup_paths)

        else:

            new_dir_path = ""
        
        # Pfad des neuen Backup-Ordners zurückgeben
        return new_dir_path

    # Veraltete Backups löschen
    def _delete_old_backup_dirs(self, target_dirs):

        # Aktuelle Ordner im Backuppfad vom Dateisystem abfragen
        current_dirs = [os.path.join(self.main_backup_dir_path, dir_name) for dir_name in os.listdir(self.main_backup_dir_path) if os.path.isdir(os.path.join(self.main_backup_dir_path, dir_name))]

        # Alle verwalteten Backups [Aktuell noch auf dem Dateisystem vorhanden, aber nicht mehr im Verwaltungssystem]
        removed_backup = [backup for backup in current_dirs if backup not in target_dirs]

        # Jedes Backup, welches veraltet ist, löschen
        for backup in removed_backup:
            if os.path.exists(backup):
                shutil.rmtree(backup)  

    # Startet das Backup im Intervall
    def _run(self):

        # Intervall abwarten
        time.sleep(self.interval)

        # Solange das Auto-Backup eingeschaltet ist
        while self._running:

            current_state = self.gameserver_state_function()

            if current_state == ServerState.RUNNING:

                # Backup erstellen
                self.create_backup()

            else:

                print(f"Es wird kein Auto-Backup erstellt, da der Server im falschen Zustand ist: {current_state}")

            # Intervall abwarten
            time.sleep(self.interval)

    # Liest die Verwaltungsstruktur (JSON) ein
    def _read_management(self):

        management = {}
        with open(self.backup_management_path, "r", encoding="utf-8") as file:
            management = json.load(file)

        return management
    
    # Überschreibt die Verwaltungsstruktur (JSON) mit neuen Daten
    def _write_management(self, management):

        # Änderungen speichern
        with open(self.backup_management_path, "w", encoding="utf-8") as file:
            json.dump(management, file, indent=4, ensure_ascii=False)

    # Liest die Zuordnung von Dateien und Verzeichnissen im Backup- und Game-Ordner aus der Konfiguration
    def _read_path_mapping(self, path_mapping_path):

        path_mapping = {}
        with open(path_mapping_path, "r", encoding="utf-8") as file:
            path_mapping = json.load(file)

        return path_mapping

    # Setzen einer Speicherfunktion: Spiel vor dem Backup speichern
    def set_save_function(self, save_function):
        self.save_function = save_function

    # Ausgabe aller vorhandenen Backups mit dem geschätzten Alter
    def get_backups(self):

        # Backup_Intervall in min
        backup_interval = self.interval // 60
        print(backup_interval)

        # Verwaltungsjson-Datei öffnen
        management = {}
        with open(self.backup_management_path, "r", encoding="utf-8") as file:
            management = json.load(file)

        # Backup mit dem dazugehörigen Alter 
        ausgabe = [f"{os.path.relpath(backup["path"], self.main_backup_dir_path)}: {(backup["age"] - 1) * backup_interval // 60}:{((backup["age"] - 1) * backup_interval) % 60:02d}h - {backup["age"] * backup_interval // 60}:{(backup["age"] * backup_interval) % 60:02d}h" for backup in management if backup["path"] != ""]

        return ausgabe
    
    # Erstellt das vollständige Backup
    def create_backup(self, save_game=True):

        # Spiel speichern
        if save_game and self.save_function:

            # Spiel speichern
            self.save_function()

            # Verzögerung, damit alle Dateien vollständig gespeichert wurde
            time.sleep(10)

        # Ein neuen Back-Ordner erstellen und in die Verwaltungsstruktur integrieren
        backup_dir_path = self._add_backup()

        if backup_dir_path == "":

            print("Backup abgebrochen, da bereits ein gleichnamiges Backup vorhanden ist.")

            return

        # Backup ganzer Verzeichnisse
        for dir in self.dir_paths_mapping:

            # Quell- und Zielverzeichnis aus Konfiguration extrahieren
            path_src = os.path.join(self.game_dir_path, dir["game"])
            path_dst = os.path.join(backup_dir_path, dir["backup"])

            # Erstellen fehlender Zwischenordner
            path_dst_dir = os.path.dirname(path_dst)
            os.makedirs(path_dst_dir, exist_ok=True)

            print(f"Ordner DST: {path_dst}")
            print(f"Ordner SRC: {path_src}")

            try:

                # Verzeichnis ins Backup kopieren
                shutil.copytree(path_src, path_dst, dirs_exist_ok=True)
                print(f"{path_src} nach {path_dst} kopiert.")

            except FileNotFoundError as e:

                print(f"Vezeichnis, welches für das Backup vorgesehen ist, exististiert nicht! {e}")

        # Backup einzelner Dateien
        for file in self.file_paths_mapping:

            # Quell- und Zieldatei aus Konfiguration extrahieren
            path_src = os.path.join(self.game_dir_path, file["game"])
            path_dst = os.path.join(backup_dir_path, file["backup"])

            # Erstellen fehlender Zwischenordner
            path_dst_dir = os.path.dirname(path_dst)
            os.makedirs(path_dst_dir, exist_ok=True)

            try:

                # Datei ins Backup kopieren
                shutil.copy2(path_src, path_dst)
                print(f"{path_src} nach {path_dst} kopiert.")

            except FileNotFoundError:

                print("Datei, welcher für das Backup vorgesehen ist, exististiert nicht!")

        # Last-Saved in Datenbank aktualisieren
        if self.update_last_save_function:

            self.update_last_save_function()
        
        print("Backup erstellt")

    # Läd ein bestimmtes Backup in den Gameordner
    def load_backup(self, backup_index):

        print(f"Lade Backup #{backup_index}.")

        # Verwaltungsjson-Datei öffnen
        management = {}
        with open(self.backup_management_path, "r", encoding="utf-8") as file:
            management = json.load(file)

        if backup_index > len(management) or management[backup_index]["path"] == "":

            print(f"Das Backup #{backup_index} existiert nicht!")
            return
        
        print(f"Backup #{backup_index} wird geladen. Der Pfad beträgt {management[backup_index]["path"]} und das Alter {management[backup_index]["age"]}.")

        backup_dir_path = management[backup_index]["path"]

        # Laden der Verzeichnisse aus dem Backup || Verzeichnisse im Game-Ordner werden entfernt, wenn kein passender Ordner im Backup ist
        for dir in self.dir_paths_mapping:

            # Quell- und Zielverzeichnis aus Konfiguration extrahieren
            path_src = os.path.join(backup_dir_path, dir["backup"])
            path_dst = os.path.join(self.game_dir_path, dir["game"])
            

            # Erstellen fehlender Zwischenordner
            path_dst_dir = os.path.dirname(path_dst)
            os.makedirs(path_dst_dir, exist_ok=True)

            try:

                # Game-Vezeichnis entfernen, um Platz für das Verzeichnis aus dem Backup zu schaffen
                if os.path.exists(path_dst):
                    shutil.rmtree(path_dst)  

                # Verzeichnis aus dem Backup kopieren
                shutil.copytree(path_src, path_dst, dirs_exist_ok=True)
                print(f"{path_src} nach {path_dst} kopiert.")

            except FileNotFoundError:

                print("Verzeichnis wurde im Backup nicht gefunden!")

        # Laden einzelner Dateien aus dem Backup || Dateien werden nicht entfernt, wenn keine passende Datei im Backup ist
        for file in self.file_paths_mapping:

            # Quell- und Zieldatei aus Konfiguration extrahieren
            path_src = os.path.join(backup_dir_path, file["backup"])
            path_dst = os.path.join(self.game_dir_path, file["game"])
            

            # Erstellen fehlender Zwischenordner
            path_dst_dir = os.path.dirname(path_dst)
            os.makedirs(path_dst_dir, exist_ok=True)

            try:

                # Datei aus dem Backup kopieren
                shutil.copy2(path_src, path_dst)
                print(f"{path_src} nach {path_dst} kopiert.")

            except FileNotFoundError:

                print("Datei existiert nicht im Backup!")
        
        print("Backup geladen")

    def create_backup_path(self):

        # Backup Pfad erstellen
        os.makedirs(self.main_backup_dir_path)

        # Management Datei kopieren aus dem Default
        shutil.copy2(self.default_backup_management_path, self.backup_management_path)

    # Backup Intervall
    def start_backup_interval(self):
        
        # Nur, wenn noch kein Backup-Intervall läuft
        if not self._running:

            # Thread starten, welcher _run ausführt
            print("Starte Backup-Intervall")
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    # Backup Intervall beenden
    def stop_backup_interval(self, create_Backup=True):

        if self._running:

            print("Stoppe Backup-Intervall")

            if create_Backup:

                # Backup erstellen
                self.create_backup(save_game=False)

            # Thread beenden
            self._running = False
            self._thread = None

#test_game = Game_Backup(r"C:\Users\lucar\Desktop\BackupTest\Saved\config.json", r"C:\Users\lucar\Desktop\BackupTest\Saved", r"C:\Users\lucar\Desktop\BackupTest\Test_Game", r"C:\Users\lucar\Desktop\BackupTest\path_mapping.json", 1, None)    
#test_game.get_backup_time()


#def test():

#    print("Erfolgreiche")

#test_game.set_save_function(test)

#test_game.create_backup()

# print(test_game.get_backups())

# test_game.load_backup(0)

#test_game.start_backup_interval()

#time.sleep(150)

#test_game.stop_backup_interval()



