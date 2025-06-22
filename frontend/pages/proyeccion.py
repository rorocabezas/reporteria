# -*- coding: utf-8 -*-
# pages/proyeccion.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
from menu import generarMenu # Asumo que tienes este archivo
import warnings

warnings.filterwarnings('ignore')

# --- CONFIGURACIÓN DE PÁGINA Y ESTILOS ---
st.set_page_config(
    page_title="Proyección de Ventas",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🔮"
)

st.markdown("""
<style>
    /* ... (Copia y pega aquí exactamente el mismo bloque CSS de tu archivo ventas.py) ... */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    .metric-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
        font-weight: 700;
    }
    /* ... y el resto de tus estilos ... */
</style>
""", unsafe_allow_html=True)

# Generar el menú lateral
generarMenu()

# --- CARGA Y PROCESAMIENTO DE DATOS ---
@st.cache_data(ttl=600, show_spinner="🔄 Cargando datos históricos...")
def load_historical_data():
    """
    Carga los datos históricos de ventas desde el endpoint de FastAPI.
    """
    try:
        # Usamos el endpoint que creamos para obtener todos los datos necesarios
        response = requests.get("http://localhost:8000/ventas_historicas_diarias", timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if 'data' not in data or 'columns' not in data:
            st.error("❌ Formato de datos incorrecto en el endpoint.")
            return pd.DataFrame()

        df = pd.DataFrame(data['data'], columns=data['columns'])
        
        # --- Limpieza y pre-procesamiento fundamental ---
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['total_venta'] = pd.to_numeric(df['total_venta'], errors='coerce')
        df.dropna(inplace=True)
        
        return df

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error de conexión al cargar datos históricos: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error inesperado al procesar datos históricos: {e}")
        return pd.DataFrame()

def create_features(df):
    """
    Crea características de ingeniería de tiempo (features) a partir de la columna de fecha.
    Estas características son las que el modelo usará para "entender" la estacionalidad.
    """
    df['año'] = df['fecha'].dt.year
    df['mes'] = df['fecha'].dt.month
    df['dia_del_mes'] = df['fecha'].dt.day
    df['dia_de_la_semana'] = df['fecha'].dt.dayofweek  # Lunes=0, Domingo=6
    df['dia_del_año'] = df['fecha'].dt.dayofyear
    df['semana_del_año'] = df['fecha'].dt.isocalendar().week.astype(int)
    # Variable para capturar el tiempo de forma continua (tendencia general)
    df['tiempo'] = (df['fecha'] - df['fecha'].min()).dt.days
    
    return df

@st.cache_data(ttl=3600, show_spinner="⚙️ Entrenando modelos de proyección...")
def train_projection_models(df, branches_to_train):
    """
    Entrena un modelo de regresión lineal para cada sucursal seleccionada.
    Retorna un diccionario de modelos entrenados.
    """
    models = {}
    for branch in branches_to_train:
        # 1. Filtrar datos para la sucursal actual
        branch_df = df[df['branch_office'] == branch].copy()
        
        # Si no hay suficientes datos, no se puede entrenar un modelo
        if len(branch_df) < 30: # Un umbral mínimo de datos para entrenar
            st.warning(f"⚠️ Datos insuficientes para entrenar un modelo para la sucursal '{branch}'. Se omitirá.")
            continue

        # 2. Crear características (features) para el modelo
        branch_df = create_features(branch_df)
        
        # 3. Definir variables (X) y objetivo (y)
        # Usamos las características de tiempo para predecir la venta
        features = ['tiempo', 'mes', 'dia_de_la_semana', 'dia_del_año', 'semana_del_año']
        X = branch_df[features]
        y = branch_df['total_venta']
        
        # 4. Entrenar el modelo
        model = LinearRegression()
        model.fit(X, y)
        
        # 5. Guardar el modelo entrenado
        models[branch] = model
        
    return models

def generate_projections(models, df_historical, projection_days):
    """
    Usa los modelos entrenados para generar proyecciones de ventas futuras.
    """
    if not models:
        return pd.DataFrame()

    last_date = df_historical['fecha'].max()
    future_dates = pd.to_datetime([last_date + timedelta(days=i) for i in range(1, projection_days + 1)])
    
    df_projection = pd.DataFrame()

    for branch, model in models.items():
        # Crear un DataFrame futuro para esta sucursal
        df_future_branch = pd.DataFrame({'fecha': future_dates})
        df_future_branch['branch_office'] = branch
        
        # Crear las mismas características que usamos para entrenar
        df_future_branch = create_features(df_future_branch)

        # Ajustar la característica 'tiempo' para que sea continua con los datos históricos
        min_historical_date = df_historical['fecha'].min()
        df_future_branch['tiempo'] = (df_future_branch['fecha'] - min_historical_date).dt.days

        # Predecir
        features = ['tiempo', 'mes', 'dia_de_la_semana', 'dia_del_año', 'semana_del_año']
        X_future = df_future_branch[features]
        
        predicted_sales = model.predict(X_future)
        
        # Asegurarnos de que las ventas proyectadas no sean negativas
        df_future_branch['proyeccion_venta'] = np.maximum(0, predicted_sales)
        
        df_projection = pd.concat([df_projection, df_future_branch], ignore_index=True)
        
    return df_projection


# --- INTERFAZ DE USUARIO (Streamlit) ---

# Header
st.markdown("<div class='main-header'><h1>🔮 Módulo de Proyección de Ventas</h1></div>", unsafe_allow_html=True)

# Cargar los datos
df_sales = load_historical_data()

if df_sales.empty:
    st.error("No se pudieron cargar los datos para la proyección. Verifica la conexión con la API o la base de datos.")
    st.stop()

# Sidebar con filtros
with st.sidebar:
    st.markdown("### 🎛️ Parámetros de Proyección")
    
    all_branches = sorted(df_sales['branch_office'].unique())
    selected_branches = st.multiselect(
        "🏢 Seleccionar Sucursales para Proyectar",
        options=all_branches,
        default=all_branches[:3] # Por defecto, selecciona las primeras 3 para no sobrecargar
    )
    
    projection_days = st.slider(
        "🗓️ Días a Proyectar",
        min_value=7,
        max_value=90,
        value=30,
        step=7,
        help="Selecciona el horizonte de tiempo para la proyección."
    )

if not selected_branches:
    st.warning("Por favor, selecciona al menos una sucursal para generar la proyección.")
    st.stop()

# Entrenar modelos y generar proyecciones
trained_models = train_projection_models(df_sales, selected_branches)
df_projection = generate_projections(trained_models, df_sales, projection_days)

# Resumen de Métricas
if not df_projection.empty:
    total_projected_sales = df_projection['proyeccion_venta'].sum()
    avg_daily_projection = df_projection['proyeccion_venta'].mean()
    
    st.markdown("### 📈 Resumen de la Proyección")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h3>💰 Ventas Totales Proyectadas</h3>
            <h2>${total_projected_sales:,.0f}</h2>
            <p>Para los próximos {projection_days} días</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);'>
            <h3>📊 Promedio Diario Proyectado</h3>
            <h2>${avg_daily_projection:,.0f}</h2>
            <p>Para las sucursales seleccionadas</p>
        </div>
        """, unsafe_allow_html=True)
else:
    st.error("No se pudo generar la proyección. Revisa las advertencias anteriores.")
    st.stop()


# Tabs para visualización
tab1, tab2, tab3 = st.tabs(["📈 Proyección General", "🏢 Detalle por Sucursal", "📋 Datos Proyectados"])

with tab1:
    st.markdown("### Proyección General de Ventas (Sucursales Seleccionadas)")
    
    fig = go.Figure()
    
    # Datos históricos
    df_hist_filtered = df_sales[df_sales['branch_office'].isin(selected_branches)]
    # Agrupamos los datos históricos por día para tener una sola línea
    df_hist_agg = df_hist_filtered.groupby('fecha')['total_venta'].sum().reset_index()

    fig.add_trace(go.Scatter(
        x=df_hist_agg['fecha'],
        y=df_hist_agg['total_venta'],
        mode='lines',
        name='Ventas Históricas (Agregado)',
        line=dict(color='royalblue', width=2)
    ))
    
    # Datos proyectados
    df_proj_agg = df_projection.groupby('fecha')['proyeccion_venta'].sum().reset_index()

    fig.add_trace(go.Scatter(
        x=df_proj_agg['fecha'],
        y=df_proj_agg['proyeccion_venta'],
        mode='lines',
        name='Ventas Proyectadas (Agregado)',
        line=dict(color='firebrick', dash='dash')
    ))

    fig.update_layout(
        title=f'Histórico vs. Proyección de Ventas para los Próximos {projection_days} Días',
        xaxis_title='Fecha',
        yaxis_title='Ventas Totales ($)',
        hovermode='x unified',
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.markdown("### Desglose de la Proyección por Sucursal")
    
    for branch in selected_branches:
        if branch not in trained_models:
            continue
            
        st.markdown(f"#### 🏢 Proyección para: **{branch}**")
        
        fig_branch = go.Figure()
        
        # Histórico de la sucursal
        df_hist_branch = df_sales[df_sales['branch_office'] == branch]
        fig_branch.add_trace(go.Scatter(
            x=df_hist_branch['fecha'],
            y=df_hist_branch['total_venta'],
            mode='lines',
            name='Histórico',
            line=dict(color='skyblue')
        ))
        
        # Proyección de la sucursal
        df_proj_branch = df_projection[df_projection['branch_office'] == branch]
        fig_branch.add_trace(go.Scatter(
            x=df_proj_branch['fecha'],
            y=df_proj_branch['proyeccion_venta'],
            mode='lines',
            name='Proyección',
            line=dict(color='orangered', dash='dot')
        ))
        
        fig_branch.update_layout(
            title=f'Proyección para {branch}',
            xaxis_title='Fecha',
            yaxis_title='Ventas ($)',
            height=400,
            showlegend=True
        )
        st.plotly_chart(fig_branch, use_container_width=True)

with tab3:
    st.markdown("### Datos Detallados de la Proyección")
    st.info("Puedes ordenar la tabla haciendo clic en los encabezados de las columnas.")
    
    # Formatear la tabla para una mejor visualización
    df_display = df_projection[['fecha', 'branch_office', 'proyeccion_venta']].copy()
    df_display['fecha'] = df_display['fecha'].dt.strftime('%Y-%m-%d')
    df_display['proyeccion_venta'] = df_display['proyeccion_venta'].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(df_display, use_container_width=True, height=500)