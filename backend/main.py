# backend/main.py
from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from backend.database import get_connection, close_connection, create_cursor
import bcrypt
from datetime import datetime, date, timedelta
from typing import List


app = FastAPI()
security = HTTPBasic()

class UserLogin(BaseModel):
    rut: str
    password: str

@app.post("/login")
def login(user: UserLogin):
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = "SELECT rut, full_name, hashed_password FROM users WHERE rut = %s"
            cursor.execute(query, (user.rut,))
            result = cursor.fetchone()
            if result:
                hashed_password = result['hashed_password']
                if bcrypt.checkpw(user.password.encode('utf-8'), hashed_password.encode('utf-8')):
                    return {"message": "Login successful", "user": result}
                else:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
            else:
                raise HTTPException(status_code=401, detail="Invalid credentials")
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
@app.get("/api/usuarios/{usuario}")
def get_usuario(usuario: str):
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = "SELECT rut, full_name, hashed_password FROM users WHERE rut = %s"
            cursor.execute(query, (usuario,))
            result = cursor.fetchone()
            if result:
                return result
            else:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")


@app.get("/api/usuarios/{usuario}/sucursales")
def get_usuario_sucursales(usuario: str, credentials: HTTPBasicCredentials = Depends(security)):
    cnx = get_connection('default')
    if not cnx:
        raise HTTPException(status_code=500, detail="Database connection error")

    try:
        cursor = create_cursor(cnx)
        query = """
            SELECT 
            users.rut,
            users.full_name,
            users.hashed_password,
            branch_offices.branch_office,
            branch_offices.id as branch_office_id
            FROM users
            LEFT JOIN branch_offices
            ON users.rut = branch_offices.principal_supervisor
            WHERE users.rut = %s and branch_offices.status_id = 7
        """
        cursor.execute(query, (usuario,))
        result = cursor.fetchall()

        if not result:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    finally:
        close_connection(cnx)

@app.get("/sucursales")
def get_datos():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
                SELECT
                    responsable, 
                    (id*1) as branch_office_id, 
                    branch_office, 
                    dte_code, 
                    principal AS marca, 
                    zone AS zona, 
                    segment AS segmento, 
                    address AS direccion,
                    region,
                    commune
                FROM
                    QRY_BRANCH_OFFICES
                WHERE
                    status_id = 7
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")


@app.get("/sucursales_rut")
def get_sucursales_by_rut(rut: str = Query(..., description="RUT del usuario para filtrar sucursales")):
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
                SELECT
                    users.rut,
                    users.full_name,
                    branch_offices.branch_office,
                    branch_offices.id AS branch_office_id,
                    QRY_BRANCH_OFFICES.responsable,
                    QRY_BRANCH_OFFICES.dte_code,
                    QRY_BRANCH_OFFICES.principal as marca,
                    QRY_BRANCH_OFFICES.zone as zona,
                    QRY_BRANCH_OFFICES.segment as segmento,
                    QRY_BRANCH_OFFICES.address as direccion,
                    QRY_BRANCH_OFFICES.region,
                    QRY_BRANCH_OFFICES.commune
                FROM
                    users
                LEFT JOIN branch_offices ON users.rut = branch_offices.principal_supervisor
                LEFT JOIN QRY_BRANCH_OFFICES ON branch_offices.id = QRY_BRANCH_OFFICES.id
                WHERE
                    branch_offices.status_id = 7 AND users.rut = %s
            """
            cursor.execute(query, (rut,))
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # Obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

@app.get("/periodos")
def get_periodos():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT DISTINCT
                DM_PERIODO.Periodo, 
                DM_PERIODO.Trimestre, 
                DM_PERIODO.period, 
                DM_PERIODO.`Año`
            FROM
                DM_PERIODO; """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
