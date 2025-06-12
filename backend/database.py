# backend/database.py
import mysql.connector
from mysql.connector import Error

# Configuración de la conexión a la base de datos
configs = {
    'default': {
        'host': '192.250.226.219',
        'user': 'admin',
        'password': 'Chile2025',
        'database': 'jisparking'
    },
    'nuevo': {
        'host': 'erpjis.mysql.database.azure.com',
        'user': 'erpjis@erpjis',
        'password': 'Macana11',
        'database': 'erp_jis'
    }
}

def get_connection(config_key='default'):
    """Obtiene una conexión a la base de datos."""
    config = configs.get(config_key)
    if not config:
        raise ValueError(f"Configuración no encontrada para la clave: {config_key}")

    try:
        cnx = mysql.connector.connect(**config)
        return cnx
    except Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        return None

def close_connection(cnx):
    """Cierra una conexión a la base de datos."""
    try:
        cnx.close()
    except Error as err:
        print(f"Error al cerrar la conexión: {err}")

def create_cursor(cnx):
    """Crea un cursor para una conexión a la base de datos."""
    try:
        cursor = cnx.cursor(dictionary=True)
        return cursor
    except Error as err:
        print(f"Error al crear el cursor: {err}")
        return None