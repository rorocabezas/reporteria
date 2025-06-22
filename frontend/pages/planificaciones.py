# -*- coding: utf-8 -*-
# pages/Planificaciones.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import calendar
import requests
import hashlib
from menu import generarMenu
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import zipfile


from fpdf import FPDF

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Planificación de Turnos", layout="wide", initial_sidebar_state="expanded", page_icon="📅")
generarMenu()

st.markdown("""
    <style>
    .dataframe { font-size: 12px !important; }
    .stDataFrame > div { width: 100% !important; }
    .stDataFrame [data-testid="stDataFrameResizeHandle"] { display: none !important; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin: 0.5rem 0; }
    .warning-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin: 0.5rem 0; }
    .success-card { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin: 0.5rem 0; }
    </style>
    """, unsafe_allow_html=True)

st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #16a085 0%, #2ecc71 100%); border-radius: 10px; margin-bottom: 20px;'>
        <h1 style="color:white; font-size: 3em; margin-bottom: 10px;">
            📅 Planificación Mensual de Turnos
        </h1>
    </div>
    """, unsafe_allow_html=True)
st.markdown("---")

# --- 2. FUNCIONES AUXILIARES ---

def format_rut_with_dots(rut_str):
    if not isinstance(rut_str, str) or '-' not in rut_str: return rut_str
    body, verifier = rut_str.split('-')
    body = body.replace('.', '')
    try:
        formatted_body = f"{int(body):,}".replace(",", ".")
        return f"{formatted_body}-{verifier}"
    except ValueError:
        return rut_str

def generar_color_por_hash(texto: str):
    hash_object = hashlib.md5(texto.encode())
    hash_int = int(hash_object.hexdigest(), 16)
    hue1, hue2 = hash_int % 360, (hash_int + 35) % 360
    color1, color2 = f"hsl({hue1}, 70%, 40%)", f"hsl({hue2}, 70%, 50%)"
    return color1, color2

def get_dia_semana_es(fecha):
    dias = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
    return dias[fecha.weekday()]

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_from_endpoint(endpoint: str, params: dict = None):
    API_BASE_URL = "http://localhost:8000"
    try:
        with st.spinner(f'Cargando datos de {endpoint}...'):
            response = requests.get(f"{API_BASE_URL}/{endpoint}", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if 'data' not in data: return pd.DataFrame()
            if isinstance(data['data'], list): df = pd.DataFrame(data['data'])
            elif 'columns' in data: df = pd.DataFrame(data['data'], columns=data['columns'])
            else: return pd.DataFrame()
            return df
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error al conectar con la API ({endpoint}): {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"💥 Error inesperado al procesar datos de '{endpoint}': {e}")
        return pd.DataFrame()

def save_malla_to_endpoint(payload: dict):
    API_BASE_URL = "http://localhost:8000"
    endpoint = "guardar_malla"
    try:
        response = requests.post(f"{API_BASE_URL}/{endpoint}", json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API para guardar: {e}")
        return {"success": False, "message": f"Error de conexión: {e}"}
    except Exception as e:
        st.error(f"Error inesperado al guardar la planificación: {e}")
        return {"success": False, "message": f"Error inesperado: {e}"}

def seconds_to_time_str(value):
    if pd.isna(value) or not isinstance(value, (int, float)): return ""
    m, s = divmod(int(value), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def minutes_to_time(total_minutes):
    if pd.isna(total_minutes) or total_minutes is None or total_minutes == 0: return "0:00"
    hours, minutes = int(total_minutes // 60), int(total_minutes % 60)
    return f"{hours:02d}:{minutes:02d}"

def calcular_estadisticas_avanzadas(df_editada, turnos_dict, dates, df_personal_completo):
    stats = {}
    if df_editada.empty: return stats

    stats['total_trabajadores'] = df_editada.shape[0]
    df_melted = df_editada.melt(id_vars=['rut', 'Trabajador'], var_name='Fecha', value_name='Turno')
    df_melted = df_melted[df_melted['Turno'] != ""].copy()
    
    if df_melted.empty:
        df_horas_planificadas = df_editada[['rut']].copy()
        df_horas_planificadas['Horas_Planificadas'] = 0.0
    else:
        df_melted['Minutos'] = df_melted['Turno'].apply(lambda x: turnos_dict.get(x, {}).get('working_minutes', 0))
        df_horas_calc = df_melted.groupby('rut')['Minutos'].sum().reset_index()
        df_horas_calc['Horas_Planificadas'] = df_horas_calc['Minutos'] / 60
        df_horas_planificadas = df_horas_calc[['rut', 'Horas_Planificadas']]

    df_analisis = pd.merge(df_editada[['rut', 'Trabajador']], df_horas_planificadas, on='rut', how='left')
    df_analisis['Horas_Planificadas'] = df_analisis['Horas_Planificadas'].fillna(0)
    
    df_personal_contrato = df_personal_completo[['rut', 'horas']].drop_duplicates()
    df_analisis = pd.merge(df_analisis, df_personal_contrato, on='rut', how='left')
    
    df_analisis['Horas_Contrato_Semanal'] = pd.to_numeric(df_analisis['horas'], errors='coerce').fillna(42)
    factor_mes = len(dates) / 7.0
    df_analisis['Horas_Esperadas_Mes'] = df_analisis['Horas_Contrato_Semanal'] * factor_mes
    df_analisis['Diferencia_Horas'] = df_analisis['Horas_Planificadas'] - df_analisis['Horas_Esperadas_Mes']

    stats['analisis_horas_trabajador'] = df_analisis.sort_values(by='Trabajador').to_dict('records')
    umbral_desviacion = 0.10 
    df_analisis['Umbral_Absoluto'] = df_analisis['Horas_Esperadas_Mes'] * umbral_desviacion
    stats['trabajadores_sobreplanificados'] = df_analisis[df_analisis['Diferencia_Horas'] > df_analisis['Umbral_Absoluto']].to_dict('records')
    stats['trabajadores_subplanificados'] = df_analisis[df_analisis['Diferencia_Horas'] < -df_analisis['Umbral_Absoluto']].to_dict('records')
    stats['trabajadores_sin_turnos'] = df_analisis[df_analisis['Horas_Planificadas'] == 0].to_dict('records')

    stats['trabajadores_con_turnos'] = df_melted['rut'].nunique()
    if not df_melted.empty:
        df_melted['Fecha'] = pd.to_datetime(df_melted['Fecha'], format='%d-%m-%Y')
        df_melted['Dia_Semana'] = df_melted['Fecha'].apply(get_dia_semana_es)
        stats.update({
            'total_turnos_asignados': len(df_melted),
            'total_horas_planificadas': df_melted['Minutos'].sum() / 60,
            'promedio_horas_por_trabajador': (df_melted['Minutos'].sum() / 60) / max(stats['trabajadores_con_turnos'], 1),
            'horas_por_dia_semana': (df_melted.groupby('Dia_Semana')['Minutos'].sum() / 60).to_dict(),
            'turnos_mas_usados': df_melted['Turno'].value_counts().head(5).to_dict(),
            'cobertura_porcentaje': (df_melted['Fecha'].nunique() / len(dates)) * 100,
            'turnos_fin_semana': len(df_melted[df_melted['Fecha'].dt.weekday >= 5]),
            'horas_fin_semana': (df_melted[df_melted['Fecha'].dt.weekday >= 5]['Minutos'].sum() / 60)
        })
    return stats

def crear_graficos_estadisticas(stats):
    fig1, fig2 = None, None
    if stats.get('horas_por_dia_semana'):
        dias_esp = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
        horas_por_dia = [stats['horas_por_dia_semana'].get(dia, 0) for dia in dias_esp]
        fig1 = go.Figure(data=[go.Bar(x=dias_esp, y=horas_por_dia, marker_color='#16a085', text=np.round(horas_por_dia, 1), textposition='auto')])
        fig1.update_layout(title="Distribución de Horas por Día de la Semana", xaxis_title="Día", yaxis_title="Horas", height=400)
    
    if stats.get('turnos_mas_usados'):
        turnos = list(stats['turnos_mas_usados'].keys())
        cantidades = list(stats['turnos_mas_usados'].values())
        fig2 = go.Figure(data=[go.Pie(labels=turnos, values=cantidades, hole=0.4)])
        fig2.update_layout(title="Top 5 Turnos Más Utilizados", height=400)
    return fig1, fig2

def mostrar_horas_por_trabajador_cards(stats):
    st.subheader("Detalle de Horas por Trabajador")
    trabajadores_data = stats.get('analisis_horas_trabajador', [])
    if not trabajadores_data:
        st.info("No hay datos de trabajadores para mostrar.")
        return

    with st.container():
        cols_per_row = 4
        for i in range(0, len(trabajadores_data), cols_per_row):
            chunk = trabajadores_data[i:i + cols_per_row]
            cols = st.columns(cols_per_row)
            for j, worker_data in enumerate(chunk):
                with cols[j]:
                    planificadas = worker_data.get('Horas_Planificadas', 0)
                    esperadas = worker_data.get('Horas_Esperadas_Mes', 0)
                    diferencia = worker_data.get('Diferencia_Horas', 0)
                    color1, color2 = generar_color_por_hash(worker_data['rut'])
                    if diferencia > esperadas * 0.1: delta_color = "#f9ff91"
                    elif diferencia < -esperadas * 0.1: delta_color = "#ffb3b3"
                    else: delta_color = "#ffffff"

                    card_html = f"""
                    <div style="background: linear-gradient(135deg, {color1} 0%, {color2} 100%); padding: 1rem; border-radius: 10px; color: white; text-align: center; margin-bottom: 1rem; height: 160px; display: flex; flex-direction: column; justify-content: center;">
                        <p style="font-weight: bold; margin: 0; font-size: 0.9em; line-height: 1.2;">{worker_data['Trabajador']}</p>
                        <h3 style="margin: 0.3rem 0; font-size: 2em; font-weight: 700;">{planificadas:.1f}h</h3>
                        <p style="margin: 0; font-size: 0.8em; color: {delta_color};">
                            {diferencia:+.1f}h vs. {esperadas:.1f}h esperadas
                        </p>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)

