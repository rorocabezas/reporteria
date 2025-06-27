# backend/database.py
import os
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error

# Cargar las variables de entorno desde el archivo .env en la misma ruta
load_dotenv()

# Configurar el diccionario de la base de datos
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_DATABASE')
}

# Validación crucial para evitar errores posteriores
if not all(db_config.values()):
    raise ValueError("Error Crítico: Una o más variables de la base de datos no están definidas en el archivo .env.")

def get_connection(config_key='default'):
    """Obtiene una conexión a la base de datos."""
    try:
        cnx = mysql.connector.connect(**db_config) 
        return cnx
    except Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        return None

def close_connection(cnx):
    """Cierra una conexión a la base de datos."""
    try:
        if cnx.is_connected():
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
