# pages/venta_hora.py
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
from scipy.signal import find_peaks
import seaborn as sns
from menu import generarMenu
from utils import format_currency, format_percentage
import warnings
import base64
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import plotly.figure_factory as ff

warnings.filterwarnings('ignore')

# Configuración de página
st.set_page_config(
    page_title="Dashboard Venta x Hora",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🏦"
)

# CSS personalizado para mejorar la UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .alert-box {
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .alert-success { background-color: #d4edda; border-left: 4px solid #28a745; }
    .alert-warning { background-color: #fff3cd; border-left: 4px solid #ffc107; }
    .alert-danger { background-color: #f8d7da; border-left: 4px solid #dc3545; }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Generar el menú
generarMenu()

# ================ FUNCIONES DE OBTENCIÓN DE DATOS MEJORADAS ================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_from_endpoint(endpoint):
    """Función mejorada para obtener datos de endpoints con manejo de errores"""
    try:
        with st.spinner(f'Cargando datos de {endpoint}...'):
            response = requests.get(f"http://localhost:8000/{endpoint}", timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'data' not in data or 'columns' not in data:
                st.error(f"Formato de datos incorrecto en {endpoint}")
                return pd.DataFrame()

            df = pd.DataFrame(data['data'], columns=data['columns'])
            return df

    except requests.exceptions.Timeout:
        st.error(f"⏱️ Timeout al conectar con {endpoint}")
        return pd.DataFrame()
    except requests.exceptions.ConnectionError:
        st.error(f"🔌 Error de conexión con {endpoint}")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error HTTP en {endpoint}: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"💥 Error inesperado en {endpoint}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def load_and_process_data():
    """Carga y procesa todos los datos necesarios"""
    # Cargar datos
    df_venta_hora = fetch_data_from_endpoint("venta_hora")
    df_sucursales = fetch_data_from_endpoint("sucursales")
    df_periodos = fetch_data_from_endpoint("periodos_date")

    if df_venta_hora.empty:
        return pd.DataFrame(), {}

    # Procesar datos
    dte_final = df_venta_hora.merge(df_sucursales, on=['branch_office_id'], how='left')

    # Merge con sucursales
    if not df_sucursales.empty:
        dte_final = dte_final.merge(
            df_sucursales[['branch_office_id', 'responsable', 'branch_office']],
            on='branch_office_id', how='left'
        )

    # Procesar fechas y horas
    dte_final['hora_inicio'] = pd.to_datetime(dte_final['hora_inicio'], format='%H:%M:%S').dt.time
    dte_final['hora_fin'] = pd.to_datetime(dte_final['hora_fin'], format='%H:%M:%S').dt.time
    dte_final['fecha'] = pd.to_datetime(dte_final['fecha'])
    dte_final['duracion'] = pd.to_timedelta(dte_final['duracion']).dt.total_seconds() / 60  # Convertir a minutos

    return dte_final, {}

# ================ ANÁLISIS ESTADÍSTICOS AVANZADOS ================
def advanced_statistical_analysis(df):
    """Análisis estadístico completo y avanzado"""
    if df.empty:
        return {}

    analysis = {}

    # 1. Estadísticas descriptivas avanzadas
    numeric_cols = ['monto', 'duracion']
    for col in numeric_cols:
        if col in df.columns:
            data = df[col].dropna()
            analysis[f'{col}_stats'] = {
                'media': data.mean(),
                'mediana': data.median(),
                'moda': data.mode().iloc[0] if not data.mode().empty else np.nan,
                'desviacion_std': data.std(),
                'varianza': data.var(),
                'coef_variacion': (data.std() / data.mean() * 100) if data.mean() > 0 else 0,
                'asimetria': stats.skew(data),
                'curtosis': stats.kurtosis(data),
                'rango': data.max() - data.min(),
                'iqr': data.quantile(0.75) - data.quantile(0.25),
                'percentiles': {
                    'p5': data.quantile(0.05),
                    'p25': data.quantile(0.25),
                    'p75': data.quantile(0.75),
                    'p95': data.quantile(0.95)
                }
            }

    return analysis

def detect_anomalies_advanced(df):
    """Detección avanzada de anomalías usando múltiples métodos"""
    if df.empty:
        return df, {}

    df_result = df.copy()
    anomaly_info = {}

    # Características para análisis
    features = ['monto', 'duracion']
    available_features = [col for col in features if col in df.columns]

    if not available_features:
        return df_result, anomaly_info

    # 1. Isolation Forest
    if len(df) > 10:
        scaler = StandardScaler()
        X = scaler.fit_transform(df[available_features].fillna(0))

        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        df_result['anomaly_isolation'] = iso_forest.fit_predict(X) == -1

        anomaly_info['isolation_forest'] = {
            'total_anomalies': df_result['anomaly_isolation'].sum(),
            'percentage': (df_result['anomaly_isolation'].sum() / len(df_result)) * 100
        }

    return df_result, anomaly_info

def clustering_analysis(df):
    """Análisis de clustering para segmentación"""
    if df.empty:
        return df, {}

    # Características para clustering
    features = ['monto', 'duracion']
    available_features = [col for col in features if col in df.columns]

    if len(available_features) < 2 or len(df) < 10:
        return df, {}

    # Preparar datos
    X = df[available_features].fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Determinar número óptimo de clusters usando método del codo
    max_clusters = min(10, len(df) // 2)
    inertias = []
    K_range = range(2, max_clusters + 1)

    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X_scaled)
        inertias.append(kmeans.inertia_)

    # Aplicar K-means con número óptimo (usando método simple)
    optimal_k = 3 if len(K_range) >= 2 else 2
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    df['cluster'] = kmeans.fit_predict(X_scaled)

    # Análisis de clusters
    cluster_analysis = {}
    for cluster_id in range(optimal_k):
        cluster_data = df[df['cluster'] == cluster_id]
        cluster_analysis[f'cluster_{cluster_id}'] = {
            'size': len(cluster_data),
            'percentage': (len(cluster_data) / len(df)) * 100,
            'characteristics': {
                col: {
                    'mean': cluster_data[col].mean(),
                    'std': cluster_data[col].std()
                } for col in available_features
            }
        }

    return df, {'clusters': cluster_analysis, 'optimal_k': optimal_k, 'inertias': inertias}

# ================ VISUALIZACIONES AVANZADAS ================
def create_advanced_dashboard():
    """Crea dashboard principal con múltiples pestañas"""

    # Cargar datos
    df, _ = load_and_process_data()

    if df.empty:
        st.error("❌ No se pudieron cargar los datos")
        return

    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>🏦 Dashboard de Ventas por Hora</h1>
        <p>Análisis estadístico completo con machine learning y detección de anomalías</p>
    </div>
    """, unsafe_allow_html=True)

    # Crear pestañas
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Resumen Ejecutivo",
        "📈 Análisis Temporal",
        "🔍 Detección Anomalías",
        "📊 Análisis Estadístico",
        "🎯 Segmentación"
    ])

    # Aplicar filtros (sidebar)
    df_filtered = apply_filters(df)

    with tab1:
        create_executive_summary(df_filtered)

    with tab2:
        create_temporal_analysis(df_filtered)

    with tab3:
        create_anomaly_detection_tab(df_filtered)

    with tab4:
        create_statistical_analysis_tab(df_filtered)

    with tab5:
        create_clustering_tab(df_filtered)

def apply_filters(df):
    """Aplica filtros desde sidebar"""
    st.sidebar.header("🔍 Filtros de Análisis")

    # Filtro por sucursal
    sucursales_disponibles = ['Todas'] + list(df['branch_office'].dropna().unique())
    sucursal_seleccionada = st.sidebar.selectbox("Sucursal:", sucursales_disponibles)

    # Filtro por rango de fechas
    fecha_min = df['fecha'].min().date()
    fecha_max = df['fecha'].max().date()

    fecha_range = st.sidebar.date_input(
        "Rango de fechas:",
        value=[fecha_min, fecha_max],
        min_value=fecha_min,
        max_value=fecha_max
    )

    # Filtro por monto mínimo
    min_amount = st.sidebar.number_input(
        "Monto mínimo:",
        min_value=0,
        value=0,
        step=1000
    )

    # Aplicar filtros
    df_filtered = df.copy()

    if sucursal_seleccionada != 'Todas':
        df_filtered = df_filtered[df_filtered['branch_office'] == sucursal_seleccionada]

    if len(fecha_range) == 2:
        df_filtered = df_filtered[
            (df_filtered['fecha'].dt.date >= fecha_range[0]) &
            (df_filtered['fecha'].dt.date <= fecha_range[1])
        ]

    if min_amount > 0:
        df_filtered = df_filtered[df_filtered['monto'] >= min_amount]

    return df_filtered

def create_executive_summary(df):
    """Pestaña de resumen ejecutivo"""
    if df.empty:
        st.warning("No hay datos para mostrar")
        return

    # KPIs principales
    col1, col2, col3, col4 = st.columns(4)

    total_ventas = df['monto'].sum()
    total_duracion = df['duracion'].sum()
    promedio_duracion = df['duracion'].mean()
    ventas_por_hora = df.groupby(df['hora_inicio'].astype(str))['monto'].sum().idxmax()

    with col1:
        st.metric("💰 Total Ventas", format_currency(total_ventas))
    with col2:
        st.metric("⏱️ Total Duración", f"{total_duracion:.1f} minutos")
    with col3:
        st.metric("⏱️ Promedio Duración", f"{promedio_duracion:.1f} minutos")
    with col4:
        st.metric("🕒 Hora con más ventas", ventas_por_hora)

    st.markdown("---")

    # Gráficos principales
    col1, col2 = st.columns(2)

    with col1:
        # Distribución de ventas por hora
        fig_pie = px.pie(
            df.groupby(df['hora_inicio'].astype(str))['monto'].sum().reset_index(),
            values='monto',
            names='hora_inicio',
            title='Distribución de Ventas por Hora'
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Evolución temporal
        daily_data = df.groupby('fecha').agg({
            'monto': 'sum',
            'duracion': 'sum'
        }).reset_index()

        fig_evolution = go.Figure()
        fig_evolution.add_trace(go.Scatter(
            x=daily_data['fecha'],
            y=daily_data['monto'],
            mode='lines',
            name='Monto',
            line=dict(color='blue', width=3)
        ))
        fig_evolution.add_trace(go.Scatter(
            x=daily_data['fecha'],
            y=daily_data['duracion'],
            mode='lines',
            name='Duración',
            line=dict(color='red', width=3)
        ))
        fig_evolution.update_layout(title='Evolución Temporal')
        st.plotly_chart(fig_evolution, use_container_width=True)

def create_temporal_analysis(df):
    """Análisis temporal avanzado"""
    if df.empty:
        st.warning("No hay datos para análisis temporal")
        return

    st.subheader("📈 Análisis Temporal Avanzado")

    # Análisis de tendencias
    daily_data = df.groupby('fecha').agg({
        'monto': 'sum',
        'duracion': 'sum'
    }).reset_index()

    # Gráfico principal con tendencias
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=['Ventas por Fecha', 'Duración por Fecha'],
        vertical_spacing=0.08,
        row_heights=[0.5, 0.5]
    )

    # Gráfico 1: Ventas por fecha
    fig.add_trace(go.Scatter(
        x=daily_data['fecha'],
        y=daily_data['monto'],
        mode='lines',
        name='Monto',
        line=dict(color='blue', width=2)
    ), row=1, col=1)

    # Gráfico 2: Duración por fecha
    fig.add_trace(go.Scatter(
        x=daily_data['fecha'],
        y=daily_data['duracion'],
        mode='lines',
        name='Duración',
        line=dict(color='red', width=2)
    ), row=2, col=1)

    fig.update_layout(height=600, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

def create_anomaly_detection_tab(df):
    """Pestaña de detección de anomalías"""
    if df.empty:
        st.warning("No hay datos para detección de anomalías")
        return

    st.subheader("🔍 Detección de Anomalías")

    # Aplicar detección de anomalías
    df_with_anomalies, anomaly_info = detect_anomalies_advanced(df)

    # Mostrar información de anomalías
    st.write("### Información de Anomalías")
    st.json(anomaly_info)

    # Visualización de anomalías
    col1, col2 = st.columns(2)

    with col1:
        # Anomalías por Isolation Forest
        fig_iso = px.scatter(
            df_with_anomalies,
            x='fecha',
            y='monto',
            color='anomaly_isolation',
            title='Anomalías detectadas por Isolation Forest'
        )
        st.plotly_chart(fig_iso, use_container_width=True)

def create_statistical_analysis_tab(df):
    """Pestaña de análisis estadístico"""
    if df.empty:
        st.warning("No hay datos para análisis estadístico")
        return

    st.subheader("📊 Análisis Estadístico Avanzado")

    # Realizar análisis estadístico
    analysis = advanced_statistical_analysis(df)

    # Mostrar resultados
    st.write("### Estadísticas Descriptivas")
    for col in ['monto', 'duracion']:
        if f'{col}_stats' in analysis:
            st.json(analysis[f'{col}_stats'])

def create_clustering_tab(df):
    """Pestaña de análisis de clustering"""
    if df.empty:
        st.warning("No hay datos para análisis de clustering")
        return

    st.subheader("🎯 Análisis de Segmentación por Clustering")

    # Realizar análisis de clustering
    df_with_clusters, cluster_info = clustering_analysis(df)

    # Mostrar información de clusters
    st.write("### Información de Clusters")
    st.json(cluster_info)

    # Visualización de clusters
    fig_cluster = px.scatter(
        df_with_clusters,
        x='monto',
        y='duracion',
        color='cluster',
        title='Segmentación por Clustering'
    )
    st.plotly_chart(fig_cluster, use_container_width=True)

# Punto de entrada de la aplicación
if __name__ == "__main__":
    create_advanced_dashboard()