def mostrar_metricas_principales(stats):
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(f"<div class='metric-card'><h3>{stats.get('total_trabajadores', 0)}</h3><p>Trabajadores en Planilla</p></div>", unsafe_allow_html=True)
    with col2: st.markdown(f"<div class='metric-card'><h3>{stats.get('trabajadores_con_turnos', 0)}</h3><p>Con Turnos Asignados</p></div>", unsafe_allow_html=True)
    with col3: st.markdown(f"<div class='success-card'><h3>{stats.get('total_turnos_asignados', 0)}</h3><p>Turnos Asignados</p></div>", unsafe_allow_html=True)
    with col4: st.markdown(f"<div class='success-card'><h3>{stats.get('total_horas_planificadas', 0):.1f}h</h3><p>Horas Planificadas</p></div>", unsafe_allow_html=True)
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        cobertura = stats.get('cobertura_porcentaje', 0)
        color_class = "success-card" if cobertura >= 95 else "warning-card" if cobertura >= 80 else "metric-card"
        st.markdown(f"""<div class='{color_class}'><h3>{cobertura:.1f}%</h3><p>Cobertura Diaria</p></div>""", unsafe_allow_html=True)
    with col6: st.markdown(f"<div class='metric-card'><h3>{stats.get('promedio_horas_por_trabajador', 0):.1f}h</h3><p>Promedio por Trabajador</p></div>", unsafe_allow_html=True)
    with col7: st.markdown(f"<div class='metric-card'><h3>{stats.get('turnos_fin_semana', 0)}</h3><p>Turnos Fin de Semana</p></div>", unsafe_allow_html=True)
    with col8: st.markdown(f"<div class='metric-card'><h3>{stats.get('horas_fin_semana', 0):.1f}h</h3><p>Horas Fin de Semana</p></div>", unsafe_allow_html=True)

