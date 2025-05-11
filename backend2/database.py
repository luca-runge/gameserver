import psycopg2
import asyncpg
import os

def getDatabaseConnection():

    conn = psycopg2.connect(
        user=os.getenv["DB_USER"],
        password=os.getenv["DB_PASSWORD"],
        host=os.getenv["DB_HOST"],
        port=os.getenv["DB_PORT"],
        database=os.getenv["DB_DATABASE"]
    )

    return conn

async def getAsyncDatabaseConnection():

    conn = await asyncpg.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_DATABASE")
    )

    return conn

        