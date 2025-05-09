import psycopg2
from psycopg2 import sql, pool

class DB_Pool:

    # Aktueller Datenbankpool der für alle benötigten Funktionen verwendet werden kann
    db_pool_global = None

    @staticmethod
    def set_db_pool(pool):
        DB_Pool.db_pool_global = pool
    
    @staticmethod
    def get_db_pool():
        return DB_Pool.db_pool_global

    # Initialisierung
    def __init__(self, db_minconn, db_maxconn, db_name, db_user, db_password, db_host, db_port ):

        # Mindestanzahl Verbindungen
        self.db_mincom = db_minconn

        # Maximalanzahl Verbindungen
        self.db_maxconn = db_maxconn

        # Datenbankname
        self.db_name = db_name

        # Datenbankbenutzer
        self.db_user = db_user

        # Passwort
        self.db_password = db_password

        # Host
        self.db_host = db_host

        # Port
        self.db_port = db_port

        # Pool erstellen
        self.db_pool = pool.SimpleConnectionPool(
            db_minconn,
            db_maxconn,
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )

    # Verbindung aus dem Pool holen
    def get_connection(self):

        return self.db_pool.getconn()
    
    # Verbindung wieder in den Pool zurückgeben
    def return_connection(self, conn):

        self.db_pool.putconn(conn)

    # Pool schließen
    #def close_pool(self):

       # if self.db_pool:
          #  self.db_pool.closeall()

    # Wenn das Obejekt zerstört wird
   # def __del__(self):

     #   self.close_pool()







        