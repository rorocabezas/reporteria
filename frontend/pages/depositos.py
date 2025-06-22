# -*- coding: utf-8 -*-
# pages/depositos.py
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
    page_title="Dashboard Depósitos",
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
def fetch_data_from_endpoint(endpoint, sucursales=None, rut=None):
    """Función mejorada para obtener datos de endpoints con manejo de errores"""
    try:
        with st.spinner(f'Cargando datos de {endpoint}...'):
            if endpoint == "sucursales" and rut:
                # Si el endpoint es sucursales y tenemos un rut, usamos el endpoint sucursales_rut
                response = requests.get(f"http://localhost:8000/sucursales_rut", params={"rut": rut}, timeout=30)
            else:
                # Para otros endpoints, usamos la URL normal
                response = requests.get(f"http://localhost:8000/{endpoint}", timeout=30)

            response.raise_for_status()
            data = response.json()

            if 'data' not in data or 'columns' not in data:
                st.error(f"Formato de datos incorrecto en {endpoint}")
                return pd.DataFrame()

            df = pd.DataFrame(data['data'], columns=data['columns'])

            # Filtrar por sucursales si se proporcionan
            if sucursales is not None and not df.empty and 'branch_office_id' in df.columns:
                st.write(f"Filtrando sucursales: {sucursales}")  # Depuración
                df = df[df['branch_office_id'].isin(sucursales)]
                st.write(f"DataFrame después del filtrado: {df}")  # Depuración

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
    # Obtener las sucursales del usuario desde st.session_state
    rut = None
    sucursales = None
    if 'user_info' in st.session_state and 'rut' in st.session_state.user_info:
        rut = st.session_state.user_info['rut']
        st.write(f"RUT del usuario: {rut}")  # Depuración

    st.write(f"RUT del usuario: {rut}")

    # Cargar datos
    df_deposito = fetch_data_from_endpoint("depositos", sucursales)
    df_recaudacion = fetch_data_from_endpoint("recaudacion", sucursales)
    df_sucursales = fetch_data_from_endpoint("sucursales", sucursales, rut=rut)  # Pasar el rut al endpoint de sucursales

    st.write("DataFrame de sucursales después de filtrar:")
    st.write(df_sucursales)

    df_periodos = fetch_data_from_endpoint("periodos_date")

    if df_deposito.empty or df_recaudacion.empty:
        return pd.DataFrame(), {}

    # Procesar datos
    dte_final = df_recaudacion.merge(df_deposito, on=['branch_office_id', 'date'], how='left')
    dte_final['deposito'] = dte_final['deposito'].fillna(0)
    dte_final['diferencia'] = dte_final['recaudacion'] - dte_final['deposito']
    dte_final['status'] = dte_final['diferencia'].apply(lambda x: "Si" if x != 0 else "No")

    # Merge con sucursales
    if not df_sucursales.empty:
        dte_final = dte_final.merge(
            df_sucursales[['branch_office_id', 'responsable', 'branch_office']],
            on='branch_office_id', how='left'
        )

    # Procesar fechas
    dte_final['date'] = pd.to_datetime(dte_final['date'])
    if not df_periodos.empty:
        df_periodos['date'] = pd.to_datetime(df_periodos['date'])
        dte_final['date_for_merge'] = dte_final['date'].dt.date
        df_periodos['date_for_merge'] = df_periodos['date'].dt.date
        dte_final = dte_final.merge(
            df_periodos[['date_for_merge', 'periodo', 'period', 'año']],
            on='date_for_merge', how='left'
        )

    # Renombrar columnas
    dte_final.rename(columns={
        "branch_office": "sucursal",
        "recaudacion": "recaudado",
        "deposito": "depositado"
    }, inplace=True)

    # Agregar características adicionales
    dte_final['mes'] = dte_final['date'].dt.month
    dte_final['dia_semana'] = dte_final['date'].dt.day_name()
    dte_final['dia_mes'] = dte_final['date'].dt.day
    dte_final['trimestre'] = dte_final['date'].dt.quarter
    dte_final['ratio_deposito'] = np.where(dte_final['recaudado'] > 0,
                                          dte_final['depositado'] / dte_final['recaudado'], 0)

    # Calcular métricas móviles
    dte_final = dte_final.sort_values(['sucursal', 'date'])
    for col in ['recaudado', 'depositado', 'diferencia']:
        dte_final[f'{col}_ma7'] = dte_final.groupby('sucursal')[col].transform(
            lambda x: x.rolling(window=7, min_periods=1).mean()
        )
        dte_final[f'{col}_ma30'] = dte_final.groupby('sucursal')[col].transform(
            lambda x: x.rolling(window=30, min_periods=1).mean()
        )

    # Estadísticas de calidad de datos
    data_quality = {
        'total_records': len(dte_final),
        'missing_values': dte_final.isnull().sum().to_dict(),
        'duplicates': dte_final.duplicated().sum(),
        'date_range': (dte_final['date'].min(), dte_final['date'].max()),
        'unique_branches': dte_final['sucursal'].nunique(),
        'data_completeness': (1 - dte_final.isnull().sum().sum() / (len(dte_final) * len(dte_final.columns))) * 100
    }

    return dte_final, data_quality

