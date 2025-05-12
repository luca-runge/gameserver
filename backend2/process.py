import os
import asyncio
import psutil

class Process:

    def __init__(self, command, SearchGameProcessName, SearchCommandline):

        self.command = command
        self.SearchGameProcessName = SearchGameProcessName
        self.SearchCommandline = SearchCommandline
        self.ShellProcess = None
        self.GameProcess = None

    async def async_StartDetached(self):

        process = None

        # Starte Subprozess in neuer Prozessgruppe (Linux)
        process = await asyncio.create_subprocess_shell(
            self.command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None
        )

        # Prozess der Shell
        pid = process.pid
        print(pid)
        self.ShellProcess = await self.async_getProcess(pid)

        await asyncio.sleep(10)

        # Kindprozesse der Shell
        ChildPIDs = await self.async_getChildPIDs()

        print(ChildPIDs)

        # Mögliche Spiel-Prozesse anhand Name und Command
        GamePIDs = await self.async_findGameProcesses()

        print(GamePIDs)

        # Spiel-Prozesse, die auch Child-Prozesse der aktuellen Shell sind
        GameProcessPID = [PID for PID in GamePIDs if PID in ChildPIDs]

        print(GameProcessPID)

        # Game Prozess gefunden?
        if len(GameProcessPID) > 0:

            # Game Prozess hinzufügen
            self.GameProcess = await self.async_getProcess(GameProcessPID[0])

        else:

            # 10s warten
            await asyncio.sleep(10)

            # Versuchen, sich an den Prozess anzuhängen
            result = await self.async_Reattach()

            if not result:

                print("Fehler beim Starten des Game-Prozesses!")

    # Kindprozesse der Shell abfragen (asynchron)
    async def async_getChildPIDs(self):
        ChildPIDs = await asyncio.to_thread(self.getChildPIDs)
        return ChildPIDs
    
    # Kindprozesse der Shell abfragen
    def getChildPIDs(self):
        try:
            # Kindprozesse des Shellprozesses
            children =  self.ShellProcess.children(recursive=True)

            # PID der Kindprozesse
            return [child.pid for child in children]
        except psutil.NoSuchProcess:
            return []

    # Prozess beenden (asynchron) 
    async def async_StopProcess(self):

        await asyncio.to_thread(self.StopProcess)

    # Prozess beenden
    def StopProcess(self):

        try:

            # Prüfen, ob der Spiel-Prozess noch läuft
            if self.GameProcess and self.GameProcess.is_running():

                print(f"Spielprozess läuft noch...")

                # Spielprozess "sanft" beenden
                self.GameProcess.terminate()

                try:
                    # Bis zu 10s auf das Beenden warten
                    self.GameProcess.wait(timeout=10) 
                    print("Spielprozess beendet.")

                except psutil.TimeoutExpired:

                    print("Timeout")
                    
                    # Spielprozess läuft immer noch?
                    if self.GameProcess and self.GameProcess.is_running():
                        print("Spielprozess reagiert nicht, erzwinge das Beenden des Spiels...")

                        # Spielprozess "hart" beenden
                        self.GameProcess.kill()
                        self.GameProcess.wait()
                        print("Spielprozess abgeschossen.")

                finally:

                    # Shell beenden
                    if self.ShellProcess and self.ShellProcess.is_running():
                       # self.ShellProcess.kill()
                       # self.ShellProcess.wait()
                        print("Shell (Elternprozess) beendet.")
            
            # Shell beenden
            elif self.ShellProcess and self.ShellProcess.is_running():
               # self.ShellProcess.kill()
               # self.ShellProcess.wait()
                print("Shell (Elternprozess) beendet.")

            else:

                print(f"Das Spiel und die Shell sind bereits beendet.")

        except Exception as e:

            print(f"Der Prozess konnte nicht ordnungsgemäß gestoppt werden. {e}")

    # Liste an passenden PIDs des Spielprozesses (asynchron)
    async def async_findGameProcesses(self):
        PIDs = await asyncio.to_thread(self.findGameProcesses)
        return PIDs

    # Liste an passenden PIDs des Spielprozesses
    def findGameProcesses(self):
    
        process_name = self.SearchGameProcessName
        command = self.SearchCommandline

        process_id = []
        # Durchlaufe alle laufenden Prozesse
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Sicherstellen, dass cmdline nicht None ist und eine Liste enthält
                cmdline = process.info['cmdline']
                name = process.info['name']
                if cmdline and command in " ".join(cmdline) and name and name == process_name:  # Befehl des Prozesses prüfen
                    print(f"Gefundener Prozess: PID={process.info['pid']}, Name={process.info['name']}, Befehl={cmdline}")
                    process_id.append(process.info['pid']) 
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return process_id
    
        # Liste an passenden PIDs des Spielprozesses
    def findChildProcesses(self):
    
        ChildPIDs = self.getChildPIDs()

        process_id = []
        # Durchlaufe alle laufenden Prozesse
        for process in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Sicherstellen, dass cmdline nicht None ist und eine Liste enthält
                cmdline = process.info['cmdline']
                name = process.info['name']
                if process.info['pid'] in ChildPIDs:  # Befehl des Prozesses prüfen
                    print(f"Gefundener Prozess: PID={process.info['pid']}, Name={process.info['name']}, Befehl={cmdline}")
                    process_id.append(process.info['pid']) 
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        print(process_id)

    # Prüfen, ob der Spielprozess gecrashed ist
    async def async_CrashCheck(self):

        result = True

        print(f"Prüfe, ob es einen Crash gegeben hat.")

        # Prüfen, ob der Gameprozess zurzeit läuft
        if self.GameProcess and self.GameProcess.is_running():
            result = False

        # Versuchen den Gameprozess zu finden und zu prüfen, ob dieser erreichbar ist
        if result:

            # Reattach versuchen
            reattach = await self.async_Reattach()

            # Prüfen, ob der Gameprozess nach dem Reattach läuft? (Reattach erfolgreich?)
            if reattach and self.GameProcess and self.GameProcess.is_running():
                result = False

        print(f"Ergebnis der Crash-Analyse: {result}")

        return result

    # Wiederfinden + Anhängen an den Spielprozess
    async def async_Reattach(self):

        # Ergebnis
        result = False

        # Alle PIDs passender, laufender Spielprozesse
        GamePIDs = await self.async_findGameProcesses()

        # Spielprozesse gefunden
        if len(GamePIDs) > 0:

            # Erster Spielprozess
            GamePID = GamePIDs[0]

            # Spielprozess setzen
            self.GameProcess = await self.async_getProcess(GamePID)

            # Parent-PID zum GameProzess holen 
            PPID = self.GameProcess.ppid()

            # Prüfen, ob dieser einen Eltern-Prozess (Shell) besitzt oder "adoptiert" wurde
            if PPID != 1:

                # Shell-Prozess setzen
                self.ShellProcess = await self.async_getProcess(PPID)  

            # Reattach erfolgreich
            result = True

        return result
    
    # Prozess mit angegebner PID holen (asynchron)
    async def async_getProcess(self, pid):
        Process = await asyncio.to_thread(self.getProcess, pid)
        return Process
    
    # Prozess mit angegebner PID holen
    def getProcess(self, pid):

        process = None

        try:
            # Prozess-Objekt
            process = psutil.Process(pid)
        
        # Fehler beim Holen des Prozesses
        except psutil.NoSuchProcess:
            print(f"Kein Prozess mit der PID {pid} gefunden.")
        except psutil.AccessDenied:
            print(f"Kein Zugriff auf den Prozess mit der PID {pid}.")
        except Exception as e:
            print(f"Fehler: {e}")

        # Prozess zurückliefern
        finally:
            return process

    # Prozess-ID des Spiel-Prozesses abfragen
    def getGamePID(self):
        return self.GameProcess.pid
