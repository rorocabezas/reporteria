# -*- coding: utf-8 -*-
# pages/asistencia.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import locale
import requests
from menu import generarMenu
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
# --- 1. CONFIGURACIÓN INICIAL ---

st.set_page_config(
    page_title="Dashboard Asistencia",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🕙"
)

generarMenu()

try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    st.warning("No se pudo configurar la localización en español.")

st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); border-radius: 10px; margin-bottom: 20px;'>
        <h1 style="color:white; font-size: 3em; margin-bottom: 10px;">
            🕙 Dashboard de Asistencia Diaria
        </h1>
    </div>
    """, unsafe_allow_html=True)
st.markdown("---")


# --- 2. FUNCIONES AUXILIARES ---

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_from_endpoint(endpoint: str, params: dict = None):
    API_BASE_URL = "http://localhost:8000"
    try:
        with st.spinner(f'Cargando datos de {endpoint}...'):
            response = requests.get(f"{API_BASE_URL}/{endpoint}", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if 'data' not in data or 'columns' not in data:
                st.error(f"Respuesta con formato incorrecto desde el endpoint '{endpoint}'")
                return pd.DataFrame()
            df = pd.DataFrame(data['data'], columns=data['columns'])
            return df
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error al conectar con la API ({endpoint}): {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"💥 Error inesperado al procesar datos de '{endpoint}': {e}")
        return pd.DataFrame()

def minutes_to_time(total_minutes):
    if pd.isna(total_minutes) or total_minutes is None: return "0:00"
    hours = int(total_minutes // 60)
    minutes = int(total_minutes % 60)
    return f"{hours}:{minutes:02d}"

def process_asistencia_data(df):
    if df.empty:
        return df
    df = df.rename(columns={
        'JornadaTurnoMinutos': 'Jornada Turno Minutos',
        'JornadaEfectivaMinutos': 'Jornada Efectiva Minutos',
        'HorasNoTrabajadasMinutos': 'Horas No Trabajadas Minutos',
        'HorasExtraordinariasMinutos': 'Horas Extraordinarias Minutos',
        'HorasOrdinariasMinutos': 'Horas Ordinarias Minutos',
        'EntradaFecha': 'Entrada Fecha Display',
        'SalidaFecha': 'Salida Fecha Display',
        'Area': 'Sucursal'
    })
    if 'Sucursal' not in df.columns and 'Área' in df.columns:
        df = df.rename(columns={'Área': 'Sucursal'})
    df['Entrada Fecha Display'] = pd.to_datetime(df['Entrada Fecha Display'], errors='coerce')
    df['Salida Fecha Display'] = pd.to_datetime(df['Salida Fecha Display'], errors='coerce')
    df['Horas Perdidas Minutos'] = (df['Jornada Turno Minutos'] - df['Jornada Efectiva Minutos']).clip(lower=0)
    df['Semana'] = 'Semana ' + df['Entrada Fecha Display'].dt.isocalendar().week.astype(str)
    df['Dia Sem'] = df['Entrada Fecha Display'].dt.day_name().str.capitalize()
    traduccion_dias = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
    df['Dia Sem'] = df['Dia Sem'].map(traduccion_dias).fillna(df['Dia Sem'])
    df['Entrada Fecha'] = df['Entrada Fecha Display'].dt.strftime('%Y-%m-%d')
    df['Entrada Hora'] = df['Entrada Fecha Display'].dt.strftime('%H:%M:%S')
    df['Salida Hora'] = df['Salida Fecha Display'].dt.strftime('%H:%M:%S')
    
    columns_to_format = ['Jornada Turno Minutos', 'Jornada Efectiva Minutos', 'Horas No Trabajadas Minutos', 'Horas Extraordinarias Minutos', 'Horas Perdidas Minutos']
    for col_minutos in columns_to_format:
        col_hm = col_minutos.replace(' Minutos', '')
        ## CORRECCIÓN CLAVE: Leer de la columna con minutos y escribir en la nueva columna formateada
        df[col_hm] = df[col_minutos].apply(minutes_to_time)
        
    return df

def generar_reporte_excel(df: pd.DataFrame, periodo: str, nombre_columna_fecha: str, titulo: str):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_reporte = df.sort_values(by=['Sucursal', nombre_columna_fecha])
        sheet_name = titulo.replace(' ', '_')[:30]
        df_reporte.to_excel(writer, index=False, sheet_name=sheet_name, startrow=4)
        workbook  = writer.book
        worksheet = writer.sheets[sheet_name]
        header_format = workbook.add_format({'bold': True, 'text_wrap': True, 'valign': 'top', 'fg_color': '#D7E4BC', 'border': 1})
        title_format = workbook.add_format({'bold': True, 'font_size': 18, 'align': 'center'})
        subtitle_format = workbook.add_format({'bold': False, 'font_size': 11, 'align': 'center'})
        worksheet.merge_range('B1:G1', titulo, title_format)
        worksheet.merge_range('B2:G2', f"Periodo Analizado: {periodo}", subtitle_format)
        worksheet.merge_range('B3:G3', f"Generado el: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}", subtitle_format)
        for col_num, value in enumerate(df_reporte.columns.values):
            worksheet.write(4, col_num, value, header_format)
        for i, col in enumerate(df_reporte.columns):
            column_len = max(df_reporte[col].astype(str).map(len).max(), len(col))
            worksheet.set_column(i, i, column_len + 2)
    return output.getvalue()

# --- 3. LÓGICA PRINCIPAL DEL DASHBOARD ---

st.sidebar.header("Seleccionar Periodo")
current_year = datetime.now().year
selected_year = st.sidebar.selectbox("Año", list(range(current_year - 2, current_year + 2)), index=2)
selected_month = st.sidebar.selectbox("Mes", range(1, 13), index=datetime.now().month - 1)

params = {"year": selected_year, "month": selected_month}
df_raw = fetch_data_from_endpoint("asistencia_diaria", params=params)
df_processed = process_asistencia_data(df_raw)

if df_processed.empty:
    st.warning(f"No se encontraron datos de asistencia para {selected_month}/{selected_year}.")
else:
    # --- FILTROS SECUENCIALES EN SIDEBAR ---
    st.sidebar.title('🔍 Filtros Adicionales')
    
    df_final_filtrado = df_processed.copy()

    supervisores_options = sorted(df_final_filtrado['Supervisor'].dropna().unique())
    supervisores_seleccionados = st.sidebar.multiselect('👥 Supervisor(es)', supervisores_options)
    if supervisores_seleccionados:
        df_final_filtrado = df_final_filtrado[df_final_filtrado['Supervisor'].isin(supervisores_seleccionados)]

    sucursales_options = sorted(df_final_filtrado['Sucursal'].dropna().unique())
    sucursales_seleccionadas = st.sidebar.multiselect('📍 Sucursal(es)', sucursales_options)
    if sucursales_seleccionadas:
        df_final_filtrado = df_final_filtrado[df_final_filtrado['Sucursal'].isin(sucursales_seleccionadas)]

    trabajadores_options = sorted(df_final_filtrado['Trabajador'].dropna().unique())
    trabajadores_seleccionados = st.sidebar.multiselect('👨‍💻 Trabajador(es)', trabajadores_options)
    if trabajadores_seleccionados:
        df_final_filtrado = df_final_filtrado[df_final_filtrado['Trabajador'].isin(trabajadores_seleccionados)]

    semanas_options = sorted(df_final_filtrado['Semana'].dropna().unique())
    semanas_seleccionadas = st.sidebar.multiselect('📅 Semana(s)', semanas_options, default=semanas_options)
    if semanas_seleccionadas:
        df_final_filtrado = df_final_filtrado[df_final_filtrado['Semana'].isin(semanas_seleccionadas)]

    st.sidebar.markdown("---")
    
    
    fecha_min = df_final_filtrado['Entrada Fecha Display'].min().date()
    fecha_max = df_final_filtrado['Entrada Fecha Display'].max().date()

    fecha_inicio = st.sidebar.date_input('Fecha de Inicio', value=fecha_min, min_value=fecha_min, max_value=fecha_max, key='fecha_inicio_asistencia')
    fecha_fin = st.sidebar.date_input('Fecha de Fin', value=fecha_max, min_value=fecha_min, max_value=fecha_max, key='fecha_fin_asistencia')

    if fecha_inicio > fecha_fin:
        st.sidebar.error('La fecha de inicio no puede ser posterior a la fecha de fin.')
    else:
        df_final_filtrado = df_final_filtrado[
            (df_final_filtrado['Entrada Fecha Display'].dt.date >= fecha_inicio) & 
            (df_final_filtrado['Entrada Fecha Display'].dt.date <= fecha_fin)
        ]

    st.subheader("📈 Métricas Clave (Según Filtros)")
    if not df_final_filtrado.empty:
        df_final_filtrado['Puntual'] = df_final_filtrado['Horas No Trabajadas Minutos'] == 0
        trabajadores_unicos = df_final_filtrado['Trabajador'].nunique()
        total_planificadas_min = df_final_filtrado['Jornada Turno Minutos'].sum()
        total_efectiva_min = df_final_filtrado['Jornada Efectiva Minutos'].sum()
        total_perdidas_min = df_final_filtrado['Horas Perdidas Minutos'].sum()
        total_extras_min = df_final_filtrado['Horas Extraordinarias Minutos'].sum()
        total_retrasos_min = df_final_filtrado['Horas No Trabajadas Minutos'].sum()
        marcas_incompletas = df_final_filtrado['Salida Fecha Display'].isna().sum()
        total_registros_filtrados = len(df_final_filtrado)
        llegadas_puntuales = df_final_filtrado['Puntual'].sum()
        tasa_puntualidad = (llegadas_puntuales / total_registros_filtrados * 100) if total_registros_filtrados > 0 else 0
    else:
        trabajadores_unicos, total_planificadas_min, total_efectiva_min, total_perdidas_min, total_extras_min, total_retrasos_min, tasa_puntualidad, marcas_incompletas = 0, 0, 0, 0, 0, 0, 0, 0

    st.markdown("##### Resumen General")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Trabajadores Únicos", f"{trabajadores_unicos:,}")
    col2.metric("🗓️ H. Planificadas", minutes_to_time(total_planificadas_min))
    col3.metric("✅ H. Efectivas", minutes_to_time(total_efectiva_min))
    col4.metric("⚠️ Marcas Incompletas", f"{marcas_incompletas}", help="Registros a los que les falta la marca de salida.")
    st.markdown("##### Desglose de Horas")
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("⚠️ H. Perdidas", minutes_to_time(total_perdidas_min), help="Diferencia entre Horas Planificadas y Efectivas.")
    col6.metric("📈 H. Extras", minutes_to_time(total_extras_min))
    col7.metric("📉 Retrasos", minutes_to_time(total_retrasos_min))
    col8.metric("🎯 Tasa Puntualidad", f"{tasa_puntualidad:.1f}%")
    st.markdown("---")

    tab_list = ["📊 Resumen Visual", "🏢 Análisis por Grupo", "👤 Detalle Individual", "📋 Datos Completos", "🗓️ Planificación", "⚠️ Marcas Incompletas", "✅ Horas Extras", "📉 Retrasos"]
    tab_visual, tab_grupos, tab_trabajador, tab_datos, tab_planificacion, tab_incompletas, tab_extras, tab_retrasos = st.tabs(tab_list)
    
    with tab_visual:
        st.header("Análisis Visual General")
        if not df_final_filtrado.empty:
            col_donut, col_tendencia = st.columns(2)
            with col_donut:
                st.write("#### Composición del Tiempo Efectivo")
                labels = ['Horas Ordinarias Minutos', 'Horas Extraordinarias Minutos', 'Horas No Trabajadas Minutos']
                values = [df_final_filtrado[label].sum() for label in labels]
                display_labels = ['Horas Ordinarias', 'Horas Extras', 'Retrasos']
                fig_donut = go.Figure(data=[go.Pie(labels=display_labels, values=values, hole=.4, marker_colors=['#4facfe', '#43e97b', '#f5576c'])])
                fig_donut.update_layout(legend_title_text='Tipo de Hora')
                st.plotly_chart(fig_donut, use_container_width=True)
            with col_tendencia:
                st.write("#### Tendencia Diaria de Horas")
                df_tendencia = df_final_filtrado.groupby(df_final_filtrado['Entrada Fecha Display'].dt.date).agg(Planificadas_Min=('Jornada Turno Minutos', 'sum'), Efectiva_Min=('Jornada Efectiva Minutos', 'sum'), Extra_Min=('Horas Extraordinarias Minutos', 'sum')).reset_index()
                df_tendencia['Horas Planificadas'] = df_tendencia['Planificadas_Min'] / 60
                df_tendencia['Horas Efectivas'] = df_tendencia['Efectiva_Min'] / 60
                df_tendencia['Horas Extras'] = df_tendencia['Extra_Min'] / 60
                fig_tendencia = px.line(df_tendencia, x='Entrada Fecha Display', y=['Horas Planificadas', 'Horas Efectivas', 'Horas Extras'], labels={'value': 'Total Horas', 'Entrada Fecha Display': 'Fecha', 'variable': 'Tipo de Hora'}, color_discrete_map={'Horas Planificadas': '#17A2B8', 'Horas Efectivas': '#28A745', 'Horas Extras': '#FFC107'})
                st.plotly_chart(fig_tendencia, use_container_width=True)
            st.markdown("---")
            st.write("#### Rankings de Trabajadores")
            col_extras, col_retrasos = st.columns(2)
            with col_extras:
                top_extras = df_final_filtrado.groupby('Trabajador')['Horas Extraordinarias Minutos'].sum().nlargest(15).sort_values(ascending=True)
                if not top_extras.empty:
                    fig_extras = px.bar(top_extras, x='Horas Extraordinarias Minutos', y=top_extras.index, orientation='h', title='Top 15: Más Horas Extras', text=top_extras.apply(minutes_to_time))
                    fig_extras.update_traces(marker_color='#38f9d7', texttemplate='%{text}', textposition='outside')
                    st.plotly_chart(fig_extras, use_container_width=True)
            with col_retrasos:
                top_retrasos = df_final_filtrado.groupby('Trabajador')['Horas No Trabajadas Minutos'].sum().nlargest(15).sort_values(ascending=True)
                if not top_retrasos.empty:
                    fig_retrasos = px.bar(top_retrasos, x='Horas No Trabajadas Minutos', y=top_retrasos.index, orientation='h', title='Top 15: Mayores Retrasos', text=top_retrasos.apply(minutes_to_time))
                    fig_retrasos.update_traces(marker_color='#f093fb', texttemplate='%{text}', textposition='outside')
                    st.plotly_chart(fig_retrasos, use_container_width=True)
        else:
            st.info("No hay datos para visualizar con los filtros seleccionados.")

    with tab_grupos:
        st.header("Análisis Agrupado")
        if not df_final_filtrado.empty:
            st.write("#### Resumen por Supervisor")
            summary_supervisor = df_final_filtrado.groupby('Supervisor').agg(
                Cantidad_Trabajadores=('Trabajador', 'nunique'), Jornada_Turno_Total_Min=('Jornada Turno Minutos', 'sum'),
                Jornada_Efectiva_Total_Min=('Jornada Efectiva Minutos', 'sum'), Horas_Perdidas_Total_Min=('Horas Perdidas Minutos', 'sum'),
                Horas_Extraordinarias_Total_Min=('Horas Extraordinarias Minutos', 'sum'),
                Horas_No_Trabajadas_Total_Min=('Horas No Trabajadas Minutos', 'sum'),
                Total_Registros=('Puntual', 'size'), Llegadas_Puntuales=('Puntual', 'sum')).reset_index()
            summary_supervisor['Tasa de Puntualidad Num'] = (summary_supervisor['Llegadas_Puntuales'] / summary_supervisor['Total_Registros'] * 100).fillna(0)
            summary_supervisor = summary_supervisor.sort_values(by='Tasa de Puntualidad Num', ascending=False).reset_index(drop=True)
            summary_supervisor['Tasa de Puntualidad'] = summary_supervisor['Tasa de Puntualidad Num'].apply(lambda x: f"{x:.1f}%")
            summary_supervisor['Horas_Planificadas_Total'] = summary_supervisor['Jornada_Turno_Total_Min'].apply(minutes_to_time)
            summary_supervisor['Jornada_Efectiva_Total'] = summary_supervisor['Jornada_Efectiva_Total_Min'].apply(minutes_to_time)
            summary_supervisor['Horas_Perdidas_Total'] = summary_supervisor['Horas_Perdidas_Total_Min'].apply(minutes_to_time)
            summary_supervisor['Horas_Extraordinarias_Total'] = summary_supervisor['Horas_Extraordinarias_Total_Min'].apply(minutes_to_time)
            summary_supervisor['Retrasos_Total'] = summary_supervisor['Horas_No_Trabajadas_Total_Min'].apply(minutes_to_time)
            total_sup_row = {'Supervisor': 'TOTAL', 'Cantidad_Trabajadores': df_final_filtrado['Trabajador'].nunique(), 'Tasa de Puntualidad': f"{(summary_supervisor['Llegadas_Puntuales'].sum() / summary_supervisor['Total_Registros'].sum() * 100):.1f}%" if summary_supervisor['Total_Registros'].sum() > 0 else "0.0%", 'Horas_Planificadas_Total': minutes_to_time(summary_supervisor['Jornada_Turno_Total_Min'].sum()), 'Jornada_Efectiva_Total': minutes_to_time(summary_supervisor['Jornada_Efectiva_Total_Min'].sum()), 'Horas_Perdidas_Total': minutes_to_time(summary_supervisor['Horas_Perdidas_Total_Min'].sum()), 'Horas_Extraordinarias_Total': minutes_to_time(summary_supervisor['Horas_Extraordinarias_Total_Min'].sum()), 'Retrasos_Total': minutes_to_time(summary_supervisor['Horas_No_Trabajadas_Total_Min'].sum())}
            df_totals_sup = pd.DataFrame([total_sup_row])
            summary_supervisor_with_totals = pd.concat([summary_supervisor, df_totals_sup], ignore_index=True)
            st.dataframe(summary_supervisor_with_totals[['Supervisor', 'Cantidad_Trabajadores', 'Tasa de Puntualidad', 'Horas_Planificadas_Total', 'Jornada_Efectiva_Total', 'Horas_Perdidas_Total', 'Horas_Extraordinarias_Total', 'Retrasos_Total']], use_container_width=True)
            st.markdown("---")
            st.write("#### Resumen por Sucursal")
            summary_area = df_final_filtrado.groupby('Sucursal').agg(
                Cantidad_Trabajadores=('Trabajador', 'nunique'), Jornada_Turno_Total_Min=('Jornada Turno Minutos', 'sum'),
                Jornada_Efectiva_Total_Min=('Jornada Efectiva Minutos', 'sum'), Horas_Perdidas_Total_Min=('Horas Perdidas Minutos', 'sum'),
                Horas_Extraordinarias_Total_Min=('Horas Extraordinarias Minutos', 'sum'), Horas_No_Trabajadas_Total_Min=('Horas No Trabajadas Minutos', 'sum'),
                Total_Registros=('Puntual', 'size'), Llegadas_Puntuales=('Puntual', 'sum')).reset_index()
            summary_area['Tasa de Puntualidad'] = (summary_area['Llegadas_Puntuales'] / summary_area['Total_Registros'] * 100).fillna(0).apply(lambda x: f"{x:.1f}%")
            summary_area['Horas_Planificadas_Total'] = summary_area['Jornada_Turno_Total_Min'].apply(minutes_to_time)
            summary_area['Jornada_Efectiva_Total'] = summary_area['Jornada_Efectiva_Total_Min'].apply(minutes_to_time)
            summary_area['Horas_Perdidas_Total'] = summary_area['Horas_Perdidas_Total_Min'].apply(minutes_to_time)
            summary_area['Horas_Extraordinarias_Total'] = summary_area['Horas_Extraordinarias_Total_Min'].apply(minutes_to_time)
            summary_area['Retrasos_Total'] = summary_area['Horas_No_Trabajadas_Total_Min'].apply(minutes_to_time)
            total_area_row = {'Sucursal': 'TOTAL', 'Cantidad_Trabajadores': df_final_filtrado['Trabajador'].nunique(), 'Tasa de Puntualidad': f"{(summary_area['Llegadas_Puntuales'].sum() / summary_area['Total_Registros'].sum() * 100):.1f}%" if summary_area['Total_Registros'].sum() > 0 else "0.0%", 'Horas_Planificadas_Total': minutes_to_time(summary_area['Jornada_Turno_Total_Min'].sum()), 'Jornada_Efectiva_Total': minutes_to_time(summary_area['Jornada_Efectiva_Total_Min'].sum()), 'Horas_Perdidas_Total': minutes_to_time(summary_area['Horas_Perdidas_Total_Min'].sum()), 'Horas_Extraordinarias_Total': minutes_to_time(summary_area['Horas_Extraordinarias_Total_Min'].sum()), 'Retrasos_Total': minutes_to_time(summary_area['Horas_No_Trabajadas_Total_Min'].sum())}
            df_totals_area = pd.DataFrame([total_area_row])
            summary_area_with_totals = pd.concat([summary_area, df_totals_area], ignore_index=True)
            st.dataframe(summary_area_with_totals[['Sucursal', 'Cantidad_Trabajadores', 'Tasa de Puntualidad', 'Horas_Planificadas_Total', 'Jornada_Efectiva_Total', 'Horas_Perdidas_Total', 'Horas_Extraordinarias_Total', 'Retrasos_Total']], use_container_width=True)
            st.markdown("---")
            st.write("#### Resumen por Trabajador (dentro de los grupos seleccionados)")
            summary_trabajador_grupo = df_final_filtrado.groupby(['Trabajador', 'Sucursal', 'Supervisor']).agg(
                Jornada_Turno_Total_Min=('Jornada Turno Minutos', 'sum'), Jornada_Efectiva_Total_Min=('Jornada Efectiva Minutos', 'sum'),
                Horas_Perdidas_Total_Min=('Horas Perdidas Minutos', 'sum'), Horas_Extraordinarias_Total_Min=('Horas Extraordinarias Minutos', 'sum'),
                Horas_No_Trabajadas_Total_Min=('Horas No Trabajadas Minutos', 'sum'), Total_Registros=('Puntual', 'size'),
                Llegadas_Puntuales=('Puntual', 'sum')).reset_index()
            summary_trabajador_grupo['Tasa de Puntualidad Num'] = (summary_trabajador_grupo['Llegadas_Puntuales'] / summary_trabajador_grupo['Total_Registros'] * 100).fillna(0)
            summary_trabajador_grupo = summary_trabajador_grupo.sort_values(by='Tasa de Puntualidad Num', ascending=False).reset_index(drop=True)
            summary_trabajador_grupo['Tasa de Puntualidad'] = summary_trabajador_grupo['Tasa de Puntualidad Num'].apply(lambda x: f"{x:.1f}%")
            summary_trabajador_grupo['Horas Planificadas'] = summary_trabajador_grupo['Jornada_Turno_Total_Min'].apply(minutes_to_time)
            summary_trabajador_grupo['Horas Efectivas'] = summary_trabajador_grupo['Jornada_Efectiva_Total_Min'].apply(minutes_to_time)
            summary_trabajador_grupo['Horas Perdidas'] = summary_trabajador_grupo['Horas_Perdidas_Total_Min'].apply(minutes_to_time)
            summary_trabajador_grupo['Horas Extras'] = summary_trabajador_grupo['Horas_Extraordinarias_Total_Min'].apply(minutes_to_time)
            summary_trabajador_grupo['Retrasos'] = summary_trabajador_grupo['Horas_No_Trabajadas_Total_Min'].apply(minutes_to_time)
            total_trab_row = {'Trabajador': 'TOTAL', 'Sucursal': '', 'Supervisor': '', 'Tasa de Puntualidad': f"{(summary_trabajador_grupo['Llegadas_Puntuales'].sum() / summary_trabajador_grupo['Total_Registros'].sum() * 100):.1f}%" if summary_trabajador_grupo['Total_Registros'].sum() > 0 else "0.0%", 'Horas Planificadas': minutes_to_time(summary_trabajador_grupo['Jornada_Turno_Total_Min'].sum()), 'Horas Efectivas': minutes_to_time(summary_trabajador_grupo['Jornada_Efectiva_Total_Min'].sum()), 'Horas Perdidas': minutes_to_time(summary_trabajador_grupo['Horas_Perdidas_Total_Min'].sum()), 'Horas Extras': minutes_to_time(summary_trabajador_grupo['Horas_Extraordinarias_Total_Min'].sum()), 'Retrasos': minutes_to_time(summary_trabajador_grupo['Horas_No_Trabajadas_Total_Min'].sum())}
            df_totals_trab = pd.DataFrame([total_trab_row])
            summary_trab_with_totals = pd.concat([summary_trabajador_grupo, df_totals_trab], ignore_index=True)
            st.dataframe(summary_trab_with_totals[['Trabajador', 'Sucursal', 'Supervisor', 'Tasa de Puntualidad', 'Horas Planificadas', 'Horas Efectivas', 'Horas Perdidas', 'Horas Extras', 'Retrasos']], use_container_width=True)
        else:
            st.info("No hay datos para mostrar con los filtros seleccionados.")

    with tab_trabajador:
        st.header("Análisis Individual por Trabajador")
        if trabajadores_seleccionados:
            df_trabajador_detalle_view = df_final_filtrado[df_final_filtrado['Trabajador'].isin(trabajadores_seleccionados)].copy()
            if not df_trabajador_detalle_view.empty:
                summary_trabajador = df_trabajador_detalle_view.groupby('Trabajador').agg(Total_Jornada_Turno_Min=('Jornada Turno Minutos', 'sum'), Total_Jornada_Efectiva_Min=('Jornada Efectiva Minutos', 'sum'), Total_Horas_Perdidas_Min=('Horas Perdidas Minutos', 'sum'), Total_Horas_No_Trabajadas_Min=('Horas No Trabajadas Minutos', 'sum'), Total_Horas_Extraordinarias_Min=('Horas Extraordinarias Minutos', 'sum')).reset_index()
                for index, row in summary_trabajador.iterrows():
                    st.markdown(f"#### Resumen para: {row['Trabajador']}")
                    trabajador_info = df_trabajador_detalle_view[df_trabajador_detalle_view['Trabajador'] == row['Trabajador']].iloc[0]
                    st.write(f"**RUT:** {trabajador_info['RUT']} | **Especialidad:** {trabajador_info['Especialidad']} | **Contrato:** {trabajador_info['Contrato']}")
                    col_t1, col_t2, col_t3, col_t4, col_t5, col_t6 = st.columns(6)
                    with col_t1: st.metric(label="🗓️ H. Planificadas", value=minutes_to_time(row['Total_Jornada_Turno_Min']))
                    with col_t2: st.metric(label="✅ H. Efectivas", value=minutes_to_time(row['Total_Jornada_Efectiva_Min']))
                    with col_t3: st.metric(label="⚠️ H. Perdidas", value=minutes_to_time(row['Total_Horas_Perdidas_Min']))
                    with col_t4: st.metric(label="📈 H. Extras", value=minutes_to_time(row['Total_Horas_Extraordinarias_Min']))
                    with col_t5: st.metric(label="📉 Retrasos", value=minutes_to_time(row['Total_Horas_No_Trabajadas_Min']))
                    with col_t6: st.metric(label="🅿️ Permisos", value="0:00")
                    st.write(f"**Detalle de Asistencia por Fecha para {row['Trabajador']}:**")
                    df_trabajador_fecha = df_trabajador_detalle_view[df_trabajador_detalle_view['Trabajador'] == row['Trabajador']].sort_values(by='Entrada Fecha Display')
                    columns_to_show_trabajador = ['Dia Sem', 'Entrada Fecha', 'Turno', 'Entrada Hora', 'Salida Hora', 'Jornada Turno', 'Jornada Efectiva', 'Horas Perdidas', 'Horas No Trabajadas', 'Horas Extraordinarias']
                    if not df_trabajador_fecha.empty:
                        total_turno_min_trab = df_trabajador_fecha['Jornada Turno Minutos'].sum()
                        total_efectiva_min_trab = df_trabajador_fecha['Jornada Efectiva Minutos'].sum()
                        total_perdidas_min_trab = df_trabajador_fecha['Horas Perdidas Minutos'].sum()
                        total_retrasos_min_trab = df_trabajador_fecha['Horas No Trabajadas Minutos'].sum()
                        total_extras_min_trab = df_trabajador_fecha['Horas Extraordinarias Minutos'].sum()
                        totales_row = {'Dia Sem': '', 'Entrada Fecha': 'TOTALES', 'Turno': '', 'Entrada Hora': '', 'Salida Hora': '', 'Jornada Turno': minutes_to_time(total_turno_min_trab), 'Jornada Efectiva': minutes_to_time(total_efectiva_min_trab), 'Horas Perdidas': minutes_to_time(total_perdidas_min_trab), 'Horas No Trabajadas': minutes_to_time(total_retrasos_min_trab), 'Horas Extraordinarias': minutes_to_time(total_extras_min_trab)}
                        df_totales_trabajador = pd.DataFrame([totales_row])
                        df_display_trabajador = pd.concat([df_trabajador_fecha[columns_to_show_trabajador], df_totales_trabajador], ignore_index=True)
                        def highlight_total_row(row):
                            return ['background-color: #e6f7ff; font-weight: bold;' if row['Entrada Fecha'] == 'TOTALES' else '' for _ in row]
                        st.dataframe(df_display_trabajador.style.apply(highlight_total_row, axis=1), use_container_width=True, height=35 * (len(df_display_trabajador) + 1))
                    st.markdown("---")
            else:
                st.warning("No se encontraron datos para los trabajadores seleccionados con los filtros actuales.")
        else:
            st.info("Seleccione uno o más trabajadores en el sidebar para ver su detalle de asistencia.")

    with tab_datos:
        st.header("Explorador de Datos Completos")
        if st.checkbox("Mostrar tabla de datos detallados (Todas las filas filtradas)"):
            if not df_final_filtrado.empty:
                columns_to_show_detailed = ['RUT', 'Trabajador', 'Sucursal', 'Supervisor', 'Dia Sem', 'Semana', 'Entrada Fecha', 'Turno', 'Jornada Turno', 'Entrada Hora', 'Salida Hora', 'Jornada Efectiva', 'Horas Perdidas', 'Horas No Trabajadas', 'Horas Extraordinarias']
                st.dataframe(df_final_filtrado[columns_to_show_detailed], use_container_width=True, height=400)
            else:
                st.info("No hay datos para mostrar con los filtros actuales.")

    with tab_incompletas:
        st.header("Registros con Marcas Incompletas")
        st.write("Estos son los registros donde falta la marca de entrada o salida, basados en los filtros seleccionados.")
        df_incompletas = df_final_filtrado[pd.isna(df_final_filtrado['Salida Fecha Display'])].copy()
        def determinar_estado(row):
            if pd.isna(row['Salida Fecha Display']):
                return "Falta Salida"
            if pd.isna(row['Entrada Fecha Display']):
                return "Falta Entrada"
            return "Completo"
        df_incompletas['Estado Marca'] = df_incompletas.apply(determinar_estado, axis=1)
        st.metric("❗️ Total Marcas Incompletas", len(df_incompletas))
        st.markdown("---")
        if not df_incompletas.empty:
            columnas_reporte = ['Entrada Fecha', 'Trabajador', 'RUT', 'Sucursal', 'Supervisor', 'Turno', 'Estado Marca']
            st.dataframe(df_incompletas[columnas_reporte], use_container_width=True)
            st.markdown("---")
            excel_data = generar_reporte_excel(df=df_incompletas[columnas_reporte], periodo=f"{selected_month}/{selected_year}", nombre_columna_fecha='Entrada Fecha', titulo='Reporte de Marcas Incompletas')
            st.download_button(label="📥 Descargar Reporte en Excel", data=excel_data, file_name=f"reporte_marcas_incompletas_{selected_year}_{selected_month}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.success("¡Excelente! No se encontraron marcas incompletas con los filtros actuales.")
            
    with tab_extras:
        st.header("Detalle de Registros con Horas Extras")
        st.write("Estos son los registros que tienen horas extras, basados en los filtros seleccionados.")
        df_extras_raw = df_final_filtrado[df_final_filtrado['Horas Extraordinarias Minutos'] > 0].copy()
        if not df_extras_raw.empty:
            df_extras = df_extras_raw.sort_values(by=['Trabajador', 'Entrada Fecha Display'], ascending=[True, True]).reset_index(drop=True)
        else:
            df_extras = df_extras_raw
        if not df_extras.empty:
            total_registros_extras = len(df_extras)
            total_minutos_extras = df_extras['Horas Extraordinarias Minutos'].sum()
            promedio_minutos_extras = df_extras['Horas Extraordinarias Minutos'].mean()
        else:
            total_registros_extras, total_minutos_extras, promedio_minutos_extras = 0, 0, 0
        col_ex1, col_ex2, col_ex3 = st.columns(3)
        col_ex1.metric("🗒️ Registros con H. Extras", f"{total_registros_extras:,}")
        col_ex2.metric("⏱️ Total Horas Extras", minutes_to_time(total_minutos_extras))
        col_ex3.metric("📊 Promedio por Registro", minutes_to_time(promedio_minutos_extras))
        st.markdown("---")
        if not df_extras.empty:
            st.write("#### Detalle Completo de Horas Extras")
            columnas_extras_mostrar = ['Entrada Fecha', 'Trabajador', 'RUT', 'Sucursal', 'Supervisor', 'Turno', 'Entrada Hora', 'Salida Hora', 'Horas Extraordinarias']
            st.dataframe(df_extras[columnas_extras_mostrar], use_container_width=True)
            st.markdown("---")
            excel_data_extras = generar_reporte_excel(df=df_extras[columnas_extras_mostrar], periodo=f"{selected_month}/{selected_year}", nombre_columna_fecha='Entrada Fecha', titulo='Reporte de Horas Extras')
            st.download_button(label="📥 Descargar Reporte de Horas Extras", data=excel_data_extras, file_name=f"reporte_horas_extras_{selected_year}_{selected_month}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_extras")
            st.markdown("---")
            st.write("#### Top 15 Registros con Más Horas Extras")
            top_15_extras = df_extras.nlargest(15, 'Horas Extraordinarias Minutos').sort_values(by='Horas Extraordinarias Minutos', ascending=True)
            top_15_extras['label'] = top_15_extras['Trabajador'] + " (" + top_15_extras['Entrada Fecha'] + ")"
            fig_top_extras = px.bar(top_15_extras, x='Horas Extraordinarias Minutos', y='label', orientation='h', labels={'label': 'Trabajador (Fecha)', 'Horas Extraordinarias Minutos': 'Minutos Extras'}, text='Horas Extraordinarias')
            fig_top_extras.update_layout(yaxis_title="Trabajador y Fecha")
            st.plotly_chart(fig_top_extras, use_container_width=True)
        else:
            st.success("👍 No se encontraron registros con horas extras con los filtros actuales.")
        
    with tab_retrasos:
        st.header("Detalle de Registros con Retrasos")
        st.write("Estos son los registros donde la hora de entrada es posterior a la hora de entrada del turno, basados en los filtros seleccionados.")
        df_retrasos_raw = df_final_filtrado[df_final_filtrado['Horas No Trabajadas Minutos'] > 0].copy()
        if not df_retrasos_raw.empty:
            df_retrasos = df_retrasos_raw.sort_values(by=['Trabajador', 'Entrada Fecha Display'], ascending=[True, True]).reset_index(drop=True)
        else:
            df_retrasos = df_retrasos_raw
        if not df_retrasos.empty:
            total_registros_retraso = len(df_retrasos)
            total_minutos_retraso = df_retrasos['Horas No Trabajadas Minutos'].sum()
            promedio_minutos_retraso = df_retrasos['Horas No Trabajadas Minutos'].mean()
        else:
            total_registros_retraso, total_minutos_retraso, promedio_minutos_retraso = 0, 0, 0
        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("🗒️ Registros con Retraso", f"{total_registros_retraso:,}")
        col_r2.metric("⏱️ Tiempo Total de Retraso", minutes_to_time(total_minutos_retraso))
        col_r3.metric("📊 Promedio por Registro", minutes_to_time(promedio_minutos_retraso))
        st.markdown("---")
        if not df_retrasos.empty:
            st.write("#### Detalle Completo de Retrasos")
            df_retrasos['Turno_Entrada_Hora'] = df_retrasos['Turno'].str.split('-').str[0].str.strip()
            columnas_retrasos_mostrar = ['Entrada Fecha', 'Trabajador', 'RUT', 'Sucursal', 'Supervisor', 'Turno_Entrada_Hora', 'Entrada Hora', 'Horas No Trabajadas']
            st.dataframe(df_retrasos[columnas_retrasos_mostrar], use_container_width=True)
            st.markdown("---")
            excel_data_retrasos = generar_reporte_excel(df=df_retrasos[columnas_retrasos_mostrar], periodo=f"{selected_month}/{selected_year}", nombre_columna_fecha='Entrada Fecha', titulo='Reporte de Retrasos')
            st.download_button(label="📥 Descargar Reporte de Retrasos", data=excel_data_retrasos, file_name=f"reporte_retrasos_{selected_year}_{selected_month}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="download_retrasos")
            st.markdown("---")
            st.write("#### Top 15 Registros con Mayores Retrasos")
            top_15_retrasos = df_retrasos.nlargest(15, 'Horas No Trabajadas Minutos').sort_values(by='Horas No Trabajadas Minutos', ascending=True)
            top_15_retrasos['label'] = top_15_retrasos['Trabajador'] + " (" + top_15_retrasos['Entrada Fecha'] + ")"
            fig_top_retrasos = px.bar(top_15_retrasos, x='Horas No Trabajadas Minutos', y='label', orientation='h', labels={'label': 'Trabajador (Fecha)', 'Horas No Trabajadas Minutos': 'Minutos de Retraso'}, text='Horas No Trabajadas')
            fig_top_retrasos.update_layout(yaxis_title="Trabajador y Fecha")
            st.plotly_chart(fig_top_retrasos, use_container_width=True)
        else:
            st.success("👍 ¡Excelente puntualidad! No se encontraron registros con retrasos con los filtros actuales.")
    
    # --- INFORMACIÓN ADICIONAL EN SIDEBAR ---
    st.sidebar.markdown("---")
    st.sidebar.info(f"""
    **Resumen Periodo {selected_month}/{selected_year}:**
    - Total registros cargados: {len(df_processed):,}
    - Registros filtrados: {len(df_final_filtrado):,}
    """)
    st.markdown("---")
    st.markdown("*Dashboard de Asistencia Diaria")