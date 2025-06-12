# pages/cargas_indicadores.py
import sys
import os
import streamlit as st
import requests
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
from pathlib import Path
from menu import generarMenu


# Obtener la ruta del directorio actual del script
current_dir = Path(__file__).parent

# Cargar variables de entorno desde el archivo .env
env_path = current_dir.parent.parent / 'config' / '.env'
load_dotenv(env_path)

# Cargar variables de entorno desde el archivo .env
#load_dotenv('C:/REPORTERIA NUEVA/frontend/pages/.venv')

# Añadir el directorio 'backend' al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

# Configuración de la base de datos desde variables de entorno
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_DATABASE')
}

# Función para obtener una conexión a la base de datos
def get_connection():
    try:
        cnx = mysql.connector.connect(**db_config)
        return cnx
    except Error as err:
        st.error(f"Error al conectar a la base de datos: {err}")
        return None

# Función para cerrar una conexión a la base de datos
def close_connection(cnx):
    try:
        cnx.close()
    except Error as err:
        st.error(f"Error al cerrar la conexión: {err}")

# Función para crear un cursor para una conexión a la base de datos
def create_cursor(cnx):
    try:
        cursor = cnx.cursor(dictionary=True)
        return cursor
    except Error as err:
        st.error(f"Error al crear el cursor: {err}")
        return None


# Función para verificar el estado de login
def check_login():
    if 'logged_in' in st.session_state and st.session_state.logged_in:
        return True
    return False

# Verificar si el usuario está logueado
if not check_login():
    st.error("Debes iniciar sesión para acceder a esta página.")
    st.stop()

# Generar el menú
generarMenu()

# Función para obtener datos de la API
def get_indicador_data(tipo_indicador, year):
    url = f"https://mindicador.cl/api/{tipo_indicador}/{year}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Error al obtener datos de la API para {tipo_indicador} en {year}")
        return None

# Función para guardar datos en la base de datos
def save_to_database(data, tipo_indicador):
    cnx = get_connection()
    if cnx:
        cursor = create_cursor(cnx)

        # Insertar datos en la tabla correspondiente
        for entry in data['serie']:
            fecha = datetime.strptime(entry['fecha'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d')
            insert_query = f"""
            INSERT INTO DM_{tipo_indicador} (fecha, valor)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE valor = VALUES(valor)
            """
            cursor.execute(insert_query, (fecha, entry['valor']))

        cnx.commit()
        close_connection(cnx)

# Lista de indicadores
indicadores = ["dolar", "euro", "imacec", "ipc", "tasa_desempleo", "tpm", "uf", "utm"]

with st.container():
            col1, col2, col3 = st.columns([2, 6, 2])

            with col2:
                # Formulario para seleccionar el año
                st.title("Carga de Datos Económicos")
                year = st.selectbox("Selecciona el año:", [2024, 2025])

                if st.button("Cargar Datos"):
                    for tipo_indicador in indicadores:
                        data = get_indicador_data(tipo_indicador, year)
                        if data and 'serie' in data and data['serie']:
                            save_to_database(data, tipo_indicador)
                    st.success("Datos guardados exitosamente en la base de datos")
