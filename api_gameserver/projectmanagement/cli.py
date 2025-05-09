import subprocess
import os
import signal
import sys

import psutil

import time

class CLI_CMD:

    def __init__(self, command, search_game_process_name, search_game_cmdline):

        self.command = command
        self.search_game_process_name = search_game_process_name
        self.search_game_cmdline = search_game_cmdline
        self.process = None
        self.game_process = None

    def start_detached(self):
        """Startet den Befehl als losgelösten Prozess, angepasst für Windows/Linux."""
        print(self.command)
        process = None
        if sys.platform == "win32":
            # Windows: Erstelle einen neuen Prozess-Cluster
            process = subprocess.Popen(
                self.command, shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
        else:
            # Linux/macOS: Starte in einer neuen Prozessgruppe
            process = subprocess.Popen(
                self.command, shell=True, preexec_fn=os.setsid,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

        if process:
            pid = process.pid
            self.set_process(pid)

        time.sleep(10)

        child_processes = self.get_child_pids()

        game = self.find_process()

        game_process_pid = [pid for pid in game if pid in child_processes]

        print(game_process_pid)

        if game_process_pid:

            self.set_game_process(game_process_pid[0])

        else:

            time.sleep(10)

            result = self.reattach()

            if not result:

                print("Fehler beim Starten des Game-Prozesses!")
        



    def get_child_pids(self):
        try:
            parent = psutil.Process(self.process.pid)
            children = parent.children(recursive=True)
            return [child.pid for child in children]
        except psutil.NoSuchProcess:
            return []

    """
    def kill(self):
        # Sendet SIGINT (CTRL+C) an den Prozess.

        try:
            if self.process:

                pid = self.process.pid

                print(f"Beende Prozess mit PID {pid}...")
                self.process.terminate()
                self.process.wait()  # blockiert, bis der Prozess beendet wurde
                print(f"Prozess mit PID {pid} wurde erfolgreich beendet.")

        except Exception as e:

            print(f"Fehler beim stoppen des eines Pozesses {e}")

    def stop_alt(self):

        try:

            if self.process:

                #childs = self.get_child_pids()

                #for child in childs:

                    #try:
                        #child_process = psutil.Process(child)
                        #child_process.terminate()

                    #except psutil.NoSuchProcess:
                        #print(f"Kein Prozess mit der PID {child} gefunden.")
                    #except psutil.AccessDenied:
                        #print(f"Kein Zugriff auf den Prozess mit der PID {child}.")
                    #except Exception as e:
                        #print(f"Fehler: {e}")

                child_pid = self.get_child_pids()[0]

                self.set_process(child_pid)

                pid = self.process.pid



                print(f"Beende Prozess mit PID {pid}...")
                self.game_process.terminate()
                self.game_process.wait()
                print(f"Prozess mit PID {pid} wurde erfolgreich beendet.")

        except Exception as e:

            print(f"Der Prozess konnte nicht ordnungsgemäß gestoppt werden. {e}")
    
    """

    def stop(self):

        try:

            # Prüfen, ob der Spiel-Prozess noch läuft
            if self.game_process and self.game_process.is_running():

                print(f"Spielprozess läuft noch...")

                self.game_process.terminate()

                try:
                    self.game_process.wait(timeout=10)  # Warte 10s auf das Beenden
                    print("Spiel gestoppt.")
                except psutil.TimeoutExpired:
                    print("Spielprozess reagiert nicht, erzwinge das Beenden des Spiels...")
                    if self.process and self.process.is_running():
                        self.game_process.kill()
                        self.game_process.wait()
                        print("Spielprozess abgeschossen.")

                finally:

                    if self.process and self.process.is_running():

                        self.process.kill()
            
            # Commandline beenden
            elif self.process and self.process.is_running():
                print("Kein aktives Spiel gefunden, Elternprozess wird beendet...")
                self.process.kill()
                self.process.wait()
                print("Elternprozess gestoppt.")

            else:

                print(f"Das Spiel und die Commandline sind bereits beendet.")

        except Exception as e:

            print(f"Der Prozess konnte nicht ordnungsgemäß gestoppt werden. {e}")

        
    def find_process(self):
    # Durchlaufe alle laufenden Prozesse

        process_name = self.search_game_process_name
        command = self.search_game_cmdline

        process_id = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Sicherstellen, dass cmdline nicht None ist und eine Liste enthält
                cmdline = proc.info['cmdline']
                name = proc.info['name']
                if cmdline and command in " ".join(cmdline) and name and name == process_name:  # Befehl des Prozesses prüfen
                    print(f"Gefundener Prozess: PID={proc.info['pid']}, Name={proc.info['name']}, Befehl={cmdline}")
                    process_id.append(proc.info['pid']) 
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Fehlerbehandlung, falls der Prozess zwischenzeitlich beendet wurde oder Zugriffsprobleme auftreten
                continue
        return process_id

    def crash_check(self):

        result = True

        print(f"Prüfe, ob es einen Crash gegeben hat")

        # Prüfen, ob der Gameprozess zurzeit läuft
        if self.game_process:

            if self.game_process.is_running():

                result = False

        # Versuchen den Gameprozess zu finden und zu prüfen, ob dieser erreichbar ist
        if result:

            # Finden der Prozesse
            reattach = self.reattach()

            if reattach:
                
                # Prüfen, ob der gefundene Prozess läuft
                if self.game_process:

                    if self.game_process.is_running():

                        result = False

        print(f"Ergebnis der Crash-Analyse: {result}")

        return result

    def reattach(self):

        result = False

        game = self.find_process()

        print(game)

        if game:

            self.game_process = psutil.Process(game[0])

            ppid = self.game_process.ppid()

            # Prüfen, ob dieser einen Eltern-Prozess besitzt oder "adoptiert" wurde
            if ppid != 1:

                self.set_process(ppid)

            result = True

        return result
    
    def set_process(self, pid):

        try:
            self.process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            print(f"Kein Prozess mit der PID {pid} gefunden.")
            self.process = None
        except psutil.AccessDenied:
            self.process = None
            print(f"Kein Zugriff auf den Prozess mit der PID {pid}.")
        except Exception as e:
            print(f"Fehler: {e}")

    def set_game_process(self, pid):

        try:
            self.game_process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            print(f"Kein Prozess mit der PID {pid} gefunden.")
            self.game_process = None
        except psutil.AccessDenied:
            self.game_process = None
            print(f"Kein Zugriff auf den Prozess mit der PID {pid}.")
        except Exception as e:
            print(f"Fehler: {e}")

    def get_pid(self):

        return self.game_process.pid