# ================ ANÁLISIS ESTADÍSTICOS AVANZADOS ================
def advanced_statistical_analysis(df):
    """Análisis estadístico completo y avanzado"""
    if df.empty:
        return {}

    analysis = {}

    # 1. Estadísticas descriptivas avanzadas
    numeric_cols = ['recaudado', 'depositado', 'diferencia']
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

    # 2. Pruebas de normalidad
    for col in numeric_cols:
        if col in df.columns and len(df[col].dropna()) > 8:
            data = df[col].dropna()
            # Shapiro-Wilk test
            shapiro_stat, shapiro_p = stats.shapiro(data[:5000])  # Limitado a 5000 para eficiencia
            # Kolmogorov-Smirnov test
            ks_stat, ks_p = stats.kstest(data, 'norm', args=(data.mean(), data.std()))

            analysis[f'{col}_normalidad'] = {
                'shapiro_wilk': {'statistic': shapiro_stat, 'p_value': shapiro_p, 'is_normal': shapiro_p > 0.05},
                'kolmogorov_smirnov': {'statistic': ks_stat, 'p_value': ks_p, 'is_normal': ks_p > 0.05}
            }

    # 3. Análisis de correlaciones
    correlation_matrix = df[numeric_cols].corr()
    analysis['correlaciones'] = correlation_matrix.to_dict()

    # 4. Análisis de tendencias temporales
    if 'date' in df.columns:
        df_temp = df.copy()
        df_temp = df_temp.sort_values('date')

        for col in numeric_cols:
            if col in df_temp.columns:
                # Regresión lineal para tendencia
                x = np.arange(len(df_temp))
                y = df_temp[col].values
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

                # Detección de estacionalidad
                if len(df_temp) > 30:
                    # Descomposición básica de tendencia
                    rolling_mean = df_temp[col].rolling(window=30).mean()
                    detrended = df_temp[col] - rolling_mean

                analysis[f'{col}_tendencia'] = {
                    'pendiente': slope,
                    'r_cuadrado': r_value**2,
                    'p_valor': p_value,
                    'significativa': p_value < 0.05,
                    'direccion': 'creciente' if slope > 0 else 'decreciente' if slope < 0 else 'estable'
                }

    # 5. Análisis de ciclos y patrones
    if 'dia_semana' in df.columns:
        pattern_analysis = {}
        for col in numeric_cols:
            if col in df.columns:
                day_patterns = df.groupby('dia_semana')[col].agg(['mean', 'std']).to_dict()
                pattern_analysis[f'{col}_por_dia'] = day_patterns
        analysis['patrones_temporales'] = pattern_analysis

    # 6. Detección de cambios estructurales
    for col in numeric_cols:
        if col in df.columns and len(df[col].dropna()) > 50:
            data = df[col].dropna().values
            # Aplicar test de cambio estructural simple
            mid_point = len(data) // 2
            first_half = data[:mid_point]
            second_half = data[mid_point:]

            # Test t para diferencia de medias
            t_stat, t_p = stats.ttest_ind(first_half, second_half)

            analysis[f'{col}_cambio_estructural'] = {
                't_statistic': t_stat,
                'p_value': t_p,
                'cambio_significativo': t_p < 0.05,
                'media_primera_mitad': np.mean(first_half),
                'media_segunda_mitad': np.mean(second_half)
            }

    return analysis

