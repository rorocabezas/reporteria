# pages/inasistencia.py
import streamlit as st
import pandas as pd
from datetime import datetime
import locale
import requests
from menu import generarMenu
import plotly.express as px
import plotly.graph_objects as go

# --- 1. CONFIGURACIÓN INICIAL ---

st.set_page_config(
    page_title="Dashboard Inasistencias",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🤒"
)

generarMenu()

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    st.warning("No se pudo configurar la localización en español.")

st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #c0392b 0%, #8e44ad 100%); border-radius: 10px; margin-bottom: 20px;'>
        <h1 style="color:white; font-size: 3em; margin-bottom: 10px;">
            🤒 Dashboard de Inasistencias
        </h1>
    </div>
    """, unsafe_allow_html=True)
st.markdown("---")


# --- 2. FUNCIONES AUXILIARES ---

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_from_endpoint(endpoint: str, params: dict = None):
    """Función genérica para obtener datos de la API."""
    API_BASE_URL = "http://localhost:8000"
    try:
        with st.spinner(f'Cargando datos de {endpoint}...'):
            response = requests.get(f"{API_BASE_URL}/{endpoint}", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if 'data' not in data or 'columns' not in data:
                st.error(f"Respuesta con formato incorrecto desde '{endpoint}'")
                return pd.DataFrame()
            df = pd.DataFrame(data['data'], columns=data['columns'])
            return df
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error al conectar con la API ({endpoint}): {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"💥 Error inesperado al procesar datos de '{endpoint}': {e}")
        return pd.DataFrame()



def process_inasistencia_data(df):
    """Procesa el DataFrame crudo de inasistencias."""
    if df.empty:
        return df
    df['FechaInasistencia'] = pd.to_datetime(df['FechaInasistencia'], errors='coerce')
    df['Dia Sem'] = df['FechaInasistencia'].dt.day_name().str.capitalize()
    traduccion_dias = {
        'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
        'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
    }
    df['Dia Sem'] = df['Dia Sem'].map(traduccion_dias).fillna(df['Dia Sem'])
    df['Motivo'] = df['Motivo'].fillna('No especificado')
    return df




# --- 3. LÓGICA PRINCIPAL DEL DASHBOARD ---



st.sidebar.header("Seleccionar Periodo")
current_year = datetime.now().year
selected_year = st.sidebar.selectbox("Año", list(range(current_year - 2, current_year + 2)), index=2)
selected_month = st.sidebar.selectbox("Mes", range(1, 13), index=datetime.now().month - 1)

params = {"year": selected_year, "month": selected_month}
df_raw = fetch_data_from_endpoint("inasistencias", params=params)
df_processed = process_inasistencia_data(df_raw)



if df_processed.empty:
    st.warning(f"No se encontraron datos de inasistencias para {selected_month}/{selected_year}.")
else:
    # --- CORRECCIÓN DE FLUJO: Lógica de filtrado unificada y secuencial ---
    st.sidebar.title('🔍 Filtros Adicionales')
    
    # Inicia con el DataFrame procesado completo
    df_final_filtrado = df_processed.copy()

    # Filtro 1: Supervisor
    supervisores_options = sorted(df_final_filtrado['Supervisor'].dropna().unique())
    supervisores_seleccionados = st.sidebar.multiselect('👥 Supervisor(es)', supervisores_options)
    if supervisores_seleccionados:
        df_final_filtrado = df_final_filtrado[df_final_filtrado['Supervisor'].isin(supervisores_seleccionados)]

    # Filtro 2: Sucursal (las opciones dependen del filtro anterior)
    sucursales_options = sorted(df_final_filtrado['Sucursal'].dropna().unique())
    sucursales_seleccionadas = st.sidebar.multiselect('📍 Sucursal(es)', sucursales_options)
    if sucursales_seleccionadas:
        df_final_filtrado = df_final_filtrado[df_final_filtrado['Sucursal'].isin(sucursales_seleccionadas)]

    # Filtro 3: Trabajador (las opciones dependen de los filtros anteriores)
    trabajadores_options = sorted(df_final_filtrado['Trabajador'].dropna().unique())
    trabajadores_seleccionados = st.sidebar.multiselect('👨‍💻 Trabajador(es)', trabajadores_options)
    if trabajadores_seleccionados:
        df_final_filtrado = df_final_filtrado[df_final_filtrado['Trabajador'].isin(trabajadores_seleccionados)]

    st.sidebar.markdown("---")
    
    # Filtro 4: Rango de Fechas (se inicializa con los datos ya pre-filtrados)
    fecha_min = df_final_filtrado['FechaInasistencia'].min().date()
    fecha_max = df_final_filtrado['FechaInasistencia'].max().date()
    
    fecha_inicio = st.sidebar.date_input('Fecha de Inicio', value=fecha_min, min_value=fecha_min, max_value=fecha_max, key='fecha_inicio_inasistencia')
    fecha_fin = st.sidebar.date_input('Fecha de Fin', value=fecha_max, min_value=fecha_min, max_value=fecha_max, key='fecha_fin_inasistencia')

    if fecha_inicio > fecha_fin:
        st.sidebar.error('La fecha de inicio no puede ser posterior a la fecha de fin.')
    else:
        # Aplicar el filtro de fecha
        df_final_filtrado = df_final_filtrado[
            (df_final_filtrado['FechaInasistencia'].dt.date >= fecha_inicio) & 
            (df_final_filtrado['FechaInasistencia'].dt.date <= fecha_fin)
        ]

    # Filtro 5: Motivo (las opciones dependen de TODOS los filtros anteriores)
    motivos_options = sorted(df_final_filtrado['Motivo'].dropna().unique())
    motivos_seleccionados = st.sidebar.multiselect('📋 Motivo(s)', motivos_options)
    if motivos_seleccionados:
        df_final_filtrado = df_final_filtrado[df_final_filtrado['Motivo'].isin(motivos_seleccionados)]
        
    # --- FIN DE LA LÓGICA DE FILTRADO ---

    st.subheader("📈 Métricas Clave de Inasistencias (Según Filtros)")
    if not df_final_filtrado.empty:
        total_inasistencias = len(df_final_filtrado)
        trabajadores_con_inasistencia = df_final_filtrado['Trabajador'].nunique()
        motivos_unicos = df_final_filtrado['Motivo'].nunique()
    else:
        total_inasistencias, trabajadores_con_inasistencia, motivos_unicos = 0, 0, 0

    col1, col2, col3 = st.columns(3)
    col1.metric("🚨 Total Inasistencias", f"{total_inasistencias:,}")
    col2.metric("👥 Trabajadores con Inasistencia", f"{trabajadores_con_inasistencia:,}")
    col3.metric("📋 Motivos Distintos", f"{motivos_unicos:,}")
    st.markdown("---")

    tab_visual, tab_grupos, tab_datos = st.tabs(["📊 Resumen Visual", "🏢 Análisis por Grupo", "📋 Datos Completos"])
    
    with tab_visual:
        st.header("Análisis Visual de Inasistencias")
        if not df_final_filtrado.empty:
            col1, col2 = st.columns(2)
            with col1:
                st.write("#### Inasistencias por Motivo")
                motivo_counts = df_final_filtrado['Motivo'].value_counts().nlargest(10)
                fig_motivos = px.bar(motivo_counts, y=motivo_counts.index, x=motivo_counts.values, orientation='h', 
                                     labels={'y': 'Motivo', 'x': 'Cantidad de Inasistencias'},
                                     text=motivo_counts.values)
                fig_motivos.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_motivos, use_container_width=True)

            with col2:
                st.write("#### Inasistencias por Día de la Semana")
                dias_ordenados = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                dia_counts = df_final_filtrado['Dia Sem'].value_counts().reindex(dias_ordenados).fillna(0)
                fig_dias = px.bar(dia_counts, x=dia_counts.index, y=dia_counts.values,
                                  labels={'x': 'Día de la Semana', 'y': 'Cantidad de Inasistencias'},
                                  text=dia_counts.values.astype(int))
                st.plotly_chart(fig_dias, use_container_width=True)
        else:
            st.info("No hay datos para visualizar con los filtros seleccionados.")

    with tab_grupos:
        st.header("Análisis Agrupado de Inasistencias")
        if not df_final_filtrado.empty:
            st.write("#### Resumen por Sucursal")
            summary_sucursal = df_final_filtrado.groupby('Sucursal').agg(
                Total_Inasistencias=('Trabajador', 'size'),
                Trabajadores_Unicos=('Trabajador', 'nunique')
            ).reset_index().sort_values(by='Total_Inasistencias', ascending=False)
            st.dataframe(summary_sucursal, use_container_width=True)

            st.markdown("---")

            st.write("#### Resumen por Supervisor")
            summary_supervisor = df_final_filtrado.groupby('Supervisor').agg(
                Total_Inasistencias=('Trabajador', 'size'),
                Trabajadores_Unicos=('Trabajador', 'nunique')
            ).reset_index().sort_values(by='Total_Inasistencias', ascending=False)
            st.dataframe(summary_supervisor, use_container_width=True)
        else:
            st.info("No hay datos para mostrar con los filtros seleccionados.")

    with tab_datos:
        st.header("Explorador de Datos Completos")
        if not df_final_filtrado.empty:
            st.dataframe(df_final_filtrado[['FechaInasistencia', 'Dia Sem', 'Trabajador', 'RUT', 'Sucursal', 'Supervisor', 'Motivo', 'ObservacionPermiso']], use_container_width=True)
        else:
            st.info("No hay datos para mostrar con los filtros seleccionados.")

    st.sidebar.markdown("---")
    st.sidebar.info(f"""
    **Resumen Periodo {selected_month}/{selected_year}:**
    - Total inasistencias cargadas: {len(df_processed):,}
    - Inasistencias filtradas: {len(df_final_filtrado):,}
    """)
    st.markdown("---")
    st.markdown("*Dashboard de Inasistencias ")