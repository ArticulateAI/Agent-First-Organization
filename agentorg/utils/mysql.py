import os
import string
import mysql.connector
import time
import logging

logger = logging.getLogger(__name__)

CONNECTION_TIMEOUT = int(os.getenv("MYSQL_CONNECTION_TIMEOUT", 10))

MYSQL_CONFIG = {
    "user":os.getenv("MYSQL_USERNAME"),
    "password":os.getenv("MYSQL_PASSWORD"),
    "host":os.getenv("MYSQL_HOSTNAME"),
    "port":os.getenv("MYSQL_PORT"),
    "database":os.getenv("MYSQL_DB_NAME")
}
POOL_SIZE = int(os.getenv("MYSQL_POOL_SIZE", 10))

mysql.connector.pooling.CNX_POOL_MAXSIZE = POOL_SIZE

class MySQLPool(object):
    def __init__(self, pool_size, **kwargs):
        self._host = kwargs.get("host", "localhost")
        self._port = kwargs.get("port", 3306)
        self._user = kwargs.get("user", "root")
        self._password = kwargs.get("password", "")
        self._database = kwargs.get("database", "test")
        self.dbconfig = {
            "host":self._host,
            "port":self._port,
            "user":self._user,
            "password":self._password,
            "database":self._database
        }
        self.pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="mypool",
            pool_size=pool_size,
            pool_reset_session=True,
            **self.dbconfig
        )
    
    def get_connection(self) -> mysql.connector.pooling.PooledMySQLConnection:
        t0 = time.time()
        while time.time() - t0 < CONNECTION_TIMEOUT:
            try:
                conn = self.pool.get_connection()
                logger.info("mysql connection established", extra={"time":time.time()-t0})
                return conn
            except mysql.connector.pooling.PoolError as e:
                if "pool exhausted" in str(e):
                    time.sleep(0.05)
                    continue
                raise e
            except Exception as e:
                raise e
        raise Exception(f"Pool exhausted; retried for {CONNECTION_TIMEOUT} seconds")       

    def close(self, sql_conns: mysql.connector.pooling.PooledMySQLConnection):
        sql_conns.close()

    def execute(self, sql:string, params:tuple=None):
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                conn.commit()
        except Exception as e:
            raise e
        finally:
            conn.close()
        return
    
    def fetchall(self, sql:string, params:tuple=None):
        conn = self.get_connection()
        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except Exception as e:
            raise e
        finally:
            conn.close()

    def fetchone(self, sql:string, params:tuple=None):
        conn = self.get_connection()
        try:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone()
        except Exception as e:
            raise e
        finally:
            if conn.is_connected():
                conn.close()
        

mysql_pool = MySQLPool(POOL_SIZE, **MYSQL_CONFIG)