def detect_anomalies_advanced(df):
    """Detección avanzada de anomalías usando múltiples métodos"""
    if df.empty:
        return df, {}

    df_result = df.copy()
    anomaly_info = {}

    # Características para análisis
    features = ['recaudado', 'depositado', 'diferencia', 'ratio_deposito']
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

    # 2. Z-Score multivariado
    for col in available_features:
        if df[col].std() > 0:
            z_scores = np.abs(stats.zscore(df[col].fillna(df[col].mean())))
            df_result[f'zscore_{col}'] = z_scores
            df_result[f'anomaly_zscore_{col}'] = z_scores > 3

    # 3. IQR method por sucursal
    if 'sucursal' in df.columns:
        for sucursal in df['sucursal'].unique():
            mask = df['sucursal'] == sucursal
            for col in available_features:
                data = df.loc[mask, col]
                if len(data) > 4:
                    Q1 = data.quantile(0.25)
                    Q3 = data.quantile(0.75)
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR

                    outlier_mask = (data < lower_bound) | (data > upper_bound)
                    df_result.loc[mask, f'anomaly_iqr_{col}'] = outlier_mask

    # 4. Detección de picos
    for col in available_features:
        if len(df[col].dropna()) > 10:
            data = df[col].fillna(df[col].mean()).values
            peaks, properties = find_peaks(data, height=np.percentile(data, 95))
            df_result[f'is_peak_{col}'] = False
            df_result.iloc[peaks, df_result.columns.get_loc(f'is_peak_{col}')] = True

    return df_result, anomaly_info

