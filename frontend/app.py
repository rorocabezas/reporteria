# frontend/app.py

import streamlit as st
import requests
import json
from menu import generarMenu

# Configurar la página para que se vea en formato wide
st.set_page_config(
    page_title="Reportes de Gestión",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Función para verificar el estado de login
def check_login():
    return 'logged_in' in st.session_state and st.session_state.logged_in

# Función para realizar el login
def login(rut, password):
    user_data = {
        "rut": rut,
        "password": password
    }

    # Intenta hacer login
    response = requests.post("http://127.0.0.1:8000/login", json=user_data)    

    if response.status_code == 200:
        st.session_state.logged_in = True
        st.session_state.user_info = response.json().get("user")
        st.success("Login exitoso")
        st.write(f"Bienvenido, {st.session_state.user_info['full_name']}!")
        st.write(f"Rut: {st.session_state.user_info['rut']}")
        return True
    elif response.status_code == 401:
        st.error("Credenciales inválidas")
    else:
        st.error("Error al conectar con el servidor")
    return False


# Verificar si el usuario está logueado
with st.container():
    col1, col2, col3 = st.columns([3, 4, 3])
    with col2:
        if check_login():
            generarMenu()
        else:
            with st.form("Inicio de Sesión"):
                st.header('Inicio de Sesión')
                rut = st.text_input("Rut:", placeholder="12345678-9", help="Ingresa tu rut con guiones:")
                password = st.text_input("Contraseña:", type="password")
                submit = st.form_submit_button("Iniciar Sesión")
                if submit:
                    if login(rut, password):
                        st.rerun()
