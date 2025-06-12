# pages/profile.py

import streamlit as st

def show_profile():
    if st.session_state.user_info:
        st.write("Perfil de " + st.session_state.user_info['full_name'])
        st.write("Sucursales: " + ", ".join(st.session_state.user_info['sucursales']))
    else:
        st.error("No se ha encontrado información del perfil del usuario")