def mostrar_alertas_inteligentes(stats):
    st.header("7. ⚠️ Alertas y Recomendaciones")
    if not stats:
        st.info("No hay datos para generar alertas.")
        return

    col_alert1, col_alert2 = st.columns(2)
    with col_alert1:
        st.write("##### Cumplimiento de Contrato")
        sobreplanificados = stats.get('trabajadores_sobreplanificados', [])
        if sobreplanificados:
            st.error("🚨 **Trabajadores Sobreplanificados**")
            for p in sobreplanificados:
                st.markdown(f"- **{p['Trabajador']}**: Planificadas **{p['Horas_Planificadas']:.1f}h** / Esperadas {p['Horas_Esperadas_Mes']:.1f}h. (Exceso de **{p['Diferencia_Horas']:.1f}h**)")
        
        subplanificados = stats.get('trabajadores_subplanificados', [])
        if subplanificados:
            st.warning("⚠️ **Trabajadores Subplanificados**")
            for p in subplanificados:
                st.markdown(f"- **{p['Trabajador']}**: Planificadas **{p['Horas_Planificadas']:.1f}h** / Esperadas {p['Horas_Esperadas_Mes']:.1f}h. (Déficit de **{abs(p['Diferencia_Horas']):.1f}h**)")

        if not sobreplanificados and not subplanificados:
            st.success("✅ **Cumplimiento de horas contractuales dentro de los umbrales.**")

    with col_alert2:
        st.write("##### Cobertura y Asignaciones")
        if stats.get('cobertura_porcentaje', 100) < 95:
            st.error(f"🚨 **Cobertura baja**: {stats['cobertura_porcentaje']:.1f}% - Revisar días sin turnos asignados para ningún trabajador.")
        else:
            st.info("📈 Cobertura diaria sobre el 95%.")
            
        sin_turnos = stats.get('trabajadores_sin_turnos', [])
        if sin_turnos:
            st.warning(f"👥 **{len(sin_turnos)} trabajador(es) sin turnos asignados:**")
            nombres = ", ".join([p['Trabajador'] for p in sin_turnos])
            st.markdown(f"   - _{nombres}_")
            
        if stats.get('turnos_fin_semana', 0) == 0:
            st.info("📅 Sin turnos de fin de semana asignados.")

