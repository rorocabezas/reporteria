# -*- coding: utf-8 -*-
# pages/cargas.py
import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime, timedelta
import mysql.connector
from mysql.connector import Error
from menu import generarMenu
from dotenv import load_dotenv
from pathlib import Path
import requests

# Obtener la ruta del directorio actual del script
current_dir = Path(__file__).parent

# Cargar variables de entorno desde el archivo .env
env_path = current_dir / 'config' / '.env'
load_dotenv(env_path)

# Añadir el directorio 'backend' al PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))

# Configuración de la base de datos desde variables de entorno
db_config = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_DATABASE')
}

# Función para verificar el estado de login
def check_login():
    return 'logged_in' in st.session_state and st.session_state.logged_in

# Verificar si el usuario está logueado
if not check_login():
    st.error("Debes iniciar sesión para acceder a esta página.")
    st.query_params = {}
    st.rerun()

# Configuración de la página
if 'user_info' in st.session_state:
    st.write(f"Bienvenido, {st.session_state.user_info['full_name']}!")
else:
    st.error("Información de usuario no disponible.")
    st.stop()

# Generar el menú con botón de salir
if generarMenu():
    btnSalir = st.button("Salir")
    if btnSalir:
        st.session_state.clear()
        st.rerun()

st.header('Cargas :orange[Diarias]')
st.markdown("---")

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

# Función para obtener datos de un indicador de la API
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



# Función para obtener datos de ventas por día
def update_venta_x_hora(year, month):
    try:
        # Convertir parámetros a enteros para asegurar que sean del tipo correcto
        year_int = int(year)
        month_int = int(month)

        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)  

        # Definir la consulta base
        base_query = f"""
        SELECT
            dtes.branch_office_id,
            dtes.folio,
            (dtes.total * 1) AS total,
            dtes.entrance_hour,
            dtes.exit_hour,
            DATE_FORMAT(dtes.added_date, "%Y-%m-%d") AS date,
            HOUR(dtes.exit_hour) AS hora_exit,
            TIME_FORMAT(TIMEDIFF(dtes.exit_hour, dtes.entrance_hour), "%H:%i:%s") AS estadia,
            HOUR(TIMEDIFF(dtes.exit_hour, dtes.entrance_hour)) * 60 + MINUTE(TIMEDIFF(dtes.exit_hour, dtes.entrance_hour)) AS minutos,
            CASE
                WHEN HOUR(TIMEDIFF(dtes.exit_hour, dtes.entrance_hour)) * 60 + MINUTE(TIMEDIFF(dtes.exit_hour, dtes.entrance_hour)) <= 30 THEN '30 minutos'
                WHEN HOUR(TIMEDIFF(dtes.exit_hour, dtes.entrance_hour)) * 60 + MINUTE(TIMEDIFF(dtes.exit_hour, dtes.entrance_hour)) <= 60 THEN '60 minutos'
                ELSE '90 minutos'
            END AS rango
        FROM
            dtes
        WHERE
            YEAR(added_date) = {year_int} AND
            MONTH(added_date) = {month_int};
        """

        # Eliminar datos existentes en DETALLE_VENTA_HORA para el año y mes seleccionados
        delete_query = f"""
        DELETE FROM DETALLE_VENTA_HORA
        WHERE YEAR(date) = {year_int} AND MONTH(date) = {month_int};
        """
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de eliminación

        # Insertar datos en DETALLE_VENTA_HORA usando la consulta base
        insert_query = f"""
        INSERT INTO DETALLE_VENTA_HORA (
            branch_office_id,
            folio,
            total,
            entrance_hour,
            exit_hour,
            date,
            hora_exit,
            estadia,
            minutos,
            rango
        )
        {base_query}
        """
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Ejecutar la consulta base para obtener los datos
        cursor.execute(base_query)

        # Obtener resultados y convertir a DataFrame
        results = cursor.fetchall()

        # Cerrar la conexión
        cursor.close()
        connection.close()

        # Convertir resultados a DataFrame
        if results:
            df = pd.DataFrame(results)
            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        st.error(f"Error al conectar a la base de datos: {e}")
        return pd.DataFrame()

# Función para actualizar el KPI_INGRESOS_IMG_MES Ingresos Acumulados Actual
def update_ingresos_acumulado_actual():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        # Consulta SQL para borrar los datos existentes en la tabla KPI_INGRESOS_IMG_MES
        delete_query = """
        DELETE FROM KPI_INGRESOS_IMG_MES WHERE año = YEAR(CURDATE()) AND Periodo = 'Acumulado' and metrica = 'ingresos';
        """
        # Ejecutar la consulta de borrado
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de borrado

        # Consulta SQL para insertar los nuevos datos
        insert_query = """
        INSERT INTO KPI_INGRESOS_IMG_MES (
            date,
            periodo,
            año,
            branch_office_id,
            clave,
            ind,
            cash_amount,
            cash_net_amount,
            card_amount,
            card_net_amount,
            subscribers,
            ticket_number,
            ppto,
            metrica
        )
        SELECT
            A.date,
            'Acumulado' AS periodo,
            (B.Año * 1) AS año,
            A.branch_office_id,
            (A.clave * 1) as clave, 
            C.ind,
            SUM(A.cash_amount) AS cash_amount,
            SUM(ROUND((A.cash_amount) / 1.19)) AS cash_net_amount,
            SUM(A.card_amount) AS card_amount,
            SUM(ROUND((A.card_amount) / 1.19)) AS card_net_amount,
            SUM(A.subscribers) AS subscribers,
            SUM(A.ticket_number) AS ticket_number,
            '0' AS ppto,
            'ingresos' AS metrica
        FROM
            (SELECT
                   date,
                   branch_office_id,
                   cash_amount,
                   card_amount,
                   subscribers,
                   ticket_number,
                   CONCAT(
                        branch_office_id,
                        DATE_FORMAT(date, '%Y'),
                        DATE_FORMAT(date, '%m')
                    ) AS clave
                FROM CABECERA_TRANSACCIONES
            ) AS A
            LEFT JOIN DM_PERIODO AS B ON A.date = B.Fecha
            LEFT JOIN QRY_IND_SSS AS C ON TRIM(A.clave) = TRIM(C.clave)
        WHERE
            DAY(A.date) < DAY(CURDATE()) AND
            MONTH(A.date) = MONTH(CURDATE()) AND
            YEAR(A.date) = YEAR(CURDATE())
        GROUP BY
            A.date,
            A.branch_office_id,
            B.Periodo,
            B.Año,
            A.clave,
            C.ind
        ORDER BY
            A.branch_office_id ASC;
        """

        # Ejecutar la consulta de inserción
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Cerrar la conexión
        cursor.close()
        connection.close()

        st.success("Datos de ingresos acumulados actual, ha sido actualizados correctamente!")

    except Error as err:
        st.error(f"Error al actualizar los ingresos acumulados actuales: {err}")