def clustering_analysis(df):
    """Análisis de clustering para segmentación"""
    if df.empty:
        return df, {}

    # Características para clustering
    features = ['recaudado', 'depositado', 'diferencia', 'ratio_deposito']
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
    df, data_quality = load_and_process_data()

    if df.empty:
        st.error("❌ No se pudieron cargar los datos")
        return

    # Header principal
    st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); border-radius: 10px; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0;'>🏦 Dashboard - Depósitos</h1>
        
    </div>
    """, unsafe_allow_html=True)

    # Mostrar calidad de datos
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Total Registros", f"{data_quality['total_records']:,}")
    with col2:
        st.metric("🏢 Sucursales", data_quality['unique_branches'])
    with col3:
        st.metric("✅ Completitud", f"{data_quality['data_completeness']:.1f}%")
    with col4:
        days_diff = (data_quality['date_range'][1] - data_quality['date_range'][0]).days
        st.metric("📅 Días de Datos", days_diff)

    # Crear pestañas
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Resumen Ejecutivo",
        "📈 Análisis Temporal",
        "🔍 Detección Anomalías",
        "📊 Análisis Estadístico",
        "🎯 Segmentación",
        "🏢 Análisis por Sucursal"
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

    with tab6:
        create_branch_analysis_tab(df_filtered)

def apply_filters(df):
    """Aplica filtros desde sidebar"""
    st.sidebar.header("🔍 Filtros de Análisis")

    # Filtro por sucursal
    sucursales_disponibles = ['Todas'] + list(df['sucursal'].dropna().unique())
    sucursal_seleccionada = st.sidebar.selectbox("Sucursal:", sucursales_disponibles)

    # Filtro por período
    if 'periodo' in df.columns:
        periodos_disponibles = ['Todos'] + list(df['periodo'].dropna().unique())
        periodo_seleccionado = st.sidebar.selectbox("Período:", periodos_disponibles)
    else:
        periodo_seleccionado = 'Todos'

    # Filtro por rango de fechas
    fecha_min = df['date'].min().date()
    fecha_max = df['date'].max().date()

    fecha_range = st.sidebar.date_input(
        "Rango de fechas:",
        value=[fecha_min, fecha_max],
        min_value=fecha_min,
        max_value=fecha_max
    )

    # Filtros adicionales
    st.sidebar.subheader("Filtros Avanzados")

    # Filtro por monto mínimo
    min_amount = st.sidebar.number_input(
        "Monto mínimo recaudado:",
        min_value=0,
        value=0,
        step=1000
    )

    # Filtro por estado
    status_filter = st.sidebar.selectbox(
        "Estado de diferencias:",
        ['Todos', 'Con diferencias', 'Sin diferencias']
    )

    # Aplicar filtros
    df_filtered = df.copy()

    if sucursal_seleccionada != 'Todas':
        df_filtered = df_filtered[df_filtered['sucursal'] == sucursal_seleccionada]

    if periodo_seleccionado != 'Todos' and 'periodo' in df_filtered.columns:
        df_filtered = df_filtered[df_filtered['periodo'] == periodo_seleccionado]

    if len(fecha_range) == 2:
        df_filtered = df_filtered[
            (df_filtered['date'].dt.date >= fecha_range[0]) &
            (df_filtered['date'].dt.date <= fecha_range[1])
        ]

    if min_amount > 0:
        df_filtered = df_filtered[df_filtered['recaudado'] >= min_amount]

    if status_filter == 'Con diferencias':
        df_filtered = df_filtered[df_filtered['status'] == 'Si']
    elif status_filter == 'Sin diferencias':
        df_filtered = df_filtered[df_filtered['status'] == 'No']

    return df_filtered

def create_executive_summary(df):
    """Pestaña de resumen ejecutivo"""
    if df.empty:
        st.warning("No hay datos para mostrar")
        return

    # KPIs principales
    col1, col2, col3, col4 = st.columns(4)

    total_recaudado = df['recaudado'].sum()
    total_depositado = df['depositado'].sum()
    diferencia_total = df['diferencia'].sum()
    tasa_deposito = (total_depositado / total_recaudado * 100) if total_recaudado > 0 else 0

    with col1:
        st.metric("💰 Total Recaudado", format_currency(total_recaudado))
    with col2:
        st.metric("🏦 Total Depositado", format_currency(total_depositado))
    with col3:
        st.metric("📊 Tasa Depósito", f"{tasa_deposito:.1f}%")
    with col4:
        delta_color = "normal" if diferencia_total >= 0 else "inverse"
        st.metric("📈 Diferencia Neta", format_currency(diferencia_total))

    st.markdown("---")

    # Gráficos principales
    col1, col2 = st.columns(2)

    with col1:
        # Distribución por sucursal
        fig_pie = px.pie(
            df.groupby('sucursal')['recaudado'].sum().reset_index(),
            values='recaudado',
            names='sucursal',
            title='Distribución de Recaudación por Sucursal'
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Evolución temporal
        daily_data = df.groupby('date').agg({
            'recaudado': 'sum',
            'depositado': 'sum'
        }).reset_index()

        fig_evolution = go.Figure()
        fig_evolution.add_trace(go.Scatter(
            x=daily_data['date'],
            y=daily_data['recaudado'],
            mode='lines',
            name='Recaudado',
            line=dict(color='blue', width=3)
        ))
        fig_evolution.add_trace(go.Scatter(
            x=daily_data['date'],
            y=daily_data['depositado'],
            mode='lines',
            name='Depositado',
            line=dict(color='red', width=3)
        ))
        fig_evolution.update_layout(title='Evolución Temporal')
        st.plotly_chart(fig_evolution, use_container_width=True)

    # Alertas y recomendaciones
    st.subheader("🚨 Alertas y Recomendaciones")

    # Detectar problemas
    discrepancias = df[df['diferencia'] != 0]
    tasa_discrepancias = len(discrepancias) / len(df) * 100

    if tasa_discrepancias > 10:
        st.markdown("""
        <div class="alert-box alert-danger">
            <strong>⚠️ Alta tasa de discrepancias:</strong>
            Se detectó un {:.1f}% de transacciones con diferencias.
            Revisar procesos de depósito.
        </div>
        """.format(tasa_discrepancias), unsafe_allow_html=True)
    elif tasa_discrepancias > 5:
        st.markdown("""
        <div class="alert-box alert-warning">
            <strong>⚡ Tasa moderada de discrepancias:</strong>
            {:.1f}% de transacciones tienen diferencias. Monitorear tendencia.
        </div>
        """.format(tasa_discrepancias), unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="alert-box alert-success">
            <strong>✅ Buen desempeño:</strong>
            Baja tasa de discrepancias ({:.1f}%). Mantener estándares actuales.
        </div>
        """.format(tasa_discrepancias), unsafe_allow_html=True)

