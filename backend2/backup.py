import json
from datetime import datetime
import os
import shutil
from backend2.state import ServerState

import asyncio
import aiofiles

class Game_Backup():

    def __init__(self, project, backup_interval, savegame=True):

        self.project = project
        self.game = project.getGame()

        self.savegame = savegame
        self.default_backup_management_path = r"/mnt/data/gameserver/management.json"

        path_mapping = {}
        
        # Savegame-Backup oder Config-Backup
        if savegame:

            # Pfad zum Ordner, in dem die Backups gespeichert werden
            self.main_backup_dir_path = os.path.join(project.getBackuppath(), 'Saved')
            self.game_dir_path = self.game.getSavegamePath()
            path_mapping = self.game.getSavegamePathMapping()

        else:

            # Pfad zum Ordner, in dem die Backups gespeichert werden
            self.main_backup_dir_path = os.path.join(project.getBackuppath(), 'Config')
            self.game_dir_path = self.game.getConfigPath()
            path_mapping = self.game.getConfigPathMapping()

        # Zuordnungen von Dateien und Verzeichnissen im Spielordner und im Backupordner
        self.dir_paths_mapping = path_mapping["dirs"]
        self.file_paths_mapping = path_mapping["files"]

        # Pfad zur JSON, die die Backups verwaltet
        self.backup_management_path = os.path.join(self.main_backup_dir_path, 'management.json')

        # Mit Einheit = 15min: 15min, 30min, 1h, 2h, 4h, 8h, 1d, 2d, 3d, 1w || An diesen Stellen brechen die Slots auf und würden durch neuere Backups ersetzt werden (Das Backup wird auch versucht auf den nächsten Slot zu schieben)
        self.backup_slots_breakpoints = [1, 2, 4, 8, 16, 32, 96, 192, 288, 672]

        # Backup-Intervall in Sekunden
        self.interval = backup_interval

        # Autobackups im Intervall
        self._running = False

    # rekuriver Slotwechsel in der Verwaltungsstruktur
    def _pushSlot(self, management, slot_index):

        # Bis zum vorletzen Slot prüfen
        if slot_index + 1 < len(management):

            # Falls die vergangenen Backups (age) des nächsten Slots (+1) den Grenzwert überschreiten
            if management[slot_index+1]["age"] > self.backup_slots_breakpoints[slot_index+1]:

                # Versuchen für den nächsten Slot (+1) Platz zu machen: Falls der übernächste Slot (+2) den Grenzwert nicht überschreitet wird der nächste Slot (+1) entfernt
                self._pushSlot(management, slot_index+1)

                # Aktuellen Slot (+0) auf nächsten Slot (+1) schieben
                management[slot_index+1]["age"] = management[slot_index]["age"]
                management[slot_index+1]["path"] = management[slot_index]["path"]

    # Neues Backup zur Verwaltung hinzufügen // Slots in der Verwaltungsstruktur aktualisieren
    async def _async_addBackupToManagement(self, path):

        # Verwaltungsjson-Datei öffnen
        management = await self._async_readManagement()

        # Alter inkrementieren
        for backup in management:
            backup["age"] = backup["age"] + 1

        # Neuen Pfad anhängen
        self._pushSlot(management,  0)
        management[0]["age"] = 1
        management[0]["path"] = path

        # Aktuelle Backup-Ordner auslesen (um alte entfernen [nicht mehr verwendete] löschen zu können)
        paths = [backup["path"] for backup in management if backup["path"] != ""]

        # Änderungen speichern
        await self._async_writeManagement(management)

        # Aktuelle Backup-Ordner zurückgeben
        return paths
    
    # Neues Backup in Backupstruktur erstellen
    async def _async_addNewBackup(self):

        # Ordner mit aktueller Zeit vorbereiten
        new_dir_name = datetime.now().strftime("%d.%m.%Y_%H-%M-%S")
        new_dir_path = os.path.join(self.main_backup_dir_path, new_dir_name)

        path_exists = await asyncio.to_thread(os.path.exists, new_dir_path)

        # Ordner im Backup-Pfad erstellen, falls noch nicht vorhanden
        if not path_exists:  

            # Ordner erstellen
            await asyncio.to_thread(os.mkdir, new_dir_path)

            # Backup zur Verwaltung hinzufügen & Verwaltung aktualisieren
            dirs_in_management = await self._async_addBackupToManagement(new_dir_path)

            # Nicht mehr verwendete Backups löschen (Noch im Dateisystem, aber nicht mehr im Management)
            await asyncio.to_thread(self._sync_deleteOldBackupDirs, dirs_in_management)

        else:

            raise FileExistsError(f"Backup existiert bereits: {new_dir_path}")
        
        # Pfad des neuen Backup-Ordners zurückgeben
        return new_dir_path

    # Veraltete Backups löschen (Noch im Dateisystem, aber nicht mehr im Management)
    def _sync_deleteOldBackupDirs(self, dirs_in_management):

        # Aktuelle Ordner im Backuppfad vom Dateisystem abfragen
        current_dirs = [os.path.join(self.main_backup_dir_path, dir_name) for dir_name in os.listdir(self.main_backup_dir_path) if os.path.isdir(os.path.join(self.main_backup_dir_path, dir_name))]

        # Alle verwalteten Backups [Aktuell noch auf dem Dateisystem vorhanden, aber nicht mehr im Verwaltungssystem]
        removed_backup = [backup for backup in current_dirs if backup not in dirs_in_management]

        # Jedes Backup, welches veraltet ist, löschen
        for backup in removed_backup:
            if os.path.exists(backup):
                shutil.rmtree(backup)  

    # Liest die Verwaltungsstruktur (JSON) asynchron ein
    async def _async_readManagement(self):

        # Asynchron Management-Datei (JSON) öffnen
        async with aiofiles.open(self.backup_management_path, 'r', encoding='utf-8') as f:
            # Datei einlesen
            content = await f.read()
            # Zu JSON parsen
            return json.loads(content)

    # Überschreibt die Verwaltungsstruktur (JSON) asynchron mit neuen Daten
    async def _async_writeManagement(self, management):

        async with aiofiles.open(self.backup_management_path, 'w', encoding='utf-8') as f:
            # JSON als String
            content = json.dumps(management, indent=4, ensure_ascii=False)
            # Datei schreiben
            await f.write(content)

    # Ausgabe aller vorhandenen Backups mit dem geschätzten Alter
    async def async_getBackups(self):

        # Backup_Intervall in min
        backup_interval = self.interval // 60

        # Verwaltungsjson-Datei öffnen
        management = self._async_readManagement()

        # Backup mit dem dazugehörigen Alter 
        backups = [f"{os.path.relpath(backup["path"], self.main_backup_dir_path)}: {(backup["age"] - 1) * backup_interval // 60}:{((backup["age"] - 1) * backup_interval) % 60:02d}h - {backup["age"] * backup_interval // 60}:{(backup["age"] * backup_interval) % 60:02d}h" for backup in management if backup["path"] != ""]

        return backups
    
    # Neues Backup erstellen
    async def async_CreateBackup(self):
        
        # Spiel speichern
        if self.savegame:
            self.game.save()

            # Verzögerung, damit alle Dateien vollständig gespeichert wurde
            await asyncio.sleep(10)

        try:

            # Neuen Ordner für das Backup erstellen und in die Verwaltungsstruktur integrieren
            new_backup_path = await self._async_addNewBackup()
                
            # Backup von Verzeichnissen
            for dir in self.dir_paths_mapping:

                # Quell- und Zielverzeichnis aus Konfiguration extrahieren
                path_src = os.path.join(self.game_dir_path, dir["game"])
                path_dst = os.path.join(new_backup_path, dir["backup"])

                path_dst_dir = os.path.dirname(path_dst)
                # Erstellen fehlender Zwischenordner
                await asyncio.to_thread(os.makedirs, path_dst_dir, exist_ok=True)

                try:

                    # Verzeichnis ins Backup kopieren
                    await asyncio.to_thread(shutil.copytree, path_src, path_dst, dirs_exist_ok=True)
                    print(f"{path_src} nach {path_dst} kopiert.")

                except FileNotFoundError as e:

                    print(f"Vezeichnis {path_src}, welches für das Backup vorgesehen ist, exististiert nicht!")

            # Backup einzelner Dateien
            for file in self.file_paths_mapping:

                # Quell- und Zieldatei aus Konfiguration extrahieren
                path_src = os.path.join(self.game_dir_path, file["game"])
                path_dst = os.path.join(new_backup_path, file["backup"])

                path_dst_dir = os.path.dirname(path_dst)
                # Erstellen fehlender Zwischenordner
                await asyncio.to_thread(os.makedirs, path_dst_dir, exist_ok=True)

                try:

                    # Datei ins Backup kopieren
                    await asyncio.to_thread(shutil.copy2(path_src, path_dst))
                    print(f"{path_src} nach {path_dst} kopiert.")

                except FileNotFoundError:

                    print(f"Datei {path_src}, welche für das Backup vorgesehen ist, exististiert nicht!")

            # LastSave updaten
            if self.savegame:
                await self._async_updateLastSave()

            print(f"Backup wurde für {self.project.name} [{self.game.name}] erfolgreich erstellt!")

        except FileExistsError:

            print(f"Backup abgebrochen: Gleichnamiges Backup bereits vorhanden")


    async def _async_updateLastSave():
        print(f"LastSave angepasst")

    # Läd ein bestimmtes Backup in den Gameordner
    async def async_loadBackup(self, backup_index):

        print(f"Lade Backup #{backup_index}.")

        # Verwaltungsjson-Datei öffnen
        management = await self._async_readManagement()

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
            await asyncio.to_thread(os.makedirs,path_dst_dir, exist_ok=True)

            try:

                # Ordner im Game-Vezeichnis entfernen (falls dieser existiert), um Platz für das Verzeichnis aus dem Backup zu schaffen
                path_exists = await asyncio.to_thread(os.path.exists, path_dst)
                if path_exists:
                    await asyncio.to_thread(shutil.rmtree, path_dst)  

                # Verzeichnis aus dem Backup kopieren
                await asyncio.to_thread(shutil.copytree, path_src, path_dst, dirs_exist_ok=True)
                print(f"{path_src} nach {path_dst} kopiert.")

            except FileNotFoundError:

                print(f"Verzeichnis {path_src} wurde im Backup nicht gefunden!")

        # Laden einzelner Dateien aus dem Backup || Dateien werden nicht entfernt, wenn keine passende Datei im Backup ist
        for file in self.file_paths_mapping:

            # Quell- und Zieldatei aus Konfiguration extrahieren
            path_src = os.path.join(backup_dir_path, file["backup"])
            path_dst = os.path.join(self.game_dir_path, file["game"])
            

            # Erstellen fehlender Zwischenordner
            path_dst_dir = os.path.dirname(path_dst)
            await asyncio.to_thread(os.makedirs, path_dst_dir, exist_ok=True)

            try:

                # Datei aus dem Backup kopieren
                await asyncio.to_thread(shutil.copy2, path_src, path_dst)
                print(f"{path_src} nach {path_dst} kopiert.")

            except FileNotFoundError:

                print(f"Datei {path_src} existiert nicht im Backup!")
        
        print(f"Backup #{backup_index} geladen")

    def sync_createBackupPath(self):

        # Backup Pfad erstellen
        os.makedirs(self.main_backup_dir_path)

        # Management Datei kopieren aus dem Default
        shutil.copy2(self.default_backup_management_path, self.backup_management_path)


    # Startet das Backup im Intervall
    async def _autobackup(self):

        # Intervall abwarten
        await asyncio.sleep(self.interval)

        # Solange das Auto-Backup eingeschaltet ist
        while self._running:

            current_state = self.game._state

            if current_state == ServerState.RUNNING:

                # Backup erstellen
                    await self.async_CreateBackup()

            else:

                print(f"Es wird kein Auto-Backup erstellt, da der Server im falschen Zustand ist: {current_state}")

            # Intervall abwarten
            await asyncio.sleep(self.interval)

    # Laufzeitmessung starten
    def startAutobackup(self):

        # Intervall läuft nicht
        if not self._running:

            print(f"Backup-Intervall startet.")

            # Task ausführen
            self._running = True
            asyncio.create_task(self._autobackup())

    # Laufzeitmessung beenden
    async def stopAutobackup(self):

        # Intervall läuft
        if self._running:

            print(f"Backup-Intervall stoppt.")

            # Intervall beenden
            self._running = False




