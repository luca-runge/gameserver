from projectmanagement.backup import Game_Backup
from projectmanagement.runtime import Runtime
import os
from datenbank.db_utils import DB_Pool
import json
import shutil

class Project:

    def __init__(self, project_nr, default_backup_path, game_path, config_path, backup_path_mapping_path_saved, backup_path_mapping_path_config, backup_interval_saved, backup_interval_config,  name, save_function, template_path, gameserver_state_function):

        self.backup_path = os.path.join(default_backup_path, name)
        backup_path_saved = os.path.join(self.backup_path, 'Saved')
        backup_path_config = os.path.join(self.backup_path, 'Config')
        backup_management_json_path_saved = os.path.join(backup_path_saved, 'management.json')
        backup_management_json_path_config = os.path.join(backup_path_config, 'management.json')

        self.game_path = game_path
        self.config_path = config_path

        self.template_path = template_path

        self.backup = Game_Backup(management_json_path=backup_management_json_path_saved, backup_path=backup_path_saved, game_path=game_path, path_mapping_path=backup_path_mapping_path_saved, backup_interval=backup_interval_saved, gameserver_state_function=gameserver_state_function, save_function=save_function, update_last_save_function=self.update_last_saved)
        self.config_backup = Game_Backup(management_json_path=backup_management_json_path_config, backup_path=backup_path_config, game_path=config_path, path_mapping_path=backup_path_mapping_path_config, backup_interval=backup_interval_config, gameserver_state_function=gameserver_state_function)
        self.runtime = Runtime(600, project_nr=project_nr)
        self.project_nr = project_nr
        self.project_name = name

    def get_whitelist(self):

        whitelist = []

        try:

            pool = DB_Pool.get_db_pool()

            conn = pool.get_connection()

            cursor = conn.cursor()

                # Serverlaufzeit Update
            
            cursor.execute('SELECT BenutzerID, DiscordID, EpicID, MinecraftID, SteamID, WebID FROM benutzer JOIN whitelist USING(BenutzerID) WHERE  ProjektID = %s', (self.project_nr,))
            
            rows = cursor.fetchall()

            for row in rows:

                user = {}
                user["benutzerid"] = row[0]
                user["discordid"] = row[1]
                user["epicid"] = row[2]
                user["minecraftid"] = row[3]
                user["steamid"] = row[4]
                user["webid"] = row[5]

                whitelist.append(user)
        
        except Exception as e:

            print(f"Die Abfrage der Whitelist des Projekts {self.project_name} [{self.project_nr}] ist fehlgeschlagen.")

            whitelist = []
        
        finally:

            # Cursor und Verbindung schließen
            cursor.close()
            pool.return_connection(conn)

        player_count = len(whitelist)

        return player_count, whitelist
    
    def is_initialized(self):

        initialized = False

        # Verbindung aus dem Pool
        pool = DB_Pool.get_db_pool()

        conn = pool.get_connection()

        cursor = conn.cursor()
        
        # Abfrage
        cursor.execute('SELECT initialisiert FROM projekte WHERE ProjektID = %s', (self.project_nr,))
        
        # Zeile aus dem Cursor
        row = cursor.fetchone()

        # Wert auslesen
        initialized = row[0]

        # Cursor und Verbindung schließen
        cursor.close()
        pool.return_connection(conn)

        return(initialized)
    
    def initialize_project(self, config_state_zero_path, saved_state_zero_path):

        # Backup Pfad erstellen
        self.backup.create_backup_path()
        self.config_backup.create_backup_path()

        # Zustand 0 laden
        self.config_load_state_zero(config_state_zero_path)
        self.saved_load_state_zero(saved_state_zero_path)

        # Datenbank aktualisieren

        try:

            pool = DB_Pool.get_db_pool()

            conn = pool.get_connection()

            cursor = conn.cursor()

                # Serverlaufzeit Update
            
            cursor.execute('UPDATE projekte SET initialisiert = true WHERE ProjektID = %s', (self.project_nr,))
            
            conn.commit()

            print(f"Das Projekt {self.project_name} [{self.project_nr}] wurde erfolgreich initialisiert.")
             
        except Exception as e:

            conn.rollback()
            print(f"Die Abfrage der Whitelist des Projekts {self.project_name} [{self.project_nr}] ist fehlgeschlagen.")
        
        finally:

            # Cursor und Verbindung schließen
            cursor.close()
            pool.return_connection(conn)

    def config_load_state_zero(self, config_state_zero_path):

        self._load_state_zero(config_state_zero_path, self.config_path, os.path.join(self.template_path, "config"))

    def saved_load_state_zero(self, saved_state_zero_path):

        self._load_state_zero(saved_state_zero_path, self.game_path, os.path.join(self.template_path, "saved"))
    
    def _load_state_zero(self, state_zero_path, game_path, template_path):

        # Zustand 0 auslesen
        state_zero = {}
        with open(state_zero_path, "r", encoding="utf-8") as file:
            state_zero = json.load(file)

        dirs = state_zero["dirs"]
        files = state_zero["files"]
        remove_dirs = state_zero["remove_dirs"]
        remove_files = state_zero["remove_files"]
        clear_dirs = state_zero["clear_dirs"]

        # Dateien löschen
        for remove_file in remove_files:

            path = os.path.join(game_path, remove_file["game"])

            try:

                os.remove(path)
                print(f"Datei {path} erfolgreich entfernt.")

            except FileNotFoundError:

                print(f"Datei {path} ist bereits nicht vorhanden und kann nicht erntfernt werden.")

        # Verzeichnisse löschen
        for remove_dir in remove_dirs:

            path = os.path.join(game_path, remove_dir["game"])

            try:

                # Verzeichnis entfernen
                shutil.rmtree(path)
                print(f"Verzeichnis {path} erfolgreich entfernt.")

            except FileNotFoundError:

                print(f"Verzeichnis {path} ist bereits nicht vorhanden und kann nicht entfernt werden.")

        # Verzeichnis leeren
        for clear_dir in clear_dirs:

            path = os.path.join(game_path, clear_dir["game"])

            try:

                # Verzeichnis entfernen
                shutil.rmtree(path)
                os.makedirs(path, exist_ok=True)
                print(f"Verzeichnis {path} erfolgreich geleert.")

            except FileNotFoundError:

                print(f"Verzeichnis {path} ist bereits nicht vorhanden und kann nicht entfernt werden.")
                os.makedirs(path, exist_ok=True)
                print(f"Verzeichnis {path} wurde hinzugefügt.")

        # Verzeichnisse kopieren aus dem Default
        for dir in dirs:

            path_src = os.path.join(template_path, dir["default"])
            path_dst = os.path.join(game_path, dir["game"])

            # print(f"Aus dem Deafult kopieren (SRC): {path_src}")
            # print(f"Aus dem Deafult kopieren (DST): {path_dst}")

            
            # Erstellen fehlender Zwischenordner
            path_dst_dir = os.path.dirname(path_dst)
            os.makedirs(path_dst_dir, exist_ok=True)

            try:

                # Game-Vezeichnis entfernen, um Platz für das Verzeichnis aus dem Default zu schaffen
                if os.path.exists(path_dst):
                    shutil.rmtree(path_dst)  

                # Verzeichnis aus dem Default kopieren
                shutil.copytree(path_src, path_dst, dirs_exist_ok=True)
                # print(f"State-Zero: {path_src} nach {path_dst} kopiert.")

            except FileNotFoundError as e:

                print(f"Verzeichnis wurde im Deafult nicht gefunden!")

        # Datein kopieren
        for file in files:

            path_src = os.path.join(template_path, file["default"])
            path_dst = os.path.join(game_path, file["game"])

            # Erstellen fehlender Zwischenordner
            path_dst_dir = os.path.dirname(path_dst)
            os.makedirs(path_dst_dir, exist_ok=True)

            try:

                # Datei aus dem Deafult kopieren
                shutil.copy2(path_src, path_dst)
                print(f"{path_src} nach {path_dst} kopiert.")

            except FileNotFoundError:

                print("Datei existiert nicht im Default!")

    def update_last_saved(self):

        try:

            pool = DB_Pool.get_db_pool()

            conn = pool.get_connection()

            cursor = conn.cursor()

                # Serverlaufzeit Update
            
            cursor.execute('UPDATE projekte SET LastSave = current_timestamp WHERE ProjektID = %s', (self.project_nr,))
            
            conn.commit()
             
        except Exception as e:

            conn.rollback()
            print(f"Aktualisieren von Last-Saved des Projekts {self.project_name} [{self.project_nr}] ist fehlgeschlagen.")
        
        finally:

            # Cursor und Verbindung schließen
            cursor.close()
            pool.return_connection(conn)






        

        