# Función para actualizar el KPI_INGRESOS_IMG_MES Ingresos Mensual Actual
def update_ingresos_mes_actual():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Consulta SQL para borrar los datos existentes en la tabla KPI_INGRESOS_IMG_MES para el mes actual
        delete_query = """
        DELETE FROM KPI_INGRESOS_IMG_MES WHERE año = YEAR(CURDATE()) AND Periodo = 'Mensual' AND metrica = 'ingresos';
        """

        # Ejecutar la consulta de borrado
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de borrado

        # Consulta SQL para insertar los nuevos datos del mes actual
        insert_query = """
        INSERT INTO KPI_INGRESOS_IMG_MES (
            periodo,
            año,
            branch_office_id,
            clave,
            ind,
            cash_amount,
            cash_net_amount,
            card_amount,
            card_net_amount,
            subscribers,
            ticket_number,
            ppto,
            metrica
        )
        SELECT
            B.Periodo AS periodo,
            (B.Año * 1) AS año,
            A.branch_office_id,
            (A.clave * 1) as clave, 
            C.ind,
            SUM(A.cash_amount) AS cash_amount,
            SUM(ROUND((A.cash_amount) / 1.19)) AS cash_net_amount,
            SUM(A.card_amount) AS card_amount,
            SUM(ROUND((A.card_amount) / 1.19)) AS card_net_amount,
            SUM(A.subscribers) AS subscribers,
            SUM(A.ticket_number) AS ticket_number,
            '0' AS ppto,
            'ingresos' AS metrica
        FROM
            (
                SELECT
                    date,
                    branch_office_id,
                    cash_amount,
                    card_amount,
                    subscribers,
                    ticket_number,
                    CONCAT(
                        branch_office_id,
                        DATE_FORMAT(date, '%Y'),
                        DATE_FORMAT(date, '%m')
                    ) AS clave
                FROM
                    CABECERA_TRANSACCIONES
            ) AS A
            LEFT JOIN DM_PERIODO AS B ON A.date = B.Fecha
            LEFT JOIN QRY_IND_SSS AS C ON TRIM(A.clave) = TRIM(C.clave) 
        WHERE
            YEAR(A.date) = YEAR(CURDATE())
        GROUP BY
            A.branch_office_id,
            B.Periodo,
            B.Año,
            A.clave,
                C.ind 
        ORDER BY
            A.branch_office_id ASC;
        """

        # Ejecutar la consulta de inserción
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Cerrar la conexión
        cursor.close()
        connection.close()

        st.success("Datos de ingresos mensuales actuales actualizados correctamente.")

    except Error as err:
        st.error(f"Error al actualizar los ingresos mensuales actuales: {err}")

# Función para actualizar el KPI_INGRESOS_IMG_MES Ingresos Acumulados Anterior
def update_ingresos_acumulado_anterior():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Consulta SQL para borrar los datos existentes en la tabla KPI_INGRESOS_IMG_MES para el año anterior
        delete_query = """
        DELETE FROM KPI_INGRESOS_IMG_MES WHERE año = YEAR(CURDATE())-1 AND Periodo = 'Acumulado' AND metrica = 'ingresos';
        """
        # Ejecutar la consulta de borrado
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de borrado

        # Consulta SQL para insertar los nuevos datos del año anterior
        insert_query = """
        INSERT INTO KPI_INGRESOS_IMG_MES (
            date,
            periodo,
            año,
            branch_office_id,
            clave,
            ind,
            cash_amount,
            cash_net_amount,
            card_amount,
            card_net_amount,
            subscribers,
            ticket_number,
            ppto,
            metrica
        )
        SELECT
            A.date,
            'Acumulado' AS periodo,
            (B.Año * 1) AS año,
            A.branch_office_id,
            (A.clave * 1) as clave, 
            C.ind,
            SUM(A.cash_amount) AS cash_amount,
            SUM(ROUND((A.cash_amount) / 1.19)) AS cash_net_amount,
            SUM(A.card_amount) AS card_amount,
            SUM(ROUND((A.card_amount) / 1.19)) AS card_net_amount,
            SUM(A.subscribers) AS subscribers,
            SUM(A.ticket_number) AS ticket_number,
            '0' AS ppto,
            'ingresos' AS metrica
        FROM
            (
                SELECT
                    date,
                    branch_office_id,
                    cash_amount,
                    card_amount,
                    subscribers,
                    ticket_number,
                    CONCAT(
                        branch_office_id,
                        DATE_FORMAT(date, '%Y'),
                        DATE_FORMAT(date, '%m')
                    ) AS clave
                FROM
                    CABECERA_TRANSACCIONES
            ) AS A
            LEFT JOIN DM_PERIODO AS B ON A.date = B.Fecha
            LEFT JOIN QRY_IND_SSS AS C ON TRIM(A.clave) = TRIM(C.clave)
        WHERE
            DAY(A.date) < DAY(CURDATE()) AND
            MONTH(A.date) = MONTH(CURDATE()) AND
            YEAR(A.date) = YEAR(CURDATE())-1
        GROUP BY
                A.date,
            A.branch_office_id,
            B.Periodo,
            B.Año,
            A.clave,
            C.ind
        ORDER BY
            A.branch_office_id ASC;
        """

        # Ejecutar la consulta de inserción
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Cerrar la conexión
        cursor.close()
        connection.close()

        st.success("Datos de ingresos acumulados del año anterior actualizados correctamente.")

    except Error as err:
        st.error(f"Error al actualizar los ingresos acumulados del año anterior: {err}")
        