@app.get("/periodos_date")
def get_periodos():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT * FROM DM_PERIODO_DATE where año >= YEAR(CURDATE())-1; """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")


@app.get("/uf")
def get_uf():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT
            CONCAT(YEAR(uf.fecha),"-",IF(MONTH(uf.fecha) < 10, CONCAT('0', MONTH(uf.fecha)), MONTH(uf.fecha))) as periodo,
            ROUND(uf.valor) as valor
            FROM DM_uf AS uf
            INNER JOIN
                (SELECT
                    MAX(fecha) AS fecha
                    FROM DM_uf
                    GROUP BY
                        YEAR(fecha), 
                        MONTH(fecha)
                ) AS max_dates
                ON uf.fecha = max_dates.fecha
            WHERE YEAR(uf.fecha) = 2025
            ORDER BY
                CONCAT(YEAR(uf.fecha),"-",MONTH(uf.fecha)) ASC;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")

    
    
@app.get("/dolar")
def get_dolar():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """ 
            SELECT
                CONCAT(YEAR(fecha), "-", LPAD(MONTH(fecha), 2, '0')) AS periodo,
                ROUND(AVG(valor)) AS valor
            FROM (
                SELECT
                    fecha,
                    valor
                FROM
                    DM_dolar
                WHERE
                    YEAR(fecha) = 2025
            ) AS subquery
            GROUP BY
                CONCAT(YEAR(fecha), "-", LPAD(MONTH(fecha), 2, '0'))
            ORDER BY
                periodo ASC;"""
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
@app.get("/euro")
def get_euro():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT
                CONCAT(YEAR(fecha), "-", LPAD(MONTH(fecha), 2, '0')) AS periodo,
                ROUND(AVG(valor)) AS valor
            FROM (
                SELECT
                    fecha,
                    valor
                FROM
                    DM_euro
                WHERE
                    YEAR(fecha) = 2025
            ) AS subquery
            GROUP BY
                CONCAT(YEAR(fecha), "-", LPAD(MONTH(fecha), 2, '0'))
            ORDER BY
                periodo ASC;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    

@app.get("/ipc")
def get_ipc():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT
                CONCAT(YEAR(fecha), "-", LPAD(MONTH(fecha), 2, '0')) AS periodo,
                ROUND(valor, 2) AS valor,
                ROUND(@running_total := @running_total + valor, 2) AS acumulado
            FROM
                (SELECT
                    fecha,
                    valor
                FROM DM_ipc
                WHERE YEAR(fecha) = 2025
                ORDER BY fecha ASC
                ) AS subquery,
                (SELECT @running_total := 0) AS r
            ORDER BY fecha ASC;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
@app.get("/tasa_desempleo")
def get_tasa_desempleo():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT
                CONCAT(YEAR(fecha), "-", LPAD(MONTH(fecha), 2, '0')) AS periodo, 
                ROUND(valor, 2) AS valor
            FROM DM_tasa_desempleo
            WHERE YEAR(fecha) = 2025;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
@app.get("/imacec")
def get_imacec():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT
                CONCAT(YEAR(fecha), "-", LPAD(MONTH(fecha), 2, '0')) AS periodo, 
                ROUND(valor, 2) AS valor
            FROM DM_imacec
            WHERE YEAR(fecha) = 2025;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    
@app.get("/anac")
def get_anac():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT
                CONCAT(YEAR(fecha), "-", LPAD(MONTH(fecha), 2, '0')) AS periodo, 
                SUM(pasajeros + suv + camioneta + comercial) AS valor, 
                SUM(pasajeros) AS pasajeros, 
                SUM(suv) AS suv, 
                SUM(camioneta) AS camioneta, 
                SUM(comercial) AS comercial
            FROM
                DM_anac
            WHERE
                YEAR(fecha) >= 2024 
            GROUP BY 
                periodo;
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
@app.get("/abonados")
def get_abonados():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT *
            FROM CABECERA_ABONADOS
            WHERE YEAR(date) = YEAR(CURDATE())
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")

@app.get("/depositos")
def get_depositos():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT *
            FROM DETALLE_DEPOSITOS_DIA
            WHERE YEAR(date) = YEAR(CURDATE())
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")

@app.get("/recaudacion")
def get_recaudacion():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT *
            FROM DETALLE_RECAUDACION_DIA
            WHERE YEAR(date) = YEAR(CURDATE())
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")

@app.get("/venta_hora")
def get_recaudacion():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT * FROM DETALLE_VENTA_HORA
            WHERE YEAR(date) = YEAR(CURDATE()) and MONTH(date) = MONTH(CURDATE())
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
@app.get("/ingresos_acum_dia")
def get_ingresos_acum_dia():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT
                KPI_INGRESOS_IMG_MES.date, 
                KPI_INGRESOS_IMG_MES.periodo, 
                KPI_INGRESOS_IMG_MES.`año`, 
                KPI_INGRESOS_IMG_MES.clave, 
                KPI_INGRESOS_IMG_MES.branch_office_id, 
                KPI_INGRESOS_IMG_MES.ind, 
                KPI_INGRESOS_IMG_MES.cash_amount, 
                KPI_INGRESOS_IMG_MES.cash_net_amount, 
                KPI_INGRESOS_IMG_MES.card_amount, 
                KPI_INGRESOS_IMG_MES.card_net_amount, 
                KPI_INGRESOS_IMG_MES.subscribers, 
                KPI_INGRESOS_IMG_MES.ticket_number, 
                (KPI_INGRESOS_IMG_MES.cash_net_amount + KPI_INGRESOS_IMG_MES.card_net_amount ) as venta_neta,
                (KPI_INGRESOS_IMG_MES.cash_amount + KPI_INGRESOS_IMG_MES.card_amount ) as venta_bruta,
                (KPI_INGRESOS_IMG_MES.cash_net_amount + KPI_INGRESOS_IMG_MES.card_net_amount + KPI_INGRESOS_IMG_MES.subscribers) as ingresos_neto,
                ((KPI_INGRESOS_IMG_MES.cash_net_amount + KPI_INGRESOS_IMG_MES.card_net_amount ) * KPI_INGRESOS_IMG_MES.ind ) as venta_sss,
                ((KPI_INGRESOS_IMG_MES.cash_net_amount + KPI_INGRESOS_IMG_MES.card_net_amount + KPI_INGRESOS_IMG_MES.subscribers) * KPI_INGRESOS_IMG_MES.ind ) as ingresos_sss,
                KPI_INGRESOS_IMG_MES.ppto, 
                KPI_INGRESOS_IMG_MES.metrica
            FROM
                KPI_INGRESOS_IMG_MES
            WHERE
                periodo = 'Acumulado' AND
                metrica = 'ingresos';
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    
@app.get("/ingresos_acum_dia_ppto")
def get_ingresos_acum_ppto():
    cnx = get_connection('default')  # Usa la configuración 'default'
    if cnx:
        try:
            cursor = create_cursor(cnx)
            query = """
            SELECT * FROM KPI_INGRESOS_IMG_MES
            WHERE año = YEAR(CURDATE()) and periodo = 'Acumulado' and metrica = 'ppto'
            """
            cursor.execute(query)
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]  # obtener los nombres de las columnas
            return {"columns": columnas, "data": resultados}
        finally:
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    
# --- INICIO DEL NUEVO ENDPOINT PARA ASISTENCIA ---

@app.get("/asistencia_diaria")
def get_asistencia_diaria(
    # Parámetros de consulta opcionales con valores por defecto al mes y año actual
    year: int = Query(default=datetime.now().year, description="Año para filtrar los datos de asistencia"),
    month: int = Query(default=datetime.now().month, description="Mes para filtrar los datos de asistencia (1-12)")
):
    """
    Obtiene los registros de asistencia diaria para un mes y año específicos.
    Por defecto, devuelve los datos del mes y año actual.
    """
    cnx = get_connection('default') 
    if not cnx:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

    try:
        cursor = create_cursor(cnx)
        
        # Consulta SQL parametrizada para evitar inyección SQL y usar los parámetros
        query = """
        SELECT * FROM ASISTENCIA_DIARIA
        WHERE YEAR(EntradaFecha) = %s AND MONTH(EntradaFecha) = %s
        """
        
        # Ejecutar la consulta con los parámetros
        cursor.execute(query, (year, month))
        
        resultados = cursor.fetchall()
        
        # Si no hay resultados, no es un error, simplemente devuelve una lista vacía.
        # El frontend se encargará de mostrar el mensaje adecuado.
        
        columnas = [desc[0] for desc in cursor.description]
        
        return {"columns": columnas, "data": resultados}

    except Exception as e:
        # Captura cualquier otro error durante la ejecución de la consulta
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

    finally:
        if cnx:
            close_connection(cnx)

# --- FIN DEL NUEVO ENDPOINT ---

@app.get("/inasistencias")
def get_inasistencias(
    year: int = Query(default=datetime.now().year, description="Año para filtrar las inasistencias"),
    month: int = Query(default=datetime.now().month, description="Mes para filtrar las inasistencias (1-12)")
):
    """
    Obtiene los registros de inasistencias para un mes y año específicos.
    """
    cnx = get_connection('default') 
    if not cnx:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

    try:
        cursor = create_cursor(cnx)
        
        query = """
        SELECT * FROM INASISTENCIAS
        WHERE YEAR(FechaInasistencia) = %s AND MONTH(FechaInasistencia) = %s
        """
        
        cursor.execute(query, (year, month))
        
        resultados = cursor.fetchall()
        columnas = [desc[0] for desc in cursor.description]
        
        return {"columns": columnas, "data": resultados}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

    finally:
        if cnx:
            close_connection(cnx)

@app.get("/asistencia_turnos")
def get_asistencia_turnos():
    """
    Obtiene todos los registros de la tabla ASISTENCIA_TURNOS.
    """
    cnx = get_connection('default') 
    if not cnx:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

    try:
        cursor = create_cursor(cnx)
        
        query = "SELECT * FROM ASISTENCIA_TURNOS"
        
        cursor.execute(query)
        
        resultados = cursor.fetchall()
        
        # Si no hay resultados, no es un error, simplemente devuelve una lista vacía.
        if not resultados:
            return {"columns": [], "data": []}
            
        columnas = [desc[0] for desc in cursor.description]
        
        return {"columns": columnas, "data": resultados}

    except Exception as e:
        # Captura cualquier otro error durante la ejecución de la consulta
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

    finally:
        if cnx:
            close_connection(cnx)
            
            
@app.get("/trabajadores")
def get_trabajadores():
    """
    Obtiene los registros de trabajadores con información adicional de branch_offices y users.
    """
    cnx = get_connection('default')
    if not cnx:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

    try:
        cursor = create_cursor(cnx)

        query = """
        SELECT
            ASISTENCIA_TRABAJADOR.rut, 
            ASISTENCIA_TRABAJADOR.trabajador as Trabajador, 
            ASISTENCIA_TRABAJADOR.email, 
            ASISTENCIA_TRABAJADOR.especialidad, 
            ASISTENCIA_TRABAJADOR.horas, 
            ASISTENCIA_TRABAJADOR.branch_office_id, 
            branch_offices.branch_office as Sucursal, 
            users.full_name as Supervisor
        FROM
            ASISTENCIA_TRABAJADOR
            LEFT JOIN
            branch_offices
            ON 
            ASISTENCIA_TRABAJADOR.branch_office_id = branch_offices.id
            LEFT JOIN
            users
            ON 
            branch_offices.principal_supervisor = users.rut
        """

        cursor.execute(query)

        resultados = cursor.fetchall()

        # Si no hay resultados, devuelve una lista vacía
        if not resultados:
            return {"columns": [], "data": []}

        # Obtener los nombres de las columnas
        columnas = [desc[0] for desc in cursor.description]

        return {"columns": columnas, "data": resultados}

    except Exception as e:
        # Captura cualquier otro error durante la ejecución de la consulta
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

    finally:
        if cnx:
            close_connection(cnx)
            


            
# 1. Modelos Pydantic para la carga de datos de la malla
class MallaItem(BaseModel):
    rut: str
    fecha: date
    codigo: str

class MallaPayload(BaseModel):
    year: int
    month: int
    ruts: List[str]  # Lista de todos los RUTs de la planilla que se está guardando
    data: List[MallaItem]

# 2. Endpoint para guardar la planificación
@app.post("/guardar_malla", status_code=status.HTTP_201_CREATED)
def guardar_malla(payload: MallaPayload):
    """
    Guarda o actualiza la malla de planificación para un conjunto de trabajadores
    en un mes y año específicos.
    
    Lógica de operación:
    1. Borra todos los registros existentes para los RUTs y el mes/año dados.
    2. Inserta los nuevos registros de la planificación recibida.
    """
    cnx = get_connection('default')
    if not cnx:
        raise HTTPException(status_code=500, detail="Error de conexión a la base de datos")

    cursor = create_cursor(cnx)

    try:
        # --- Lógica de Borrado ---
        # Determinar el primer y último día del mes para el borrado
        primer_dia = date(payload.year, payload.month, 1)
        # Manera segura de encontrar el último día del mes
        if payload.month == 12:
            ultimo_dia = date(payload.year, 12, 31)
        else:
            ultimo_dia = date(payload.year, payload.month + 1, 1) - timedelta(days=1)

        # La consulta de borrado debe ser parametrizada para seguridad
        # El formato de placeholders %s puede variar según el conector de DB (ej. ? para otros)
        # Creamos una cadena de placeholders para la lista de RUTs: (%s, %s, %s, ...)
        ruts_placeholders = ', '.join(['%s'] * len(payload.ruts))
        
        delete_query = f"""
            DELETE FROM ASISTENCIA_MALLA 
            WHERE rut IN ({ruts_placeholders}) 
            AND fecha BETWEEN %s AND %s
        """
        
        # Los parámetros deben ser una tupla o lista plana
        delete_params = tuple(payload.ruts) + (primer_dia, ultimo_dia)
        
        cursor.execute(delete_query, delete_params)
        registros_borrados = cursor.rowcount

        # --- Lógica de Inserción ---
        if payload.data:
            insert_query = """
                INSERT INTO ASISTENCIA_MALLA (rut, fecha, codigo) 
                VALUES (%s, %s, %s)
            """
            
            # Crear una lista de tuplas para una inserción masiva y eficiente
            datos_para_insertar = [
                (item.rut, item.fecha, item.codigo) for item in payload.data
            ]
            
            cursor.executemany(insert_query, datos_para_insertar)
            registros_insertados = cursor.rowcount

        # Si todo sale bien, confirmamos los cambios en la base de datos
        cnx.commit()

        return {
            "success": True,
            "message": f"Planificación guardada. Borrados: {registros_borrados}, Insertados: {registros_insertados}."
        }

    except Exception as e:
        # Si algo falla, revertimos todos los cambios de esta transacción
        cnx.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error en la operación de base de datos: {str(e)}"
        )
    finally:
        # Siempre cerramos la conexión
        close_connection(cnx)
        
# Cópialo y pégalo en tu archivo backend/main.py

@app.get("/ventas_historicas_diarias")
def get_ventas_historicas_diarias():
    """
    Obtiene el historial completo de ventas DIARIAS por sucursal,
    calculado directamente desde la tabla de transacciones.
    Este endpoint es la base para el modelo de proyección de ventas.
    """
    cnx = get_connection('default')
    if cnx:
        try:
            cursor = create_cursor(cnx)
            
            # La consulta SQL que diseñamos, que es la correcta para tu estructura de datos.
            # Se basa en tu tabla 'CABECERA_TRANSACCIONES' y 'sucursales' (a través de la vista QRY_BRANCH_OFFICES).
            # Para mayor consistencia, usaremos QRY_BRANCH_OFFICES que ya usas en otros endpoints.
            query = """
                SELECT
                    ct.date AS fecha,
                    ct.branch_office_id,
                    s.branch_office,
                    SUM(ct.cash_amount + ct.card_amount) AS total_venta
                FROM
                    CABECERA_TRANSACCIONES ct
                JOIN
                    QRY_BRANCH_OFFICES s ON ct.branch_office_id = s.id -- Unimos con la vista QRY_BRANCH_OFFICES
                WHERE
                    s.status_id = 7 -- Aseguramos que solo sean sucursales activas
                GROUP BY
                    ct.date,
                    ct.branch_office_id,
                    s.branch_office
                ORDER BY
                    fecha,
                    s.branch_office;
            """
            
            cursor.execute(query)
            
            # Obtenemos los resultados y los nombres de las columnas, tal como lo haces en tus otros endpoints.
            resultados = cursor.fetchall()
            columnas = [desc[0] for desc in cursor.description]
            
            # Devolvemos el diccionario en el formato que espera el frontend (ventas.py y proyecciones.py).
            return {"columns": columnas, "data": resultados}
            
        except Exception as e:
            # Manejo de errores consistente con tu código existente.
            raise HTTPException(status_code=500, detail=f"Error al consultar ventas históricas: {str(e)}")
            
        finally:
            # Cerramos la conexión, como es tu práctica habitual.
            close_connection(cnx)
    else:
        raise HTTPException(status_code=500, detail="Database connection error")