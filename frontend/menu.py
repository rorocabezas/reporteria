import streamlit as st
import pandas as pd
import requests

def generarMenu():
    """Genera el menú dependiendo del usuario"""
    with st.sidebar:
        if 'user_info' in st.session_state:
            usuario = st.session_state.user_info['rut']
            # Obtener los datos del usuario
            response = requests.get(f"http://127.0.0.1:8000/api/usuarios/{usuario}")
            if response.status_code == 200:
                data = response.json()
                dfUsuario = pd.DataFrame([data])  # Convertir el diccionario a un DataFrame
                # Cargamos el nombre del usuario
                nombre = dfUsuario['full_name'].values[0]
                # Mostramos el nombre del usuario
                st.write(f"Hola **:blue-background[{nombre}]** ")
                # Mostramos los enlaces de páginas
                st.page_link("pages/inicio.py", label="Inicio", icon="🏠")
                st.subheader("Tableros")
                st.page_link("pages/indicadores.py", label="Económicos", icon="💰")
                st.page_link("pages/anac.py", label="Anac", icon="🚗")
                st.page_link("pages/ventas.py", label="Ventas", icon="🛒")
                st.page_link("pages/ventas_hora.py", label="Ventas x Hora", icon="⏱️")
                st.page_link("pages/dtes.py", label="Abonados", icon="🏷️")
                st.page_link("pages/depositos.py", label="Depositos", icon="🧮")
                st.page_link("pages/cargas.py", label="ETL", icon="🚧")
                st.page_link("pages/manuales.py", label="Manuales", icon="📋")
                st.page_link("pages/informe.py", label="Informe", icon="📅")
                st.page_link("pages/asistencia.py", label="Asistencia", icon="🕒")
                st.page_link("pages/inasistencia.py", label="Inasistencia", icon="🕒")
                st.markdown("---")
                # Botón para cerrar la sesión
                btnSalir = st.button("Salir")
                if btnSalir:
                    st.session_state.clear()
                    # Luego de borrar el Session State reiniciamos la app para mostrar la opción de usuario y clave
                    st.rerun()
            else:
                st.error("Error al obtener los datos del usuario")

