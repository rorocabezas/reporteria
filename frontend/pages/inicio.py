# frontend/pages/inicio.py
import streamlit as st
from menu import generarMenu

# Función para verificar el estado de login
def check_login():
    return 'logged_in' in st.session_state and st.session_state.logged_in


# Verificar si el usuario está logueado
if not check_login():
    st.error("Debes iniciar sesión para acceder a esta página.")
    st.query_params = {}
    st.rerun()


# Configuración de la página
st.title("Página de Inicio")
st.write(f"Bienvenido, {st.session_state.user_info['full_name']}!")

# Generar el menú con botón de salir
if generarMenu():
    btnSalir = st.button("Salir")
    if btnSalir:
        st.session_state.clear()
        st.rerun()

# Contenido de la página de inicio
st.write("¡Bienvenido a la aplicación!")
st.write("Aquí puedes encontrar un resumen de las funcionalidades disponibles:")
st.write("- **Indicadores Económicos**: Consulta los últimos indicadores económicos.")
st.write("- **Ventas**: Revisa las ventas realizadas.")
st.write("- **Abonados**: Consulta los documentos tributarios electrónicos.")
st.write("- **Depósitos**: Revisa los depósitos realizados.")
st.write("- **Ventas Totales**: Consulta el total de ventas.")
st.write("- **ETL**: Realiza procesos de extracción, transformación y carga de datos.")