# Función para actualizar el KPI_INGRESOS_IMG_MES Ingresos Mensual Anterior     
def update_ingresos_mes_anterior():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Consulta SQL para borrar los datos existentes en la tabla KPI_INGRESOS_IMG_MES para el mes anterior
        delete_query = """
        DELETE FROM KPI_INGRESOS_IMG_MES WHERE año = YEAR(CURDATE()) - 1 AND Periodo = 'Mensual' AND metrica = 'ingresos';
        """

        # Ejecutar la consulta de borrado
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de borrado

        # Consulta SQL para insertar los nuevos datos del mes anterior
        insert_query = """
        INSERT INTO KPI_INGRESOS_IMG_MES (
            periodo,
            año,
            branch_office_id,
            clave,
            ind,
            cash_amount,
            cash_net_amount,
            card_amount,
            card_net_amount,
            subscribers,
            ticket_number,
            ppto,
            metrica
        )
        SELECT
            B.Periodo AS periodo,
            (B.Año * 1) AS año,
            A.branch_office_id,
            (A.clave * 1) as clave, 
            C.ind,
            SUM(A.cash_amount) AS cash_amount,
            SUM(ROUND((A.cash_amount) / 1.19)) AS cash_net_amount,
            SUM(A.card_amount) AS card_amount,
            SUM(ROUND((A.card_amount) / 1.19)) AS card_net_amount,
            SUM(A.subscribers) AS subscribers,
            SUM(A.ticket_number) AS ticket_number,
            '0' AS ppto,
            'ingresos' AS metrica
        FROM
            (
                SELECT
                    date,
                    branch_office_id,
                    cash_amount,
                    card_amount,
                    subscribers,
                    ticket_number,
                    CONCAT(
                        branch_office_id,
                        DATE_FORMAT(date, '%Y'),
                        DATE_FORMAT(date, '%m')
                    ) AS clave
                FROM
                    CABECERA_TRANSACCIONES
            ) AS A
            LEFT JOIN DM_PERIODO AS B ON A.date = B.Fecha
            LEFT JOIN QRY_IND_SSS AS C ON TRIM(A.clave) = TRIM(C.clave) 
        WHERE
            YEAR(A.date) = YEAR(CURDATE()) - 1
        GROUP BY
            A.branch_office_id,
            B.Periodo,
            B.Año,
            A.clave,
                C.ind 
        ORDER BY
            A.branch_office_id ASC;
        """

        # Ejecutar la consulta de inserción
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Cerrar la conexión
        cursor.close()
        connection.close()

        st.success("Datos de ingresos mensuales del año anterior actualizados correctamente.")

    except Error as err:
        st.error(f"Error al actualizar los ingresos mensuales del año anterior: {err}")

# Función para actualizar el KPI_INGRESOS_IMG_MES Ppto Acumulados Actual        
def update_ingresos_acumulado_ppto():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Consulta SQL para borrar los datos existentes en la tabla KPI_INGRESOS_IMG_MES para el presupuesto
        delete_query = """
        DELETE FROM KPI_INGRESOS_IMG_MES WHERE año = YEAR(CURDATE()) AND Periodo = 'Acumulado' AND metrica = 'ppto';
        """

        # Ejecutar la consulta de borrado
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de borrado

        # Consulta SQL para insertar los nuevos datos del presupuesto
        insert_query = """
        INSERT INTO KPI_INGRESOS_IMG_MES (
            date,
            periodo,
            año,
            branch_office_id,
            clave,
            ind,
            cash_amount,
            cash_net_amount,
            card_amount,
            card_net_amount,
            subscribers,
            ticket_number,
            ppto,
            metrica
        )
        SELECT
            A.date,
            'Acumulado' AS periodo,
            B.Año AS año,
            A.branch_office_id,
            (A.clave * 1) as clave, 
            C.ind,
            '0' AS cash_amount,
            '0' AS cash_net_amount,
            '0' AS card_amount,
            '0' AS card_net_amount,
            '0' AS subscribers,
            '0' AS ticket_number,
            SUM(A.cash_amount) AS ppto,
            'ppto' AS metrica
        FROM
            (
            SELECT
                date,
                branch_office_id,
                cash_amount,
                CONCAT(
                    branch_office_id,
                    DATE_FORMAT(date, '%Y'),
                    DATE_FORMAT(date, '%m')
                    ) AS clave
                FROM PPTO_DIARIO
            ) AS A
            LEFT JOIN DM_PERIODO AS B ON A.date = B.Fecha
            LEFT JOIN QRY_IND_SSS AS C ON TRIM(A.clave) = TRIM(C.clave)
        WHERE
            DAY(A.date) < DAY(CURDATE()) AND
            MONTH(A.date) = MONTH(CURDATE()) AND
            YEAR(A.date) = YEAR(CURDATE())
        GROUP BY
                A.date,
            A.branch_office_id,
            B.Periodo,
            B.Año,
            A.clave,
                C.ind
        ORDER BY
            A.branch_office_id ASC;
        """

        # Ejecutar la consulta de inserción
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Cerrar la conexión
        cursor.close()
        connection.close()

        st.success("Datos de ingresos acumulados del presupuesto actualizados correctamente.")

    except Error as err:
        st.error(f"Error al actualizar los ingresos acumulados del presupuesto: {err}")

