# Spiele: Superklasse

from projectmanagement.project import Project
from datenbank.db_utils import DB_Pool
from projectmanagement.cli import CLI_CMD
from projectmanagement.state import ServerState

import os
import time
import asyncio
import re

import threading

class Game:

    def __init__(self, gamename, command, search_name, search_cmdline, config_path_mapping_path, saved_path_mapping_path, config_backup_interval, saved_backup_interval, config_state_zero_path, saved_state_zero_path, save_function, exit_function, send_function, in_use_function, initialize_fuction, before_start_function, after_start_function, server):

        # Kein Server am laufen
        self._state = ServerState.OFF

        # Lock für den kritischen Bereich
        self._state_lock = asyncio.Lock()

        self.check_in_use_interval = 600
        self._running = False
        self._thread = None

        self.in_use = True

        self.server = server

        self.save_function = save_function
        self.exit_function = exit_function
        self.send_function = send_function
        self.in_use_function = in_use_function
        self.initialize_function = initialize_fuction
        self.before_start_function = before_start_function
        self.after_start_function = after_start_function

        self.gamename = gamename

        self.config_path_mapping_path = config_path_mapping_path
        self.saved_path_mapping_path = saved_path_mapping_path

        self.saved_backup_interval = saved_backup_interval
        self.config_backup_interval = config_backup_interval

        self.config_state_zero_path = config_state_zero_path
        self.saved_state_zero_path = saved_state_zero_path


        pool = DB_Pool.get_db_pool()

        conn = pool.get_connection()

        cursor = conn.cursor()

            # Serverlaufzeit Update
        
        cursor.execute('SELECT ProjektID, Projektname, TemplatePfad, DefaultBackupPfad, ConfigPfad, SaveGamesPfad, initialisiert FROM projekte JOIN spiel USING(SpielID) WHERE Spielname = %s and LastSave is not null ORDER BY LastSave DESC LIMIT 1', (gamename,))
        
        row = cursor.fetchone()

        current_project_nr = row[0]
        projectname = row[1]
        self.game_template_path = row[2]
        self.game_default_backup_path = row[3]
        self.game_config_path = row[4]
        self.game_savegames_path = row[5]
        self.initialized = row[6]

        print(f"Das aktuelle {gamename} Projekt ist {current_project_nr}.")
        
        # Cursor und Verbindung schließen
        cursor.close()

        pool.return_connection(conn)

        self.project = Project(current_project_nr, self.game_default_backup_path, self.game_savegames_path, self.game_config_path, self.saved_path_mapping_path, self.config_path_mapping_path, self.saved_backup_interval, self.config_backup_interval, projectname, self.save_function, self.game_template_path, self.read_server_state_unsafe)

        zusatzparameter = "TheIsland?listen"
        print(f"Eigentlicher Command: {command}")

        replaced_command = command.replace("%ZUSATZ%", zusatzparameter)

        print(f"Gesetzter Command: {replaced_command}")
        self.cmd = CLI_CMD(replaced_command, search_name, search_cmdline)

        # Versuche Reattach

        reattached = self.cmd.reattach()

        if reattached:

            self._state = ServerState.STARTING

            # Config-Backup starten
            self.project.config_backup.start_backup_interval()

            # SaveGame-Backup starten
            self.project.backup.start_backup_interval()

            # Laufzeit messen
            self.project.runtime.start_interval()

            print(f"Der laufende Game-Prozess hat die ProzessID {self.cmd.get_pid()}.")

            self.start_check_use_interval()

            self._state = ServerState.RUNNING




    def load_project(self, name):

        pool = DB_Pool.get_db_pool()

        conn = pool.get_connection()

        cursor = conn.cursor()
        
        cursor.execute('SELECT ProjektID, Projektname FROM projekte JOIN spiel USING(SpielID) WHERE Spielname = %s and Projektname = %s and ProjektID <> %s ', (self.gamename, name, self.project.project_nr))
        
        row = cursor.fetchone()

        if row:

            project_nr = row[0]
            projectname = row[1]

            print(f"Es wird das Projekt {projectname} [{project_nr}] geladen. [Spiel: {self.gamename}]")
            
            # Cursor und Verbindung schließen
            cursor.close()

            pool.return_connection(conn)

            project = Project(project_nr, self.game_default_backup_path, self.game_savegames_path, self.game_config_path, self.saved_path_mapping_path, self.config_path_mapping_path, self.saved_backup_interval, self.config_backup_interval, projectname, self.save_function, self.game_template_path, self.read_server_state_unsafe)

            print(f"Projekt wird gesetzt.")

            # Projekt als aktuelles Projekt setzen
            self.project = project


            # Prüfen, ob das Projekt bereits initialisiert wurde.
            if project.is_initialized():
                
                # Backup laden
                self.project.config_backup.load_backup(0)
                self.project.backup.load_backup(0)
                self.project.update_last_saved()

            else:

                # Projekt initialisieren
                print("Initialisiere Projekt")
                self.project.initialize_project(self.config_state_zero_path, self.saved_state_zero_path)

                # Initialisierungfunktion: z.B. Spielsession-Name setzen, etc. 
                if self.initialize_function:
                    self.initialize_function()

                self.project.backup.create_backup(save_game=False)
                self.project.config_backup.create_backup(save_game=False)

                
            self.initialized = True

            return True


            #####################
            # Nachricht an Discord Bot, um die Rollen zu aktualisieren.
            #####################

        else:

            print(f"Es wurde kein Projekt {name} für das Spiel {self.gamename} gefunden!")
            return False


    def start(self):

        print("Starte SPIEL")

        self.project.backup.start_backup_interval()
        self.project.config_backup.start_backup_interval()
        self.project.runtime.start_interval()
        self.cmd.start_detached()



        print(f"Der gestartete Prozess hat die ProzessID {self.cmd.get_pid()}.")


    def stop(self):

        print("Stoppe SPIEL")

        print(self.cmd.get_child_pids())

        self.cmd.stop()

        self.project.backup.stop_backup_interval()
        self.project.config_backup.start_backup_interval()
        self.project.runtime.stop_interval()
        

    def running(self):

        running = False

        if self._state != ServerState.OFF:

            running = True

        return running
    
    async def async_load_project(self, name):

        # Zustandattribut sperren
        async with self._state_lock:

            # Prüfen, ob der Server ausgeschaltet ist
            if self._state != ServerState.OFF:

                print(f"Projekt kann nicht geladen werden, da der Server einen unpassenden Zustand hat.")
                return
            
            # Zustand: Laden
            self._state = ServerState.LOADING

        result = await asyncio.to_thread(self.load_project, name)

        # Zustandattribut sperren
        async with self._state_lock:

            # Zustand: Ausgeschaltet
            self._state = ServerState.OFF

        return result

    async def async_load_backup(self, backup_nr, config=False):

        # Zustandattribut sperren
        async with self._state_lock:

            # Prüfen, ob der Server ausgeschaltet ist
            if self._state != ServerState.OFF:

                print(f"Backup kann nicht geladen werden, da der Server einen unpassenden Zustand hat.")
                return
            
            # Zustand: Laden
            self._state = ServerState.LOADING

        # Savegame-Backup oder Config-Backup 
        if not config:

            await asyncio.to_thread(self.project.backup.load_backup, backup_nr)

        else:

            await asyncio.to_thread(self.project.config_backup.load_backup, backup_nr)     

        # Zustandattribut sperren
        async with self._state_lock:

            # Zustand: Ausgeschaltet
            self._state = ServerState.OFF

    async def async_start(self):

        if not self.initialized:

            print(f"Der Server kann nicht gestartet werden, da das Projekt nicht initialisiert ist.")
            return False

        # Zustandattribut sperren
        async with self.server._lock:
            async with self._state_lock:

                print(self._state)
                print(self.server._state)

                # Prüfen, ob der Server ausgeschaltet ist
                if self._state != ServerState.OFF or self.server._state != ServerState.RUNNING:

                    print(f"Server kann nicht gestartet werden, da der Server einen unpassenden Zustand hat.")
                    return False
                
                # Zustand: Laden
                self._state = ServerState.STARTING

        # Laufzeit messen
        await asyncio.to_thread(self.project.runtime.start_interval)

        # Config-Backup starten
        await asyncio.to_thread(self.project.config_backup.start_backup_interval)

        # SaveGame-Backup starten
        await asyncio.to_thread(self.project.backup.start_backup_interval)

        # Before-Start ausführen
        if self.before_start_function:
            await asyncio.to_thread(self.before_start_function)

        # Command zum starten ausführen
        await asyncio.to_thread(self.cmd.start_detached)

        print(f"Der gestartete Game-Prozess hat die ProzessID {self.cmd.get_pid()}.")

        ##############
        # Pruefung durch RCON, ob Server wirklich online ist
        ##############

        if self.after_start_function:
            await asyncio.to_thread(self.after_start_function)

        self.in_use = True

        await asyncio.to_thread(self.start_check_use_interval)

        # Zustandattribut sperren
        async with self._state_lock:

            # Zustand: Laufend
            self._state = ServerState.RUNNING
        
        return True

    async def async_stop(self, delay_and_notification=True):

        # Zustandattribut sperren
        async with self._state_lock:

            # Prüfen, ob der Server am laufen ist
            if self._state != ServerState.RUNNING:

                print(f"Server kann nicht gestoppt werden, da der Server einen unpassenden Zustand hat.")
                return False
            
            # Zustand: Laden
            self._state = ServerState.STOPPING

        await asyncio.to_thread(self.stop_check_use_interval)

        #####################
        # Muss noch für RCON

        if self.send_function and delay_and_notification:
        
            print(f"# RCON #: Der Server wird in 60 Sekunden ausgeschaltet.")
            await self.send_function("# RCON #: Der Server wird in 60 Sekunden ausgeschaltet.")

            await asyncio.sleep(30)

            print(f"# RCON #: Der Server wird in 30 Sekunden ausgeschaltet.")
            await self.send_function(f"# RCON #: Der Server wird in 30 Sekunden ausgeschaltet.")
            await asyncio.sleep(20)

            for i in range(10, 0, -1):

                print(f"# RCON #: Der Server wird in {i} Sekunden ausgeschaltet.")
                await self.send_function(f"# RCON #: Der Server wird in {i} Sekunden ausgeschaltet.")
                await asyncio.sleep(1)

            print(f"# RCON #: Der Server wird ausgeschaltet.")
            await self.send_function(f"# RCON #: Der Server wird ausgeschaltet.")

        #####################

        if self.save_function:

            await asyncio.to_thread(self.save_function)

            print("Save-Function abwarten")
            await asyncio.sleep(5)

        if self.exit_function:

            await self.exit_function()

            print("Exit-Function abwarten")
            await asyncio.sleep(5)

        # Command zum stoppen ausführen
        await asyncio.to_thread(self.cmd.stop)

        print("Process-Beendung abwarten")
        await asyncio.sleep(5)

        # Config-Backup stoppen
        await asyncio.to_thread(self.project.config_backup.stop_backup_interval)

        # SaveGame-Backup stoppen
        await asyncio.to_thread(self.project.backup.stop_backup_interval)

        # Laufzeit messen
        await asyncio.to_thread(self.project.runtime.stop_interval)

        ##############
        # Pruefung durch RCON, ob Server wirklich ausgeschaltet ist
        ##############

        # Zustandattribut sperren
        async with self._state_lock:

            # Zustand: Laufend
            self._state = ServerState.OFF

        return True

    # Liest den aktuellen Status aus (unsicheres lesen)
    def read_server_state_unsafe(self):

        return self._state
    
    # Startet das Backup im Intervall
    def _run(self):

        print("Überprüfe in USE")

        # Intervall abwarten
        time.sleep(self.check_in_use_interval)

        # Solange das Auto-Backup eingeschaltet ist
        while self._running:

            current_in_use = self.in_use_function()

            if not current_in_use and not self.in_use:

                print("DAS SPIEL WIRD BEENDET, DA ES NICHT IN GEBRAUCH ZU SEIN SCHEINT!")

                asyncio.run(self.async_stop())

            else:

                print("Spiel ist gerade noch in Gebrauch!")

            self.in_use = current_in_use

            # Intervall abwarten
            time.sleep(self.check_in_use_interval)

    def start_check_use_interval(self):
    
        # Nur, wenn noch kein Backup-Intervall läuft
        if not self._running:

            # Thread starten, welcher _run ausführt
            print("Starte Check-In-Use Intervall")
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    # Backup Intervall beenden
    def stop_check_use_interval(self):

        if self._running:

            print("Stoppe Check-In-Use Intervall")

            # Thread beenden
            self._running = False
            self._thread = None

    def change_config(section, key, new_value, pfad):
            
            new_value = f"{new_value}"

            with open(pfad, "r", encoding="utf-8") as file:
                daten = file.read()

            changed = Game.replace_value(daten, section, key, new_value)

            if changed == daten:

                print("Die Konfiguaration hat sich nicht geändert.")

            else:

                print(f"Die Konfiguration wird auf folgendes angepasst: \n{changed}")

                with open(pfad, "w", encoding="utf-8") as file:
                    file.write(changed)

    def replace_value(text, section_key, value_key, neuer_wert):

        section = ""

        if section_key:

            # Muster, um den Block für [Part-KEY] zu finden
            section_pattern = rf"(\[{section_key}\]([\s\S]*?))(?=\n\[|$)"
            match = re.search(section_pattern, text)

            if not match:
                print(f"Abschnitt [{section_key}] nicht gefunden.")

                # Füge Section hinzu:
                text = text + "\n\n" + f"[{section_key}]\n{value_key}={neuer_wert}"  

                return text
            
            # Abschnitt
            section = match.group(1)

        else:

            section = text

        # Valuekey-Wert suchen und ersetzen
        ziel_pattern = rf"({value_key}=)(.+)"
        if re.search(ziel_pattern, section):
            neue_section = re.sub(ziel_pattern, lambda m: f"{m.group(1)}{neuer_wert}", section)
            # Den alten Abschnitt im Text ersetzen
            text = text.replace(section, neue_section)
            print(f"'{value_key}' ersetzt durch '{neuer_wert}'.")
        else:
            print(f"'{value_key}' nicht gefunden in [{section_key}].")

        return text
    
    async def async_crash_handler(self):

        # Prüfen, ob der Server am laufen ist
        if self._state != ServerState.RUNNING:

            # Der Server läuft nicht und kann somit nicht gecrashed sein
            return False
        
        # Auf Crash prüfen

        crash = await asyncio.to_thread(self.cmd.crash_check)

        if crash:

            await self.async_stop(delay_and_notification=False)

            await self.async_start()

            return True

        else:

            return False

        
