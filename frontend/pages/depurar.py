# depurar.py
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from pathlib import Path

# Obtener la ruta del directorio actual del script
current_dir = Path(__file__).parent
print("=== primer mensaje ===")
print("Ruta del directorio actual:", current_dir)

# Cargar variables de entorno desde el archivo .env
env_path = current_dir / 'config' / '.env'
print("=== segundo mensaje ===")
print("Ruta del archivo .env:", env_path)

# Verificar si el archivo .env existe
if env_path.exists():
    print("El archivo .env existe.")
else:
    print("El archivo .env no existe.")

load_dotenv(env_path)

# Configuración de la base de datos desde variables de entorno
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_DATABASE')
}

# Imprimir la configuración de la base de datos
print( "=== tercer mensaje ===" )
print("Configuración de la base de datos:", db_config)

# Función para obtener una conexión a la base de datos
def get_connection():
    try:
        cnx = mysql.connector.connect(**db_config)
        return cnx
    except Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        return None

# Función para cerrar una conexión a la base de datos
def close_connection(cnx):
    try:
        cnx.close()
    except Error as err:
        print(f"Error al cerrar la conexión: {err}")

# Probar la conexión
cnx = get_connection()
if cnx:
    print("Conexión exitosa a la base de datos")
    close_connection(cnx)
else:
    print("Error al conectar a la base de datos")

# Imprimir la configuración de la base de datos
print("Configuración de la base de datos:", db_config)