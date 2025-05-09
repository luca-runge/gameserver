from dotenv import dotenv_values
from fastapi import HTTPException, status, Header
from datenbank.db_utils import DB_Pool

class API_Keys:

    def __init__(self, Pfad_dotenv):

        self.api_keys = self.dotenv_api(Pfad_dotenv)
    
    def dotenv_api(self, Pfad):

        print(Pfad)

        api_keys = {}

        print(dotenv_values(Pfad).items())

        for key, value in dotenv_values(Pfad).items():
            print(f"{key}:{value}")
            api_keys[value] = key

        return api_keys

    def check_https_api_key(self, authorization: str = Header(...)):

        print("PRÜFUNG API KEY")

        api_key = authorization

        print(api_key)
        print(self.api_keys)

        if api_key not in self.api_keys:

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized API Key"
            )
        
        print(f"Prüfung erfolgreich")
        
        return self.api_keys[api_key]
    
def berechtigung_pruefen(Benoetigte_Rollen, UserID):

    # Rollen das der Datenbank abfragen

    hat_berechtigung = False

    pool = DB_Pool.get_db_pool()

    conn = pool.get_connection()

    cursor = conn.cursor()

    # Beispiel-Abfrage
    cursor.execute('SELECT RollenID FROM benutzer JOIN rollenverteilung USING(BenutzerID) JOIN rollen USING(RollenID) WHERE BenutzerID = %s', [UserID])
    rows = cursor.fetchall()

    print(rows)

    if rows:
        # Ausgabe der Ergebnisse
        rollen = [row[0] for row in rows]

        print(rollen)

        for rolle in Benoetigte_Rollen:
            if rolle in rollen:
                hat_berechtigung = True

                print (f"Berechtigung {rolle} ist ausreichend.")
                break

    # Cursor und Verbindung schließen
    cursor.close()

    pool.return_connection(conn)

    if hat_berechtigung:

        return
        
    else:
    
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource."
        )
    