def create_temporal_analysis(df):
    """Análisis temporal avanzado"""
    if df.empty:
        st.warning("No hay datos para análisis temporal")
        return

    st.subheader("📈 Análisis Temporal Avanzado")

    # Análisis de tendencias
    daily_data = df.groupby('date').agg({
        'recaudado': 'sum',
        'depositado': 'sum',
        'diferencia': 'sum'
    }).reset_index()

    # Gráfico principal con tendencias
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=['Recaudación y Depósitos', 'Diferencias Diarias', 'Análisis de Volatilidad'],
        vertical_spacing=0.08,
        row_heights=[0.4, 0.3, 0.3]
    )

    # Gráfico 1: Series temporales con medias móviles
    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['recaudado'],
        mode='lines',
        name='Recaudado',
        line=dict(color='blue', width=2)
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['depositado'],
        mode='lines',
        name='Depositado',
        line=dict(color='red', width=2)
    ), row=1, col=1)

    # Gráfico 2: Diferencias diarias
    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['diferencia'],
        mode='lines',
        name='Diferencia',
        line=dict(color='green', width=2)
    ), row=2, col=1)

    # Gráfico 3: Análisis de volatilidad
    fig.add_trace(go.Scatter(
        x=daily_data['date'],
        y=daily_data['diferencia'].rolling(window=7).std(),
        mode='lines',
        name='Volatilidad (7 días)',
        line=dict(color='purple', width=2)
    ), row=3, col=1)

    fig.update_layout(height=800, showlegend=True)
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
            x='date',
            y='diferencia',
            color='anomaly_isolation',
            title='Anomalías detectadas por Isolation Forest'
        )
        st.plotly_chart(fig_iso, use_container_width=True)

    with col2:
        # Anomalías por Z-Score
        fig_zscore = px.scatter(
            df_with_anomalies,
            x='date',
            y='diferencia',
            color='anomaly_zscore_diferencia',
            title='Anomalías detectadas por Z-Score'
        )
        st.plotly_chart(fig_zscore, use_container_width=True)

def create_statistical_analysis_tab(df):
    """Pestaña de análisis estadístico"""
    if df.empty:
        st.warning("No hay datos para análisis estadístico")
        return

    st.subheader("📊 Análisis Estadístico Avanzado")

    # Realizar análisis estadístico
    analysis = advanced_statistical_analysis(df)

    # Mostrar estadísticas descriptivas en tablas
    st.write("### Estadísticas Descriptivas")
    for col in ['recaudado', 'depositado', 'diferencia']:
        if f'{col}_stats' in analysis:
            stats = analysis[f'{col}_stats']
            stats_df = pd.DataFrame.from_dict(stats, orient='index', columns=['Value'])
            st.write(f"#### {col.capitalize()}")
            st.table(stats_df)

    # Mostrar pruebas de normalidad
    st.write("### Pruebas de Normalidad")
    for col in ['recaudado', 'depositado', 'diferencia']:
        if f'{col}_normalidad' in analysis:
            normalidad = analysis[f'{col}_normalidad']
            st.write(f"#### {col.capitalize()}")
            for test, values in normalidad.items():
                st.write(f"**{test.replace('_', ' ').title()}**")
                st.write(f"Estadístico: {values['statistic']:.4f}")
                st.write(f"Valor p: {values['p_value']:.4f}")
                st.write(f"¿Es normal?: {'Sí' if values['is_normal'] else 'No'}")
                st.write("---")

    # Mostrar correlaciones con un heatmap
    st.write("### Análisis de Correlaciones")
    if 'correlaciones' in analysis:
        correlaciones = pd.DataFrame(analysis['correlaciones'])
        fig_corr = px.imshow(
            correlaciones,
            labels=dict(x="Variables", y="Variables", color="Correlación"),
            x=correlaciones.columns,
            y=correlaciones.columns,
            color_continuous_scale='RdBu_r'
        )
        st.plotly_chart(fig_corr, use_container_width=True)

    # Mostrar análisis de tendencias
    st.write("### Análisis de Tendencias")
    for col in ['recaudado', 'depositado', 'diferencia']:
        if f'{col}_tendencia' in analysis:
            tendencia = analysis[f'{col}_tendencia']
            st.write(f"#### {col.capitalize()}")
            st.write(f"Pendiente: {tendencia['pendiente']:.4f}")
            st.write(f"R cuadrado: {tendencia['r_cuadrado']:.4f}")
            st.write(f"Dirección: {tendencia['direccion'].capitalize()}")
            st.write("---")


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
        x='recaudado',
        y='depositado',
        color='cluster',
        title='Segmentación por Clustering'
    )
    st.plotly_chart(fig_cluster, use_container_width=True)