def create_excel_report(df_data, sucursal, year, month):
    output = BytesIO()
    df_export = df_data.copy()
    df_export['rut'] = df_export['rut'].apply(format_rut_with_dots)
    df_export.rename(columns={'rut': 'RUT', 'Trabajador': 'Nombre'}, inplace=True)
    df_export.insert(2, 'Área', sucursal)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        header_df_1 = pd.DataFrame([['Trabajador', '', '', f"{month:02d}-{year}"] + [''] * (len(df_export.columns) - 4)], columns=df_export.columns)
        header_df_1.to_excel(writer, sheet_name='Planificacion', startrow=0, header=False, index=False)
        df_export.to_excel(writer, sheet_name='Planificacion', startrow=1, header=True, index=False)
    return output.getvalue()


def crear_pdf_trabajador(worker_data, schedule_df, weekly_summary, sucursal, month_name, year):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()    
    # --- 1. ENCABEZADO CON LOGO Y DATOS ALINEADOS ---
    try:
        pdf.image("pages/logo.jpg", x=170, y=8, w=30)
    except FileNotFoundError:
        pass

    pdf.set_y(12)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 8, "Planilla de Turnos Mensual", 0, 1, "C")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(20, 5, "Nombre:", 0, 0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(85, 5, worker_data['Trabajador'], 0, 0)
    
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(15, 5, "RUT:")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, format_rut_with_dots(worker_data['rut']), 0, 1)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(20, 5, "Sucursal:")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(85, 5, sucursal, 0, 0)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(15, 5, "Periodo:")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, f"{month_name.capitalize()} {year}", 0, 1)
    
    pdf.ln(6)

    # --- 2. TABLA DE HORARIOS DETALLADA (CENTRADA) ---
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(224, 224, 224)
    col_widths = [30, 25, 20, 20, 40]
    total_width = sum(col_widths)
    start_x = (pdf.w - total_width) / 2
    pdf.set_x(start_x)

    headers = ["Día", "Fecha", "Turno", "Jornada", "Horario"]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 6, header, 1, 0, "C", 1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for _, row in schedule_df.iterrows():
        pdf.set_x(start_x)
        pdf.cell(col_widths[0], 5, str(row['Dia_Semana']), 1, 0, "L")
        pdf.cell(col_widths[1], 5, str(row['Fecha_str']), 1, 0, "C")
        pdf.cell(col_widths[2], 5, str(row['Turno']), 1, 0, "C")
        pdf.cell(col_widths[3], 5, str(row['working_time']), 1, 0, "C")
        pdf.cell(col_widths[4], 5, str(row['desde - hasta']), 1, 1, "C")

    # --- 3. TABLA DE RESUMEN DE HORAS (CENTRADA) ---
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Resumen de Horas", 0, 1, "C")
    
    pdf.set_font("Helvetica", "B", 8)
    summary_headers = list(weekly_summary.columns)
    num_summary_cols = len(summary_headers)
    summary_total_width = total_width
    summary_col_width = summary_total_width / num_summary_cols
    
    start_x_summary = (pdf.w - summary_total_width) / 2
    pdf.set_x(start_x_summary)
    
    for header in summary_headers:
        pdf.cell(summary_col_width, 6, header, 1, 0, "C", 1)
    pdf.ln()

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(start_x_summary)
    for header in summary_headers:
        pdf.cell(summary_col_width, 6, weekly_summary.iloc[0][header], 1, 0, "C")
    pdf.ln()

    # --- 4. SECCIÓN DE FIRMA (POSICIONADA AL FINAL) ---
    # Posicionar a 250mm desde el borde superior
    pdf.set_y(250)
    
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, "Recibido Conforme,", 0, 1, "L")
    pdf.ln(8)
    
    # Líneas y texto para Firma y Fecha en la misma "fila" visual
    pdf.line(pdf.get_x() + 10, pdf.get_y(), pdf.get_x() + 80, pdf.get_y())
    pdf.line(pdf.get_x() + 115, pdf.get_y(), pdf.get_x() + 165, pdf.get_y())
    
    pdf.cell(95, 6, "Firma Trabajador", 0, 0, "C")
    pdf.cell(0, 6, "Fecha", 0, 1, "C")
    
    return pdf.output()