# Función para actualizar el KPI_INGRESOS_IMG_MES Ppto Mensuales
def update_ingresos_mes_ppto():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Consulta SQL para borrar los datos existentes en la tabla KPI_INGRESOS_IMG_MES para el presupuesto mensual
        delete_query = """
        DELETE FROM KPI_INGRESOS_IMG_MES WHERE año = YEAR(CURDATE()) AND Periodo = 'Mensual' AND metrica = 'ppto';
        """

        # Ejecutar la consulta de borrado
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de borrado

        # Consulta SQL para insertar los nuevos datos del presupuesto mensual
        insert_query = """
        INSERT INTO KPI_INGRESOS_IMG_MES (
            periodo,
            año,
            branch_office_id,
            clave,
            ind,
            cash_amount,
            cash_net_amount,
            card_amount,
            card_net_amount,
            subscribers,
            ticket_number,
            ppto,
            metrica
        )
        SELECT
            B.Periodo AS periodo,
            (B.Año * 1) AS año,
            A.branch_office_id,
            (A.clave * 1) as clave, 
            C.ind,
            '0' AS cash_amount,
            '0' AS cash_net_amount,
            '0' AS card_amount,
            '0' AS card_net_amount,
            '0' AS subscribers,
            '0' AS ticket_number,
            SUM(A.cash_amount) AS ppto,
            'ppto' AS metrica
        FROM
            (
            SELECT
                date,
                branch_office_id,
                cash_amount,
                CONCAT(
                        branch_office_id,
                        DATE_FORMAT(date, '%Y'),
                        DATE_FORMAT(date, '%m')
                        ) AS clave
                FROM PPTO_DIARIO) AS A
            LEFT JOIN DM_PERIODO AS B ON A.date = B.Fecha
            LEFT JOIN QRY_IND_SSS AS C ON TRIM(A.clave) = TRIM(C.clave) 
        WHERE
            YEAR(A.date) = YEAR(CURDATE())
        GROUP BY
            A.branch_office_id,
            B.Periodo,
            B.Año,
            A.clave,
                C.ind 
        ORDER BY
            A.branch_office_id ASC;
        """

        # Ejecutar la consulta de inserción
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Cerrar la conexión
        cursor.close()
        connection.close()

        st.success("Datos de ingresos mensuales del presupuesto actualizados correctamente.")

    except Error as err:
        st.error(f"Error al actualizar los ingresos mensuales del presupuesto: {err}")

# Función para actualizar el CABECERA_ABONADOS
def update_abonados_actual():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Consulta SQL para borrar los datos existentes en la tabla CABECERA_ABONADOS
        delete_query = """
        DELETE FROM CABECERA_ABONADOS WHERE YEAR(date) = YEAR(CURDATE());
        """

        # Ejecutar la consulta de borrado
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de borrado

        # Consulta SQL para insertar los nuevos datos
        insert_query = """
        INSERT INTO CABECERA_ABONADOS (
            id,
            date,
            rut,
            cliente,
            razon_social,
            folio,
            branch_office_id,
            dte_type_id,
            status_id,
            status,
            total,
            period,
            comment,
            chip_id
        )
        SELECT
            d.id,
            DATE_FORMAT(d.added_date, "%Y-%m-%d") AS date,
            d.rut,
            c.customer AS cliente,
            CONCAT(d.rut, " - ", c.customer) AS razon_social,
            d.folio,
            (d.branch_office_id * 1) AS branch_office_id,
            d.dte_type_id,
            d.status_id,
            s.status,
            d.total,
            d.period,
            d.comment,
            d.chip_id
        FROM
            dtes d
        LEFT JOIN
            customers c ON d.rut = c.rut
        LEFT JOIN
            statuses s ON d.status_id = s.id
        WHERE
            d.rut <> '66666666-6' AND
            d.dte_version_id = 1 AND
            d.status_id > 3 AND
            d.status_id < 6 AND
            YEAR(d.added_date) = YEAR(CURDATE());
        """

        # Ejecutar la consulta de inserción
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Cerrar la conexión
        cursor.close()
        connection.close()

        st.success("Datos abonados mensuales actuales, actualizados correctamente!")

    except Error as err:
        st.error(f"Error al actualizar los datos mensuales actuales: {err}")

# Función para actualizar el DETALLE_DEPOSITOS_DIA
def update_depositos_dia():
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Consulta SQL para borrar los datos existentes en la tabla DETALLE_DEPOSITOS_DIA
        delete_query = """
        DELETE FROM DETALLE_DEPOSITOS_DIA WHERE YEAR(date) = YEAR(CURDATE());
        """

        # Ejecutar la consulta de borrado
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de borrado

        # Consulta SQL para insertar los nuevos datos
        insert_query = """
        INSERT INTO DETALLE_DEPOSITOS_DIA (
            date,
            branch_office_id,
            deposito
        )
        SELECT
            DATE_FORMAT(deposits.added_date, '%Y-%m-%d') AS date,
            deposits.branch_office_id,
            SUM(deposits.collection_amount) AS deposito
        FROM
            deposits
        LEFT JOIN
            QRY_BRANCH_OFFICES ON deposits.branch_office_id = QRY_BRANCH_OFFICES.id
        WHERE
            deposits.added_date < CURDATE() AND
            YEAR(deposits.added_date) = YEAR(CURDATE()) AND
            QRY_BRANCH_OFFICES.status_id = 7
        GROUP BY
            DATE_FORMAT(deposits.added_date, '%Y-%m-%d'),
            deposits.branch_office_id;
        """

        # Ejecutar la consulta de inserción
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Cerrar la conexión
        cursor.close()
        connection.close()

        st.success("Datos de depósitos diarios actualizados correctamente.")

    except Error as err:
        st.error(f"Error al actualizar los depósitos diarios: {err}")

