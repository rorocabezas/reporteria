import mysql.connector

def obtener_estructura_tabla(cursor_origen, tabla):
    """Obtiene la sentencia CREATE TABLE de la base de datos de origen."""
    try:
        cursor_origen.execute(f"SHOW CREATE TABLE {tabla}")
        create_table_result = cursor_origen.fetchone()
        if create_table_result:
            return create_table_result[1]
        else:
            print(f"No se pudo obtener la estructura de la tabla '{tabla}' en la base de datos de origen.")
            return None
    except mysql.connector.Error as err:
        print(f"Error al obtener la estructura de la tabla '{tabla}': {err}")
        return None

def crear_tabla_en_destino(cursor_destino, create_table_statement, tabla):
    """Crea la tabla en la base de datos de destino si no existe."""
    try:
        cursor_destino.execute(f"SHOW TABLES LIKE '{tabla}'")
        table_exists = cursor_destino.fetchone()
        if not table_exists:
            print(f"Creando tabla '{tabla}' en la base de datos de destino...")
            cursor_destino.execute(create_table_statement)
            print(f"Tabla '{tabla}' creada exitosamente.")
        else:
            print(f"La tabla '{tabla}' ya existe en la base de datos de destino.")
        return True
    except mysql.connector.Error as err:
        print(f"Error al crear la tabla '{tabla}' en la base de datos de destino: {err}")
        return False

def copiar_datos_uno_por_uno(cursor_origen, cursor_destino, tabla):
    """Copia los datos de la tabla de origen a la de destino fila por fila."""
    try:
        cursor_origen.execute(f"SELECT * FROM {tabla}")
        columnas = [desc[0] for desc in cursor_origen.description]
        placeholders = ', '.join(['%s'] * len(columnas))
        insert_query = f"INSERT INTO {tabla} ({', '.join(columnas)}) VALUES ({placeholders})"
        registros_copiados = 0

        for fila in cursor_origen:
            try:
                cursor_destino.execute(insert_query, fila)
                registros_copiados += 1
            except mysql.connector.Error as err:
                print(f"Error al insertar fila en la tabla '{tabla}': {err}")

        return registros_copiados

    except mysql.connector.Error as err:
        print(f"Error al leer datos de la tabla '{tabla}': {err}")
        return -1

def migrar_tabla(conexion_origen, conexion_destino, tabla):
    """Migra una tabla específica desde la base de datos de origen a la de destino."""
    cursor_origen = conexion_origen.cursor()
    cursor_destino = conexion_destino.cursor()

    print(f"\nComenzando la migración de la tabla: {tabla}")

    # 1. Obtener la estructura de la tabla de origen
    create_table_statement = obtener_estructura_tabla(cursor_origen, tabla)
    if create_table_statement:
        # 2. Crear la tabla en la base de datos de destino
        if crear_tabla_en_destino(cursor_destino, create_table_statement, tabla):
            # 3. Copiar los datos fila por fila
            registros_copiados = copiar_datos_uno_por_uno(cursor_origen, cursor_destino, tabla)
            if registros_copiados >= 0:
                conexion_destino.commit()
                print(f"Se copiaron {registros_copiados} registros a la tabla '{tabla}'.")
            else:
                conexion_destino.rollback()
                print(f"No se pudieron copiar los datos de la tabla '{tabla}'. Se realizó rollback.")
        else:
            print(f"No se pudo crear la tabla '{tabla}' en la base de datos de destino.")
    else:
        print(f"No se pudo obtener la estructura de la tabla '{tabla}'.")

    cursor_origen.close()
    cursor_destino.close()

if __name__ == "__main__":
    # Configuración de la base de datos de origen
    config_origen = {
        'host': 'erpjis.mysql.database.azure.com',
        'user': 'erpjis@erpjis',
        'password': 'Macana11',
        'database': 'erp_jis'
    }

    # Configuración de la base de datos de destino
    config_destino = {
        'host': 'jisbackend.com',
        'user': 'admin',
        'password': 'Chile2025!',
        'database': 'jisparking'
    }

    # Lista de las tablas que deseas migrar
    tablas_a_migrar = ['regions', 'communes']  # Reemplaza con los nombres de tus tablas


    conexion_origen = None
    conexion_destino = None
    try:
        # Conectar a la base de datos de origen
        conexion_origen = mysql.connector.connect(**config_origen)
        print(f"Conexión exitosa a la base de datos de origen: {config_origen['database']}")

        # Conectar a la base de datos de destino
        conexion_destino = mysql.connector.connect(**config_destino)
        print(f"Conexión exitosa a la base de datos de destino: {config_destino['database']}")

        for tabla in tablas_a_migrar:
            migrar_tabla(conexion_origen, conexion_destino, tabla)

        print("\nProceso de migración de tablas completado.")

    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        if conexion_destino:
            conexion_destino.rollback()
            print("Se realizó rollback de cualquier cambio en la base de datos de destino.")

    finally:
        # Cerrar las conexiones
        if conexion_origen and conexion_origen.is_connected():
            conexion_origen.close()
            print("Conexión a la base de datos de origen cerrada.")
        if conexion_destino and conexion_destino.is_connected():
            conexion_destino.close()
            print("Conexión a la base de datos de destino cerrada.")