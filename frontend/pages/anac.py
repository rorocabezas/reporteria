import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from menu import generarMenu
import streamlit.components.v1 as components
import numpy as np
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(page_title="Dashboard ANAC", layout="wide")

# Función para verificar el estado de login
def check_login():
    if 'logged_in' in st.session_state and st.session_state.logged_in:
        return True
    return False

# Verificar si el usuario está logueado
if not check_login():
    st.error("Debes iniciar sesión para acceder a esta página.")
    st.stop()

# Generar el menú
generarMenu()

# Importar el archivo CSS
try:
    with open("styles.css") as f:
        css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
except:
    pass

# Link CSS de Font Awesome
font_awesome = """<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css" />"""
st.markdown(font_awesome, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_anac_data():
    try:
        url = "http://localhost:8000/anac"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error("Error al obtener datos de ANAC")
            return None
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# Funciones auxiliares
def format_number(value):
    """Formatear números con separadores de miles"""
    return f"{value:,.0f}"

def format_percentage(value):
    """Formatear como porcentaje"""
    return f"{value:.1f}%"

def calculate_growth_rate(current, previous):
    """Calcular tasa de crecimiento"""
    if previous == 0:
        return 0
    return ((current - previous) / previous) * 100

def get_trend_icon(value):
    """Obtener icono de tendencia"""
    if value > 0:
        return "📈"
    elif value < 0:
        return "📉"
    else:
        return "➡️"

# Obtener datos de ANAC
with st.spinner('Cargando datos de ANAC...'):
    anac_data = get_anac_data()

if anac_data is None:
    st.stop()

# Crear DataFrame
columns_anac = anac_data["columns"]
data_anac = anac_data["data"]
df_anac = pd.DataFrame(data_anac, columns=columns_anac)

# Procesar datos
categorias = ["pasajeros", "suv", "camioneta", "comercial"]

# Procesar la columna periodo de forma más robusta
if 'periodo' in df_anac.columns:
    # Extraer año y mes directamente del string periodo (formato: "2024-01")
    df_anac['año'] = df_anac['periodo'].str[:4].astype(int)
    df_anac['mes'] = df_anac['periodo'].str[5:].astype(int)
    # Crear fecha para ordenamiento
    df_anac['periodo_date'] = pd.to_datetime(df_anac['periodo'] + '-01')
else:
    # Si no existe periodo, crear columnas por defecto
    df_anac['año'] = 2024
    df_anac['mes'] = 1
    df_anac['periodo'] = '2024-01'
    df_anac['periodo_date'] = pd.to_datetime('2024-01-01')

# Verificar que las columnas de categorías existen
categorias_existentes = [cat for cat in categorias if cat in df_anac.columns]
if not categorias_existentes:
    st.error("No se encontraron las columnas de categorías esperadas en los datos")
    st.write("Columnas disponibles:", df_anac.columns.tolist())
    st.stop()

# Calcular total de vehículos
df_anac['total_vehiculos'] = df_anac[categorias_existentes].sum(axis=1)

# Ordenar por período
df_anac = df_anac.sort_values('periodo_date')

# Header del dashboard
st.markdown("""
<div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); border-radius: 10px; margin-bottom: 20px;'>
    <h1 style='color: white; margin: 0;'>🚗 Dashboard ANAC - Indicadores Automotrices</h1>
    
</div>
""", unsafe_allow_html=True)

# SIDEBAR - FILTROS Y CONTROLES
st.sidebar.markdown("## 🔧 Filtros Disponible")

# Filtros de período
años_disponibles = sorted(df_anac['año'].unique(), reverse=True)
año_actual = max(años_disponibles)

col_año1, col_año2 = st.sidebar.columns(2)
with col_año1:
    año_comparacion_1 = st.selectbox("Año Base:", años_disponibles, index=1 if len(años_disponibles) > 1 else 0)
with col_año2:
    año_comparacion_2 = st.selectbox("Año Comparar:", años_disponibles, index=0)

# Selector de período de análisis
periodo_analisis = st.sidebar.selectbox(
    "Período de Análisis:",
    ["Último Mes", "Trimestre Actual", "Año Completo", "Personalizado"]
)

if periodo_analisis == "Personalizado":
    periodos_disponibles = sorted(df_anac['periodo'].unique())
    periodo_inicio = st.sidebar.selectbox("Desde:", periodos_disponibles)
    periodo_fin = st.sidebar.selectbox("Hasta:", periodos_disponibles, index=len(periodos_disponibles)-1)

# Configuraciones de visualización
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Opciones de Visualización")
mostrar_tendencias = st.sidebar.checkbox("Mostrar líneas de tendencia", True)
mostrar_predicciones = st.sidebar.checkbox("Mostrar predicciones", False)
tipo_grafico = st.sidebar.selectbox("Tipo de gráfico principal:", ["Barras", "Líneas", "Área"])

# MÉTRICAS PRINCIPALES
st.markdown("## 📊 Resumen Ejecutivo")

# Obtener datos del último período disponible y penúltimo
periodos_ordenados = sorted(df_anac['periodo'].unique())
ultimo_periodo = periodos_ordenados[-1]
penultimo_periodo = periodos_ordenados[-2] if len(periodos_ordenados) > 1 else ultimo_periodo

datos_actual = df_anac[df_anac['periodo'] == ultimo_periodo].iloc[0]
datos_anterior = df_anac[df_anac['periodo'] == penultimo_periodo].iloc[0] if penultimo_periodo != ultimo_periodo else datos_actual

# Mostrar métricas principales
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_actual = datos_actual['total_vehiculos']
    total_anterior = datos_anterior['total_vehiculos']
    crecimiento_total = calculate_growth_rate(total_actual, total_anterior)
    
    st.metric(
        label="🚗 Total Vehículos",
        value=format_number(total_actual),
        delta=f"{crecimiento_total:+.1f}%"
    )

with col2:
    if 'pasajeros' in categorias_existentes:
        pasajeros_actual = datos_actual['pasajeros']
        pasajeros_anterior = datos_anterior['pasajeros']
        crecimiento_pasajeros = calculate_growth_rate(pasajeros_actual, pasajeros_anterior)
        
        st.metric(
            label="🚙 Pasajeros",
            value=format_number(pasajeros_actual),
            delta=f"{crecimiento_pasajeros:+.1f}%"
        )

with col3:
    if 'suv' in categorias_existentes:
        suv_actual = datos_actual['suv']
        suv_anterior = datos_anterior['suv']
        crecimiento_suv = calculate_growth_rate(suv_actual, suv_anterior)
        
        st.metric(
            label="🚐 SUV",
            value=format_number(suv_actual),
            delta=f"{crecimiento_suv:+.1f}%"
        )

with col4:
    if 'camioneta' in categorias_existentes:
        camioneta_actual = datos_actual['camioneta']
        camioneta_anterior = datos_anterior['camioneta']
        crecimiento_camioneta = calculate_growth_rate(camioneta_actual, camioneta_anterior)
        
        st.metric(
            label="🛻 Camionetas",
            value=format_number(camioneta_actual),
            delta=f"{crecimiento_camioneta:+.1f}%"
        )

with col5:
    if 'comercial' in categorias_existentes:
        comercial_actual = datos_actual['comercial']
        comercial_anterior = datos_anterior['comercial']
        crecimiento_comercial = calculate_growth_rate(comercial_actual, comercial_anterior)
        
        st.metric(
            label="🚚 Comerciales",
            value=format_number(comercial_actual),
            delta=f"{crecimiento_comercial:+.1f}%"
        )

st.markdown("---")

# ANÁLISIS COMPARATIVO
st.markdown("## 📈 Análisis Comparativo Detallado")

# Preparar datos para comparación basados en el período seleccionado
if periodo_analisis == "Último Mes":
    # Tomar el último mes disponible de cada año
    ultimo_mes_año1 = df_anac[df_anac['año'] == año_comparacion_1]['mes'].max()
    ultimo_mes_año2 = df_anac[df_anac['año'] == año_comparacion_2]['mes'].max()
    
    df_comp_1 = df_anac[(df_anac['año'] == año_comparacion_1) & (df_anac['mes'] == ultimo_mes_año1)]
    df_comp_2 = df_anac[(df_anac['año'] == año_comparacion_2) & (df_anac['mes'] == ultimo_mes_año2)]
    titulo_comp = f"Comparativo Último Mes {año_comparacion_1} vs {año_comparacion_2}"
elif periodo_analisis == "Trimestre Actual":
    df_comp_1 = df_anac[(df_anac['año'] == año_comparacion_1) & (df_anac['mes'] <= 3)]
    df_comp_2 = df_anac[(df_anac['año'] == año_comparacion_2) & (df_anac['mes'] <= 3)]
    titulo_comp = f"Comparativo Primer Trimestre {año_comparacion_1} vs {año_comparacion_2}"
else:
    df_comp_1 = df_anac[df_anac['año'] == año_comparacion_1]
    df_comp_2 = df_anac[df_anac['año'] == año_comparacion_2]
    titulo_comp = f"Comparativo Anual {año_comparacion_1} vs {año_comparacion_2}"

# Calcular totales por categoría
comp_data = pd.DataFrame({
    "Categoría": [cat.capitalize() for cat in categorias_existentes],
    str(año_comparacion_1): [df_comp_1[cat].sum() for cat in categorias_existentes],
    str(año_comparacion_2): [df_comp_2[cat].sum() for cat in categorias_existentes]
})

# Calcular variaciones
comp_data['Variación'] = ((comp_data[str(año_comparacion_2)] / comp_data[str(año_comparacion_1)]) - 1) * 100
comp_data['Variación'] = comp_data['Variación'].fillna(0)  # Manejar divisiones por cero
comp_data['Variación_fmt'] = comp_data['Variación'].apply(format_percentage)

# Gráficos comparativos
col1, col2 = st.columns(2)

with col1:
    # Gráfico de barras mejorado
    fig_comp = go.Figure()
    
    fig_comp.add_trace(go.Bar(
        x=comp_data['Categoría'],
        y=comp_data[str(año_comparacion_1)],
        name=str(año_comparacion_1),
        marker_color='lightblue',
        text=[format_number(x) for x in comp_data[str(año_comparacion_1)]],
        textposition='outside'
    ))
    
    fig_comp.add_trace(go.Bar(
        x=comp_data['Categoría'],
        y=comp_data[str(año_comparacion_2)],
        name=str(año_comparacion_2),
        marker_color='darkblue',
        text=[format_number(x) for x in comp_data[str(año_comparacion_2)]],
        textposition='outside'
    ))
    
    # Línea de variación
    fig_comp.add_trace(go.Scatter(
        x=comp_data['Categoría'],
        y=comp_data['Variación'],
        yaxis='y2',
        name='Variación %',
        mode='lines+markers+text',
        text=comp_data['Variación_fmt'],
        textposition='top center',
        line=dict(color='red', width=3),
        marker=dict(size=12, color='white', line=dict(width=2, color='red'))
    ))
    
    fig_comp.update_layout(
        title=titulo_comp,
        xaxis_title='Categorías',
        yaxis_title='Unidades',
        yaxis2=dict(
            title='Variación %',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        barmode='group',
        legend=dict(orientation='h', yanchor='top', y=-0.15),
        height=500
    )
    
    st.plotly_chart(fig_comp, use_container_width=True)

with col2:
    # Gráfico de participación de mercado
    total_año_2 = comp_data[str(año_comparacion_2)].sum()
    
    if total_año_2 > 0:
        fig_pie = go.Figure(data=[go.Pie(
            labels=comp_data['Categoría'],
            values=comp_data[str(año_comparacion_2)],
            hole=.4,
            textinfo='label+percent',
            textposition='outside',
            marker=dict(colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'])
        )])
        
        fig_pie.update_layout(
            title=f"Participación de Mercado {año_comparacion_2}",
            showlegend=True,
            height=500,
            annotations=[dict(text=f'Total<br>{format_number(total_año_2)}', x=0.5, y=0.5, font_size=16, showarrow=False)]
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning("No hay datos para mostrar la participación de mercado")

# ANÁLISIS TEMPORAL
st.markdown("---")
st.markdown("## 📅 Evolución Temporal")

# Preparar datos temporales
df_temporal = df_anac.copy().sort_values('periodo_date')

# Crear gráfico de evolución temporal
if len(df_temporal) > 0 and len(categorias_existentes) > 0:
    # Crear subplots basado en categorías existentes
    filas = (len(categorias_existentes) + 1) // 2
    fig_temporal = make_subplots(
        rows=filas, cols=2,
        subplot_titles=[cat.capitalize() for cat in categorias_existentes],
        vertical_spacing=0.12
    )

    colores = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    for i, categoria in enumerate(categorias_existentes):
        row = (i // 2) + 1
        col = (i % 2) + 1
        color = colores[i % len(colores)]
        
        fig_temporal.add_trace(
            go.Scatter(
                x=df_temporal['periodo'],
                y=df_temporal[categoria],
                mode='lines+markers',
                name=categoria.capitalize(),
                line=dict(color=color, width=3),
                marker=dict(size=8),
                showlegend=False
            ),
            row=row, col=col
        )
        
        # Agregar línea de tendencia si está habilitada
        if mostrar_tendencias and len(df_temporal) > 1:
            try:
                z = np.polyfit(range(len(df_temporal)), df_temporal[categoria], 1)
                p = np.poly1d(z)
                fig_temporal.add_trace(
                    go.Scatter(
                        x=df_temporal['periodo'],
                        y=p(range(len(df_temporal))),
                        mode='lines',
                        name=f'Tendencia {categoria}',
                        line=dict(color=color, width=2, dash='dash'),
                        showlegend=False
                    ),
                    row=row, col=col
                )
            except:
                pass

    fig_temporal.update_layout(
        title="Evolución Temporal por Categoría",
        height=400 * filas,
        showlegend=False
    )

    st.plotly_chart(fig_temporal, use_container_width=True)
else:
    st.warning("No hay suficientes datos para mostrar la evolución temporal")

# TABLA DE ESTADÍSTICAS AVANZADAS
st.markdown("---")
st.markdown("## 📊 Estadísticas Avanzadas")

tab1, tab2, tab3, tab4 = st.tabs(["📈 Crecimiento", "📊 Estadísticas", "🎯 Rankings", "📋 Datos Detallados"])

with tab1:
    # Análisis de crecimiento
    st.subheader("Análisis de Crecimiento por Categoría")
    
    if len(categorias_existentes) > 0 and len(df_anac) > 1:
        crecimiento_data = []
        for categoria in categorias_existentes:
            try:
                datos_categoria = df_anac.sort_values('periodo_date')[['periodo', categoria]].copy()
                datos_categoria['crecimiento_mensual'] = datos_categoria[categoria].pct_change() * 100
                
                crecimiento_promedio = datos_categoria['crecimiento_mensual'].mean()
                volatilidad = datos_categoria['crecimiento_mensual'].std()
                ultimo_crecimiento = datos_categoria['crecimiento_mensual'].iloc[-1]
                
                crecimiento_data.append({
                    'Categoría': categoria.capitalize(),
                    'Crecimiento Promedio Mensual': f"{crecimiento_promedio:.2f}%" if not pd.isna(crecimiento_promedio) else "N/A",
                    'Volatilidad': f"{volatilidad:.2f}%" if not pd.isna(volatilidad) else "N/A",
                    'Último Crecimiento': f"{ultimo_crecimiento:.2f}%" if not pd.isna(ultimo_crecimiento) else "N/A"
                })
            except Exception as e:
                st.warning(f"Error calculando crecimiento para {categoria}: {str(e)}")
        
        if crecimiento_data:
            df_crecimiento = pd.DataFrame(crecimiento_data)
            st.dataframe(df_crecimiento, use_container_width=True)
        else:
            st.warning("No se pudieron calcular las estadísticas de crecimiento")
    else:
        st.warning("No hay suficientes datos para calcular el crecimiento")

with tab2:
    # Estadísticas descriptivas
    st.subheader("Estadísticas Descriptivas")
    
    if categorias_existentes:
        stats_data = df_anac[categorias_existentes].describe().round(2)
        stats_data.index = ['Conteo', 'Media', 'Desv. Estándar', 'Mínimo', '25%', '50%', '75%', 'Máximo']
        
        # Formatear números
        for col in stats_data.columns:
            stats_data[col] = stats_data[col].apply(lambda x: format_number(x) if not pd.isna(x) else 'N/A')
        
        st.dataframe(stats_data, use_container_width=True)
    else:
        st.warning("No hay datos de categorías disponibles para mostrar estadísticas")

with tab3:
    # Rankings y comparaciones
    st.subheader("Rankings por Período")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Top 5 Períodos - Total Vehículos**")
        top_periodos = df_anac.nlargest(5, 'total_vehiculos')[['periodo', 'total_vehiculos']]
        top_periodos['total_vehiculos'] = top_periodos['total_vehiculos'].apply(format_number)
        st.dataframe(top_periodos, use_container_width=True, hide_index=True)
    
    with col2:
        if categorias_existentes:
            st.write("**Participación Promedio por Categoría**")
            participacion_promedio = []
            total_promedio = df_anac['total_vehiculos'].mean()
            
            for categoria in categorias_existentes:
                if total_promedio > 0:
                    participacion = (df_anac[categoria].mean() / total_promedio) * 100
                    participacion_promedio.append({
                        'Categoría': categoria.capitalize(),
                        'Participación': f"{participacion:.1f}%"
                    })
            
            if participacion_promedio:
                df_participacion = pd.DataFrame(participacion_promedio)
                st.dataframe(df_participacion, use_container_width=True, hide_index=True)
            else:
                st.warning("No se pudo calcular la participación promedio")
        else:
            st.warning("No hay categorías disponibles para mostrar participación")

with tab4:
    # Datos detallados con filtros
    st.subheader("Datos Detallados")
    
    # Filtros para datos detallados
    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        años_filtro = st.multiselect("Filtrar por años:", años_disponibles, default=años_disponibles)
    with col_filtro2:
        categorias_mostrar = st.multiselect("Categorías a mostrar:", categorias_existentes, default=categorias_existentes)
    
    # Aplicar filtros
    df_filtrado = df_anac[df_anac['año'].isin(años_filtro)]
    
    # Seleccionar columnas a mostrar
    columnas_base = ['periodo', 'año', 'mes']
    columnas_disponibles = [col for col in columnas_base if col in df_filtrado.columns]
    categorias_disponibles = [cat for cat in categorias_mostrar if cat in df_filtrado.columns]
    
    columnas_mostrar = columnas_disponibles + categorias_disponibles
    if 'total_vehiculos' in df_filtrado.columns:
        columnas_mostrar.append('total_vehiculos')
    
    # Crear df_mostrar con las columnas seleccionadas
    df_mostrar = df_filtrado[columnas_mostrar].copy()
    
    # Ordenar por la columna de fecha si existe, sino por período
    if 'periodo_date' in df_filtrado.columns:
        df_mostrar = df_mostrar.sort_values('periodo', ascending=False)  # Usar período para ordenar la vista
    else:
        df_mostrar = df_mostrar.sort_values('periodo', ascending=False)
    
    # Formatear números para visualización
    df_display = df_mostrar.copy()
    for col in df_display.columns:
        if col in categorias_disponibles or col == 'total_vehiculos':
            if df_display[col].dtype in ['int64', 'float64']:
                df_display[col] = df_display[col].apply(format_number)
    
    st.dataframe(df_display, use_container_width=True, height=400)

# INFORMACIÓN ADICIONAL EN SIDEBAR
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Información del Dataset")
st.sidebar.info(f"""
**Resumen de Datos:**
- Períodos disponibles: {len(df_anac)}
- Rango temporal: {df_anac['periodo'].min()} - {df_anac['periodo'].max()}
- Total histórico: {format_number(df_anac['total_vehiculos'].sum())}
- Promedio mensual: {format_number(df_anac['total_vehiculos'].mean())}
""")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; padding: 20px;'>
    <small>Dashboard ANAC - Actualizado automáticamente | Datos proporcionados por API FastAPI</small>
</div>
""", unsafe_allow_html=True)