# Función para actualizar el DETALLE_RECAUDACION_DIA
def update_recaudacion_dia():
    """
    Actualiza los datos de recaudación diaria en la tabla DETALLE_RECAUDACION_DIA.
    """
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        # Consulta SQL para borrar los datos existentes en la tabla
        delete_query = """
        DELETE FROM DETALLE_RECAUDACION_DIA WHERE YEAR(date) = YEAR(CURDATE());
        """

        # Ejecutar la consulta de borrado
        cursor.execute(delete_query)
        connection.commit()  # Confirmar la transacción de borrado

        # Consulta SQL para insertar los nuevos datos
        insert_query = """
        INSERT INTO DETALLE_RECAUDACION_DIA (
            date,
            branch_office_id,
            recaudacion
        )
        SELECT
            collections.added_date AS date,
            collections.branch_office_id,
            SUM(collections.cash_gross_amount) AS recaudacion
        FROM
            collections
        LEFT JOIN
            QRY_BRANCH_OFFICES ON collections.branch_office_id = QRY_BRANCH_OFFICES.id
        WHERE
            collections.added_date < CURDATE() AND  # Solo se consideran los registros de fecha anterior a la actual
            YEAR(collections.added_date) = YEAR(CURDATE()) AND  # Solo se consideran los registros del año actual
            QRY_BRANCH_OFFICES.status_id = 7  # Solo se consideran los registros de sucursales activas
        GROUP BY
            collections.added_date,
            collections.branch_office_id;
        """

        # Ejecutar la consulta de inserción
        cursor.execute(insert_query)
        connection.commit()  # Confirmar la transacción de inserción

        # Cerrar la conexión
        cursor.close()
        connection.close()

        st.success("Datos de recaudación diaria actualizados correctamente.")

    except Error as err:
        st.error(f"Error al actualizar la recaudación diaria: {err}")

# --- INICIO DE NUEVO CÓDIGO PARA ASISTENCIA ---

def parse_time_safe(time_input):
    if pd.isna(time_input): return None
    time_str = str(time_input).split('.')[0]
    for fmt in ('%H:%M:%S', '%H:%M'):
        try: return datetime.strptime(time_str, fmt).time()
        except ValueError: pass
    return None

def calculate_time_diff_minutes(start_time, end_time, allow_overnight=False):
    ## CORRECCIÓN: Añadir verificación de nulos al inicio
    if pd.isna(start_time) or pd.isna(end_time):
        return 0
        
    start_dt = datetime.combine(datetime.today(), start_time)
    end_dt = datetime.combine(datetime.today(), end_time)
    if allow_overnight and end_dt < start_dt: end_dt += timedelta(days=1)
    if end_dt < start_dt: return 0
    return (end_dt - start_dt).total_seconds() / 60

def calcular_horas_extra_minutos(turno_salida_time, salida_real_time):
    ## CORRECCIÓN: Añadir verificación de nulos al inicio
    if pd.isna(turno_salida_time) or pd.isna(salida_real_time):
        return 0
        
    today = datetime.today().date()
    turno_salida_dt = datetime.combine(today, turno_salida_time)
    salida_real_dt = datetime.combine(today, salida_real_time)
    if (turno_salida_dt.hour > 18 and salida_real_dt.hour < 6): salida_real_dt += timedelta(days=1)
    if salida_real_dt > turno_salida_dt: return (salida_real_dt - turno_salida_dt).total_seconds() / 60
    return 0

#FUNCIÓN DE CARGA DE ASISTENCIA 
# En tu archivo cargas.py, reemplaza la función cargar_asistencia_diaria con esta:

def cargar_asistencia_diaria(year, month, uploaded_file):
    if not uploaded_file:
        st.error("Por favor, suba un archivo de asistencia.")
        return
    try:
        with st.spinner("Procesando archivo Excel..."):
            
            # --- CORRECCIÓN 1: Leer el Excel con encabezado de dos niveles ---
            df = pd.read_excel(uploaded_file, header=[0, 1])

            # --- CORRECCIÓN 2: Aplanar los nombres de las columnas multinivel ---
            # Une los dos niveles de encabezado. Si el segundo nivel es 'Unnamed...', usa solo el primero.
            df.columns = ['_'.join(col).strip() if 'Unnamed' not in str(col[1]) else col[0] for col in df.columns.values]
            
            # Ahora, en lugar del antiguo df.rename, vamos a mapear directamente los nombres que necesitamos
            # de los nuevos nombres de columna aplanados.
            # Los nombres de columna ahora serán: 'Código', 'RUT', 'Nombre', 'Entrada_Fecha', 'Entrada_Hora', etc.

            # Limpieza y preparación de datos
            df['Trabajador'] = (df['Nombre'].fillna('') + ' ' + df['Primer Apellido'].fillna('') + ' ' + df['Segundo Apellido'].fillna('')).str.strip()
            df['RUT'] = df['RUT'].astype(str).str.replace('.', '', regex=False)
            
            # Renombrar 'Área' a 'Sucursal' para consistencia, si existe.
            if 'Área' in df.columns:
                df.rename(columns={'Área': 'Sucursal'}, inplace=True)

            # --- CORRECCIÓN 3: Combinar fecha y hora usando los nuevos nombres de columna ---
            # Convertir las columnas de fecha y hora a string para una unión segura
            df['Fecha_Entrada_str'] = pd.to_datetime(df['Entrada_Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
            df['Hora_Entrada_str'] = pd.to_datetime(df['Entrada_Hora'], errors='coerce').dt.strftime('%H:%M:%S')
            df['Fecha_Salida_str'] = pd.to_datetime(df['Salida_Fecha'], errors='coerce').dt.strftime('%Y-%m-%d')
            df['Hora_Salida_str'] = pd.to_datetime(df['Salida_Hora'], errors='coerce').dt.strftime('%H:%M:%S')
            
            # Combinar las cadenas para crear un datetime completo y correcto
            df['EntradaFecha'] = pd.to_datetime(df['Fecha_Entrada_str'].fillna('') + ' ' + df['Hora_Entrada_str'].fillna(''), errors='coerce')
            df['SalidaFecha'] = pd.to_datetime(df['Fecha_Salida_str'].fillna('') + ' ' + df['Hora_Salida_str'].fillna(''), errors='coerce')
            
            # --- FIN DE LAS CORRECCIONES PRINCIPALES ---
            
            # El resto de la lógica de cálculo funciona igual, pero ahora se basa en las nuevas columnas
            df['Turno Entrada Time'] = df['Turno'].astype(str).str.split('-').str[0].str.strip().apply(parse_time_safe)
            df['Turno Salida Time'] = df['Turno'].astype(str).str.split('-').str[1].str.strip().apply(parse_time_safe)
            
            df['Entrada Hora Time'] = df['EntradaFecha'].dt.time
            df['Salida Hora Time'] = df['SalidaFecha'].dt.time
            
            df['JornadaTurnoMinutos'] = df.apply(lambda r: calculate_time_diff_minutes(r['Turno Entrada Time'], r['Turno Salida Time'], allow_overnight=True), axis=1)
            df['JornadaEfectivaMinutos'] = df.apply(lambda r: calculate_time_diff_minutes(r['Entrada Hora Time'], r['Salida Hora Time'], allow_overnight=True), axis=1)
            df['HorasNoTrabajadasMinutos'] = df.apply(lambda r: calculate_time_diff_minutes(r['Turno Entrada Time'], r['Entrada Hora Time']), axis=1)
            df['HorasExtraordinariasMinutos'] = df.apply(lambda r: calcular_horas_extra_minutos(r['Turno Salida Time'], r['Salida Hora Time']), axis=1)
            df['HorasOrdinariasMinutos'] = (df['JornadaEfectivaMinutos'] - df['HorasExtraordinariasMinutos']).clip(lower=0)
            
            df.dropna(subset=['EntradaFecha'], inplace=True)
            
            # Filtro para excluir registros de Gerencia
            filas_antes_filtro = len(df)
            df = df[~df['Sucursal'].str.contains("GERENCIA", case=False, na=False)]
            filas_despues_filtro = len(df)
            st.info(f"Se excluyeron {filas_antes_filtro - filas_despues_filtro} registros de asistencia pertenecientes a 'GERENCIA'.")
        
        # El resto de la función (conexión a BD e inserción) no necesita cambios, ya que creamos
        # las columnas finales con los nombres que la consulta INSERT espera.
        cnx = get_connection()
        if not cnx: return
        cursor = cnx.cursor()
        
        with st.spinner(f"Eliminando registros de asistencia existentes para {month}/{year}..."):
            delete_query = "DELETE FROM ASISTENCIA_DIARIA WHERE YEAR(EntradaFecha) = %s AND MONTH(EntradaFecha) = %s"
            cursor.execute(delete_query, (year, month))
            cnx.commit()
            st.info(f"{cursor.rowcount} registros anteriores eliminados.")
            
        with st.spinner("Insertando nuevos registros en la base de datos..."):
            insert_query = """
                INSERT INTO ASISTENCIA_DIARIA (
                    RUT, Trabajador, Especialidad, Sucursal, Contrato, Supervisor, Turno,
                    EntradaFecha, SalidaFecha, JornadaTurnoMinutos, JornadaEfectivaMinutos,
                    HorasNoTrabajadasMinutos, HorasExtraordinariasMinutos, HorasOrdinariasMinutos
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            data_to_insert = []
            for _, row in df.iterrows():
                data_to_insert.append((
                    row['RUT'], row['Trabajador'], row.get('Especialidad'), row.get('Sucursal'), row.get('Contrato'),
                    row.get('Supervisor'), row.get('Turno'),
                    row['EntradaFecha'].to_pydatetime() if pd.notna(row['EntradaFecha']) else None,
                    row['SalidaFecha'].to_pydatetime() if pd.notna(row['SalidaFecha']) else None,
                    row['JornadaTurnoMinutos'], row['JornadaEfectivaMinutos'],
                    row['HorasNoTrabajadasMinutos'], row['HorasExtraordinariasMinutos'],
                    row['HorasOrdinariasMinutos']
                ))
            
            cursor.executemany(insert_query, data_to_insert)
            cnx.commit()
            st.success(f"¡Éxito! Se han guardado {cursor.rowcount} nuevos registros de asistencia.")
            
    except Exception as e:
        st.error(f"Ocurrió un error inesperado durante el proceso de carga: {e}")
        if 'cnx' in locals() and cnx.is_connected():
            cnx.rollback()
    finally:
        if 'cnx' in locals() and cnx.is_connected():
            cursor.close()
            close_connection(cnx)

# --- FIN DE NUEVO CÓDIGO PARA ASISTENCIA ---



# --- INICIO DE NUEVA FUNCIÓN PARA INASISTENCIAS ---
def cargar_inasistencias(year, month, uploaded_file):
    """
    Procesa, VALIDA y guarda un archivo Excel de inasistencias en la base de datos,
    interpretando correctamente el formato de fecha DD/MM/YYYY.
    """
    if not uploaded_file:
        st.error("Por favor, suba un archivo de inasistencias.")
        return

    try:
        with st.spinner("Procesando y validando archivo Excel..."):
            df = pd.read_excel(uploaded_file)
            
            # Renombrar columnas
            df = df.rename(columns={
                df.columns[0]: 'Código', df.columns[1]: 'RUT', df.columns[2]: 'Primer Apellido',
                df.columns[3]: 'Segundo Apellido', df.columns[4]: 'Nombre', df.columns[5]: 'Especialidad',
                df.columns[6]: 'Sucursal', df.columns[7]: 'Contrato', df.columns[8]: 'Turno',
                df.columns[9]: 'Supervisor', df.columns[10]: 'FechaInasistencia',
                df.columns[11]: 'Motivo',
            })
            
            # --- CORRECCIÓN CLAVE: Especificar que el día va primero en el formato de fecha ---
            df['FechaInasistencia'] = pd.to_datetime(df['FechaInasistencia'], dayfirst=True, errors='coerce')
            
            # Limpieza y preparación de datos
            df['Trabajador'] = (df['Nombre'].fillna('') + ' ' + df['Primer Apellido'].fillna('') + ' ' + df['Segundo Apellido'].fillna('')).str.strip()
            df['RUT'] = df['RUT'].astype(str).str.replace('.', '', regex=False)
            
            df['Motivo'] = df['Motivo'].astype(str).replace('-', 'Sin Motivo', regex=False)
            df['Motivo'] = df['Motivo'].fillna('Sin Motivo').replace('nan', 'Sin Motivo')

            df.dropna(subset=['FechaInasistencia'], inplace=True)
            
            # Validación de fechas
            st.info(f"Validando que todas las fechas correspondan al periodo {month}/{year}...")
            df['mes_archivo'] = df['FechaInasistencia'].dt.month
            df['año_archivo'] = df['FechaInasistencia'].dt.year
            df_fechas_incorrectas = df[(df['mes_archivo'] != month) | (df['año_archivo'] != year)]
            
            if not df_fechas_incorrectas.empty:
                st.error("Error de validación: El archivo contiene fechas que no corresponden al periodo seleccionado.")
                st.write("Fechas incorrectas encontradas:")
                st.dataframe(df_fechas_incorrectas[['Trabajador', 'FechaInasistencia']])
                return
            
            df.drop(columns=['mes_archivo', 'año_archivo'], inplace=True)
            st.success("Validación de fechas completada. Todas las fechas son correctas.")
            
            # Filtro para excluir registros de Gerencia
            filas_antes_filtro = len(df)
            df = df[~df['Sucursal'].str.contains("GERENCIA", case=False, na=False)]
            filas_despues_filtro = len(df)
            st.info(f"Se excluyeron {filas_antes_filtro - filas_despues_filtro} registros pertenecientes a 'GERENCIA'.")
            
        # Conexión y operaciones de base de datos
        cnx = get_connection()
        if not cnx: return
        cursor = cnx.cursor()
        
        with st.spinner(f"Eliminando inasistencias existentes para {month}/{year}..."):
            delete_query = "DELETE FROM INASISTENCIAS WHERE YEAR(FechaInasistencia) = %s AND MONTH(FechaInasistencia) = %s"
            cursor.execute(delete_query, (year, month))
            cnx.commit()
            st.info(f"{cursor.rowcount} registros de inasistencias anteriores eliminados.")
            
        with st.spinner("Insertando nuevos registros de inasistencias..."):
            insert_query = """
                INSERT INTO INASISTENCIAS (
                    RUT, Trabajador, Especialidad, Sucursal, Contrato, Supervisor, Turno,
                    FechaInasistencia, Motivo, ObservacionPermiso
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            data_to_insert = []
            for _, row in df.iterrows():
                data_to_insert.append((
                    row['RUT'], row['Trabajador'], row.get('Especialidad'), row.get('Sucursal'), row.get('Contrato'),
                    row.get('Supervisor'), row.get('Turno'),
                    row['FechaInasistencia'].to_pydatetime().date() if pd.notna(row['FechaInasistencia']) else None,
                    row.get('Motivo'), row.get('ObservacionPermiso', None)
                ))
            
            cursor.executemany(insert_query, data_to_insert)
            cnx.commit()
            st.success(f"¡Éxito! Se han guardado {cursor.rowcount} nuevos registros de inasistencias.")
            
    except Exception as e:
        st.error(f"Ocurrió un error inesperado durante la carga de inasistencias: {e}")
        if 'cnx' in locals() and cnx.is_connected():
            cnx.rollback()
    finally:
        if 'cnx' in locals() and cnx.is_connected():
            cursor.close()
            close_connection(cnx)

# --- FIN DE NUEVA FUNCIÓN PARA INASISTENCIAS ---

# Función para cargar datos según las opciones seleccionadas
def cargar_datos(opcion1, opcion2=None, opcion3=None, year=None, month=None):
    # Esta función ya no manejará la asistencia. Se queda solo con las otras opciones.
    if opcion1 == "Informe de ventas":
        if opcion2 == "Acumulado":
            if opcion3 == "Actual":
                st.info("Comenzado la carga de datos para Informe de ventas Acumulado Actual...")
                update_ingresos_acumulado_actual()
            elif opcion3 == "Año Anterior":
                st.info("Comenzado la carga de datos para Informe de ventas Acumulado Año Anterior")
                update_ingresos_acumulado_anterior()
            elif opcion3 == "Ppto":
                st.info("Comenzado la carga de datos para Informe de ventas Acumulado Presupuesto")
                update_ingresos_acumulado_ppto()
        elif opcion2 == "Mensual":
            if opcion3 == "Actual":
                st.info("Comenzando la carga de datos para Informe de ventas Mensual Actual")
                update_ingresos_mes_actual()
            elif opcion3 == "Año Anterior":
                st.info("Comenzando la carga de datos para Informe de ventas Mensual Año Anterior")
                update_ingresos_mes_anterior()
            elif opcion3 == "Ppto":
                st.info("Comenzando la carga de datos para Informe de ventas Mensual Presupuesto")
                update_ingresos_mes_ppto()
    elif opcion1 == "Venta x hora":
        if year and month:
            df = update_venta_x_hora(year, month)
            if not df.empty:
                st.info(f"Cargando datos para venta por hora para el año {year} y mes {month} seleccionado")
            else:
                st.error("No se encontraron datos para el período seleccionado.")
    elif opcion1 == "Depositos":
        if opcion2 == "Recaudacion":
            st.info("Comenzando la carga de datos para Depositos - Recaudacion")
            update_recaudacion_dia()
        elif opcion2 == "Depositos":
            st.info("Comenzando la carga de datos para Depositos - Depositos")
            update_depositos_dia()
    elif opcion1 == "Abonados":
        st.info("Comenzando la carga de datos para Abonados Actual")
        update_abonados_actual()
    elif opcion1 == "Indicadores Economicos":
        st.info("Comenzando la carga de datos para Indicadores Económicos")
        indicadores = ["dolar", "euro", "imacec", "ipc", "tasa_desempleo", "tpm", "uf", "utm"]
        for tipo_indicador in indicadores:
            data = get_indicador_data(tipo_indicador, year)
            if data and 'serie' in data and data['serie']:
                save_to_database(data, tipo_indicador)
        st.success("Datos guardados exitosamente en la base de datos")
    else:
        st.write(f"Opción no implementada: {opcion1} - {opcion2} - {opcion3}")


# Función principal para manejar la lógica del formulario
def main(authenticated=False):
    if not authenticated:
        raise Exception("No autenticado, Necesitas autenticarte primero")
    else:
        with st.container():
            col1, col2, col3 = st.columns([2, 6, 2])
            with col2:
                st.header('Cargas Datos')
                opciones = ["Informe de ventas", "Venta x hora", "Abonados", "Depositos", "Indicadores Economicos", "Asistencia Diaria", "Inasistencias"]
                opcion1 = st.selectbox("Selecciona una opción", opciones)
                

                if opcion1 == "Asistencia Diaria":
                    st.info("Carga el archivo de asistencia mensual. Los datos del mes y año seleccionados serán reemplazados.")
                    current_year = datetime.now().year
                    year_options = list(range(current_year - 2, current_year + 2))
                    year = st.selectbox("Selecciona el año", year_options, index=year_options.index(current_year))
                    month_options = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
                    month_name = st.selectbox("Selecciona el mes", list(month_options.keys()))
                    month_number = month_options[month_name]
                    asistencia_file = st.file_uploader("Sube el archivo Excel de asistencia", type=['xlsx', 'xls'], key="asistencia_uploader")
                    
                    if st.button("Cargar Asistencia", key="carga_asistencia"):
                        if asistencia_file:
                            # Llamada directa a la función específica de asistencia
                            cargar_asistencia_diaria(year, month_number, asistencia_file)
                        else:
                            st.warning("Por favor, selecciona un archivo para cargar.")
                
                # Las otras opciones llaman a la función genérica 'cargar_datos'
                elif opcion1 == "Informe de ventas":
                    opcion2 = st.selectbox("Selecciona una opción", ["Acumulado", "Mensual"])
                    opcion3 = st.selectbox("Selecciona una opción", ["Actual", "Año Anterior", "Ppto"])
                    if st.button("Carga", key=f"carga_{opcion2}_{opcion3}"):
                        cargar_datos(opcion1, opcion2, opcion3)
                elif opcion1 == "Venta x hora":
                    year = st.selectbox("Selecciona el año", ["2023", "2024", "2025"])
                    month_options = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
                    month_name = st.selectbox("Selecciona el mes", list(month_options.keys()))
                    month_number = month_options[month_name]
                    if st.button("Cargar", key="carga_venta_dia"):
                        cargar_datos(opcion1, year=year, month=month_number)
                elif opcion1 == "Depositos":
                    opcion2 = st.selectbox("Selecciona una opción", ["Recaudacion", "Depositos"])
                    if st.button("Carga", key=f"carga_{opcion2}"):
                        cargar_datos(opcion1, opcion2)
                elif opcion1 == "Abonados":
                    if st.button("Carga", key="carga_abonados"):
                        cargar_datos(opcion1)
                elif opcion1 == "Indicadores Economicos":
                    year = st.selectbox("Selecciona el año:", [2024, 2025])
                    if st.button("Cargar Datos", key="carga_indicadores"):
                        cargar_datos(opcion1, year=year)
                # --- INICIO DEL NUEVO BLOQUE DE UI PARA INASISTENCIAS ---
                elif opcion1 == "Inasistencias":
                    st.info("Carga el archivo de inasistencias mensual. Los datos del mes y año seleccionados serán reemplazados.")
                    current_year = datetime.now().year
                    year_options = list(range(current_year - 2, current_year + 2))
                    year = st.selectbox("Selecciona el año", year_options, index=year_options.index(current_year))
                    month_options = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
                    month_name = st.selectbox("Selecciona el mes", list(month_options.keys()))
                    month_number = month_options[month_name]
                    inasistencia_file = st.file_uploader("Sube el archivo Excel de inasistencias", type=['xlsx', 'xls'], key="inasistencia_uploader")

                    if st.button("Cargar Inasistencias", key="carga_inasistencias"):
                        if inasistencia_file:
                            cargar_inasistencias(year, month_number, inasistencia_file)
                        else:
                            st.warning("Por favor, selecciona un archivo para cargar.")

if __name__ == "__main__":
    main(authenticated=check_login())