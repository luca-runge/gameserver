import subprocess
import os
import signal
import sys

import psutil

import time

class CLI_CMD:

    def __init__(self, command):

        self.command = "/Gameserver/satisfactory_server/Engine/Binaries/Linux/FactoryServer-Linux-Shipping"
        self.process = None
        self.game_process_name = "FactoryServer-Linux-Shipping"
        self.game_process = None
    """
    def start_detached(self):
        #Startet den Befehl als losgelösten Prozess
        if self.process is None:
            self.process = subprocess.Popen(
                self.command, shell=True, preexec_fn=os.setsid,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    
    def stop(self):
        #Beendet einen laufenden gebundenen Prozess mit SIGINT
        if self.process:
            os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
            self.process.wait()
            self.process = None
    """
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

    def get_child_pids(self):
        try:
            parent = psutil.Process(self.process.pid)
            children = parent.children(recursive=True)
            return [child.pid for child in children]
        except psutil.NoSuchProcess:
            return []


    def kill(self):
        """Sendet SIGINT (CTRL+C) an den Prozess."""

        try:
            if self.process:

                pid = self.process.pid

                print(f"Beende Prozess mit PID {pid}...")
                self.process.terminate()
                self.process.wait()  # blockiert, bis der Prozess beendet wurde
                print(f"Prozess mit PID {pid} wurde erfolgreich beendet.")

        except Exception as e:

            print(f"Fehler beim stoppen des eines Pozesses {e}")

    def stop(self):

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
                pid = self.process.pid

                print(f"Beende Prozess mit PID {pid}...")
                self.process.terminate()
                self.process.wait()
                print(f"Prozess mit PID {pid} wurde erfolgreich beendet.")

        except Exception as e:

            print(f"Der Prozess konnte nicht ordnungsgemäß gestoppt werden. {e}")

    def find_process_by_command(self, process_name):
    # Durchlaufe alle laufenden Prozesse

        command = self.command.split(' ')[0]
        print(command)

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
    
    def find_process_by_command2(self, command_part):
    # Durchlaufe alle laufenden Prozesse

        process_id = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Sicherstellen, dass cmdline nicht None ist und eine Liste enthält
                cmdline = proc.info['cmdline']
                if cmdline and command_part in " ".join(cmdline):  # Befehl des Prozesses prüfen
                    print(f"Gefundener Prozess: PID={proc.info['pid']}, Name={proc.info['name']}, Befehl={cmdline}")
                    process_id.append({"pid": proc.info['pid'], "name":proc.info['name']}) 
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Fehlerbehandlung, falls der Prozess zwischenzeitlich beendet wurde oder Zugriffsprobleme auftreten
                continue
        return process_id
    
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

    def reattach(self):

        result = False

        game = self.find_process_by_command(self.game_process_name)

        print(game)

        if game:

            self.game_process = psutil.Process(game[0])

            ppid = self.game_process.ppid()

            # Prüfen, ob dieser einen Eltern-Prozess besitzt oder "adoptiert" wurde
            if ppid != 1:

                self.set_process(ppid)

            result = True

        return result




    def get_pid(self):

        return self.process.pid
    


ark = CLI_CMD('/Gameserver/ark_server/ShooterGame/Binaries/Linux/ShooterGameServer TheIsland?listen -exclusivejoin -server -log')
##ark.set_process(1924)
# ark.start_detached()

#print(ark.get_child_pids())

#print(ark.process.ppid())

#print(ark.process.name())
#print(ark.process.cmdline())

#ark.process.terminate()
#ark.process.wait()

if ark.reattach():

    print("Reattached!")

    if ark.process and ark.process.is_running():

        print(f"Die PID der Shell: {ark.process.pid}")

    if ark.game_process and ark.game_process.is_running():

        print(f"Die PID des Spiels: {ark.game_process.pid}")

        #ark.game_process.terminate()
        #ark.game_process.wait()

        #print(f"Spiel angehalten!")

#print("Wurde angehalten!")

#time.sleep(1)

##prozesse = ark.find_process_by_command('ShooterGameServer')
#print(prozesse)

#prozesse = ark.find_process_by_command('sh')
#print(prozesse)

#ark.reattach()