def generar_zip_con_pdfs(df_editada, turnos_dict, sucursal, month_name, year, dates):
    df_melted = df_editada.melt(id_vars=['rut', 'Trabajador'], var_name='Fecha_str', value_name='Turno')
    df_melted = df_melted[df_melted['Turno'] != ""].copy()
    if df_melted.empty:
        return None

    df_melted['Fecha'] = pd.to_datetime(df_melted['Fecha_str'], format='%d-%m-%Y')
    df_melted['Dia_Semana'] = df_melted['Fecha'].apply(get_dia_semana_es)
    df_melted['working_minutes'] = df_melted['Turno'].apply(lambda x: turnos_dict.get(x, {}).get('working_minutes', 0))
    df_melted['working_time'] = df_melted['working_minutes'].apply(minutes_to_time)
    df_melted['desde - hasta'] = df_melted['Turno'].apply(lambda x: turnos_dict.get(x, {}).get('desde - hasta', '-'))
    
    df_melted['Semana'] = 'Semana ' + df_melted['Fecha'].dt.isocalendar().week.astype(str)
    pivot_resumen = df_melted.pivot_table(index='rut', columns='Semana', values='working_minutes', aggfunc='sum').fillna(0)
    pivot_formateado = pivot_resumen.applymap(minutes_to_time)
    pivot_formateado['Total Mes'] = pivot_resumen.sum(axis=1).apply(minutes_to_time)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        for _, worker in df_editada.iterrows():
            worker_rut, worker_name_for_file = worker['rut'], worker['Trabajador'].replace(" ", "_")
            schedule_df = df_melted[df_melted['rut'] == worker_rut].sort_values(by='Fecha')
            weekly_summary_worker = pivot_formateado[pivot_formateado.index == worker_rut]
            if schedule_df.empty: continue
            pdf_bytes = crear_pdf_trabajador(worker, schedule_df, weekly_summary_worker, sucursal, month_name, year)
            file_name = f"Planificacion_{worker_name_for_file}_{month_name}_{year}.pdf"
            zip_file.writestr(file_name, pdf_bytes)
            
    return zip_buffer.getvalue()