def create_branch_analysis_tab(df):
    """Pestaña de análisis por sucursal"""
    if df.empty:
        st.warning("No hay datos para análisis por sucursal")
        return

    st.subheader("🏢 Análisis por Sucursal")

    # Análisis por sucursal
    sucursal_stats = df.groupby('sucursal').agg({
        'recaudado': ['sum', 'mean', 'std'],
        'depositado': ['sum', 'mean', 'std'],
        'diferencia': ['sum', 'mean', 'std']
    }).reset_index()

    # Aplanar las columnas MultiIndex
    sucursal_stats.columns = ['sucursal'] + ['_'.join(col).strip() for col in sucursal_stats.columns.values[1:]]

    st.write("### Estadísticas por Sucursal")
    st.dataframe(sucursal_stats)

    # Visualización por sucursal
    fig_branch = px.bar(
        sucursal_stats,
        x='sucursal',  # Cambiado a 'sucursal'
        y='recaudado_sum',
        title='Recaudación Total por Sucursal'
    )
    st.plotly_chart(fig_branch, use_container_width=True) 

    fig_branch = px.bar(
        sucursal_stats,
        x='sucursal',  # Cambiado a 'sucursal'
        y='depositado_sum',
        title='Depositado Total por Sucursal'
    )
    st.plotly_chart(fig_branch, use_container_width=True)

    fig_branch = px.bar(
        sucursal_stats,
        x='sucursal',  # Cambiado a 'sucursal'
        y='diferencia_sum',
        title='Diferencia Total por Sucursal'
    )
    st.plotly_chart(fig_branch, use_container_width=True)
    
    fig_branch = px.bar(
        sucursal_stats,
        x='sucursal',  # Cambiado a 'sucursal'
        y='diferencia_mean',
        title='Diferencia Promedio por Sucursal'
    )
    st.plotly_chart(fig_branch, use_container_width=True)
    
    fig_branch = px.bar(
        sucursal_stats,
        x='sucursal',  # Cambiado a 'sucursal'
        y='diferencia_std',
        title='Diferencia Desviación por Sucursal'
    )
    st.plotly_chart(fig_branch, use_container_width=True)
    
    fig_branch = px.bar(
        sucursal_stats,
        x='sucursal',  # Cambiado a 'sucursal'
        y='depositado_mean',
        title='Depositado Promedio por Sucursal'
    )
    st.plotly_chart(fig_branch, use_container_width=True)
    
    fig_branch = px.bar(
        sucursal_stats,
        x='sucursal',  # Cambiado a 'sucursal'
        y='depositado_std',
        title='Depositado Desviación por Sucursal'
    )
    st.plotly_chart(fig_branch, use_container_width=True)
    
    fig_branch = px.bar(
        sucursal_stats,
        x='sucursal',  # Cambiado a 'sucursal'
        y='recaudado_mean',
        title='Recaudación Promedio por Sucursal'
    )
    st.plotly_chart(fig_branch, use_container_width=True)
    
    fig_branch = px.bar(
        sucursal_stats,
        x='sucursal',  # Cambiado a 'sucursal'
        y='recaudado_std',
        title='Recaudación Desviación por Sucursal'
    )
    st.plotly_chart(fig_branch, use_container_width=True)


# Punto de entrada de la aplicación
if __name__ == "__main__":
    create_advanced_dashboard()