# --- 3. LÓGICA PRINCIPAL DEL DASHBOARD ---
df_personal = fetch_data_from_endpoint("trabajadores")

if 'plantilla_generada' not in st.session_state:
    st.session_state.plantilla_generada = False

col_izq, col_der = st.columns(2)
with col_izq:
    st.subheader("1. Seleccione Sucursal a Planificar")
    if not df_personal.empty:
        supervisores_options = sorted(df_personal['Supervisor'].dropna().unique())
        selected_supervisor = st.selectbox('Supervisor:', supervisores_options, key='supervisor_selector')
        df_filtrado_sup = df_personal[df_personal['Supervisor'] == selected_supervisor]
        sucursales_options = sorted(df_filtrado_sup['Sucursal'].dropna().unique())
        selected_sucursal = st.selectbox('Sucursal:', sucursales_options, key='sucursal_selector')
    else:
        st.error("No se pudo cargar la lista de personal.")
        st.stop()
with col_der:
    st.subheader("2. Seleccione  Periodo")
    col_año, col_mes = st.columns(2)
    with col_año:
        current_year = datetime.now().year
        selected_year = st.selectbox("Año:", list(range(current_year - 1, current_year + 3)), index=2, key='year_selector')
    with col_mes:
        month_options = {"Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12}
        month_name = st.selectbox("Mes:", list(month_options.keys()), index=datetime.now().month - 1, key='month_selector')
        selected_month = month_options[month_name]
    def on_generate_click():
        st.session_state.plantilla_generada = True
        st.session_state.year_plan = selected_year
        st.session_state.month_plan = selected_month
        st.session_state.month_name_plan = month_name
        st.session_state.supervisor_plan = selected_supervisor
        st.session_state.sucursal_plan = selected_sucursal
        if "planificacion_editor" in st.session_state: del st.session_state["planificacion_editor"]
    st.button("📝 Generar Plantilla de Planificación", on_click=on_generate_click, type="primary")

st.markdown("---")

# --- 4. RENDERIZACIÓN DE LA PLANTILLA Y DETALLES ---
if st.session_state.plantilla_generada:
    year, month, month_name, supervisor, sucursal = st.session_state.year_plan, st.session_state.month_plan, st.session_state.month_name_plan, st.session_state.supervisor_plan, st.session_state.sucursal_plan
    st.header(f"3. Ingrese los Turnos para {sucursal}")
    st.subheader(f"Periodo: {month_name.upper()} {year} | Supervisor: {supervisor}")
    df_turnos_validos = fetch_data_from_endpoint("asistencia_turnos")
    if df_turnos_validos.empty:
        st.error("No se pudieron cargar los tipos de turno desde la BD.")
    else:
        lista_turnos = [""] + sorted(df_turnos_validos['codigo'].tolist())
        if 'working' in df_turnos_validos.columns:
            df_turnos_validos['working_minutes'] = df_turnos_validos['working'] / 60
            df_turnos_validos['working_time'] = df_turnos_validos['working'].apply(seconds_to_time_str)
        else:
             st.error("La columna 'working' no se encontró en los datos de turnos.")
             st.stop()
             
        turnos_dict = df_turnos_validos.set_index('codigo').to_dict('index')
        df_plantilla_base = df_personal[
            (df_personal['Supervisor'] == supervisor) & (df_personal['Sucursal'] == sucursal)
        ][['rut', 'Trabajador']].drop_duplicates().sort_values(by='Trabajador').reset_index(drop=True)
        
        if df_plantilla_base.empty:
            st.warning("No se encontraron trabajadores para la selección.")
        else:
            _, num_days = calendar.monthrange(year, month)
            dates = [datetime(year, month, day) for day in range(1, num_days + 1)]
            columnas_planas = [d.strftime('%d-%m-%Y') for d in dates]
            df_planificacion = df_plantilla_base.copy()
            for col_name in columnas_planas: df_planificacion[col_name] = ""
            
            config_columnas = {}
            for col in columnas_planas:
                fecha_obj = datetime.strptime(col, '%d-%m-%Y')
                dia_semana_es = get_dia_semana_es(fecha_obj)
                if fecha_obj.weekday() == 6: label = f"🔴{dia_semana_es.capitalize()} {fecha_obj.day:02d}\n{col}"
                else: label = f"{dia_semana_es} {fecha_obj.day:02d}\n{col}"
                config_columnas[col] = st.column_config.SelectboxColumn(label=label, options=lista_turnos, required=False)
            
            st.info("💡 Haga clic en una celda para seleccionar un turno. Use Ctrl+C y Ctrl+V para copiar turnos entre celdas.")
            df_editada = st.data_editor(df_planificacion, column_config=config_columnas, use_container_width=True, hide_index=True, disabled=["rut", "Trabajador"], num_rows="fixed", key="planificacion_editor")
            
            st.markdown("---")
            st.header("3.1. Información del turno")

            if not df_editada.empty:
                info_campos = {'working_time': 'Jornada (working)', 'desde - hasta': 'Turno (desde - hasta)'}
                base_info_df = df_editada[['rut', 'Trabajador']].copy()
                nuevas_columnas_display, sunday_cols = [], []
                for d in dates:
                    dia_semana_es, fecha_corta = get_dia_semana_es(d), d.strftime('%d-%m-%Y')
                    header_str = f"{dia_semana_es} {d.day:02d} {fecha_corta}"
                    nuevas_columnas_display.append(header_str)
                    if d.weekday() == 6: sunday_cols.append(header_str)

                for campo_api, titulo_tabla in info_campos.items():
                    st.write(f"##### {titulo_tabla}")
                    data_matrix = []
                    for index, row in df_editada.iterrows():
                        row_data = [turnos_dict.get(row[col_fecha], {}).get(campo_api, "-") for col_fecha in columnas_planas]
                        data_matrix.append(row_data)
                    df_temp_info = pd.DataFrame(data_matrix, index=base_info_df.index, columns=nuevas_columnas_display)
                    df_info_final = pd.concat([base_info_df.reset_index(drop=True), df_temp_info.reset_index(drop=True)], axis=1)
                    st.dataframe(df_info_final.style.apply(lambda x: ['color: #d32f2f; font-weight: bold;' if (x.name in sunday_cols) else '' for i in x], axis=0), use_container_width=True, hide_index=True)

            st.markdown("---")
            st.header("4. 📋 Resumen Semanal Detallado")
            df_melted_semanal = df_editada.melt(id_vars=['rut', 'Trabajador'], var_name='Fecha', value_name='Turno')
            df_melted_semanal = df_melted_semanal[df_melted_semanal['Turno'] != ""].copy()
            if not df_melted_semanal.empty:
                df_melted_semanal['Fecha'] = pd.to_datetime(df_melted_semanal['Fecha'], format='%d-%m-%Y')
                df_melted_semanal['Minutos Planificados'] = df_melted_semanal['Turno'].apply(lambda x: turnos_dict.get(x, {}).get('working_minutes', 0))
                df_melted_semanal['Semana'] = 'Semana ' + df_melted_semanal['Fecha'].dt.isocalendar().week.astype(str)
                pivot_resumen = df_melted_semanal.pivot_table(index=['rut', 'Trabajador'], columns='Semana', values='Minutos Planificados', aggfunc='sum').fillna(0)
                pivot_formateado = pivot_resumen.applymap(minutes_to_time)
                pivot_formateado['Total Mes'] = pivot_resumen.sum(axis=1).apply(minutes_to_time)
                total_row = pivot_resumen.sum(axis=0).apply(minutes_to_time)
                total_row['Total Mes'] = minutes_to_time(pivot_resumen.sum().sum())
                total_row.name = ('TOTAL', '')
                pivot_final = pd.concat([pivot_formateado, total_row.to_frame().T])
                st.write("#### Horas Planificadas por Semana")
                st.dataframe(pivot_final, use_container_width=True)
            
            st.markdown("---")
            st.header("5. 📊 Resumen Ejecutivo")
            stats = calcular_estadisticas_avanzadas(df_editada, turnos_dict, dates, df_personal)
            if stats:
                mostrar_metricas_principales(stats)
            
            st.markdown("---")
            st.header("6. 📈 Análisis Visual")
            if stats:
                fig1, fig2 = crear_graficos_estadisticas(stats)
                col_graf1, col_graf2 = st.columns(2)
                with col_graf1:
                    if fig1: st.plotly_chart(fig1, use_container_width=True)
                with col_graf2:
                    if fig2: st.plotly_chart(fig2, use_container_width=True)
                
                mostrar_horas_por_trabajador_cards(stats)

            st.markdown("---")
            
            mostrar_alertas_inteligentes(stats)

            st.markdown("---")
            
            st.header("9. 📤 Exportar y Guardar")
            col_export1, col_export2, col_save = st.columns([1, 1, 1,])
            with col_export1:
                excel_data = create_excel_report(df_editada, sucursal, year, month)
                st.download_button(label="📥 Planilla (Excel)", data=excel_data, file_name=f"planificacion_{sucursal}_{month_name}_{year}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            with col_export2:
                zip_bytes = generar_zip_con_pdfs(df_editada, turnos_dict, sucursal, month_name, year, dates)
                st.download_button(label="📄 PDFs Individuales", data=zip_bytes, file_name=f"PDFs_Planificacion_{sucursal}_{month_name}_{year}.zip", mime="application/zip")
            with col_save:
                if st.button("💾 Guardar en BD", type="primary", key="save_final"):
                    with st.spinner("Preparando y guardando planificación..."):
                        # --- LÍNEA CORREGIDA ---
                        df_to_save = df_editada.melt(
                            id_vars=['rut', 'Trabajador'], # Incluir 'Trabajador' aquí
                            var_name='fecha',
                            value_name='codigo'
                        )
                        df_to_save = df_to_save[df_to_save['codigo'].notna() & (df_to_save['codigo'] != "")].copy()
                        
                        if df_to_save.empty:
                            st.warning("No se ingresó ningún turno para guardar.")
                        else:
                            df_to_save['fecha'] = pd.to_datetime(df_to_save['fecha'], format='%d-%m-%Y').dt.strftime('%Y-%m-%d')
                            
                            payload = {
                                "year": year,
                                "month": month,
                                "ruts": df_editada['rut'].tolist(),
                                "data": df_to_save[['rut', 'fecha', 'codigo']].to_dict('records') # Enviar solo las columnas necesarias
                            }

                            result = save_malla_to_endpoint(payload)
                            
                            if result.get("success", False):
                                st.success(result.get("message", "¡Planificación guardada con éxito en la base de datos!"))
                            else:
                                st.error(f"Error al guardar: {result.get('message', 'Ocurrió un error desconocido.')}")