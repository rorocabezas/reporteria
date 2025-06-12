# pages/indicadores.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from menu import generarMenu
from utils import format_currency, format_percentage, format_number
import streamlit.components.v1 as components
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Configuración de la página
st.set_page_config(page_title="Indicadores Económicos", layout="wide")

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

# ============== FUNCIONES DE API ==============
def get_uf_data():
    url = "http://localhost:8000/uf"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error al obtener datos de UF")
        return None

def get_dolar_data():
    url = "http://localhost:8000/dolar"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error al obtener datos de Dólar")
        return None

def get_ipc_data():
    url = "http://localhost:8000/ipc"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error al obtener datos de IPC")
        return None

def get_euro_data():
    url = "http://localhost:8000/euro"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error al obtener datos de Euro")
        return None

def get_imacec_data():
    url = "http://localhost:8000/imacec"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error al obtener datos de IMACEC")
        return None

def get_tasa_desempleo_data():
    url = "http://localhost:8000/tasa_desempleo"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error al obtener datos de Tasa de Desempleo")
        return None


def get_daily_indicators():
    url = "https://mindicador.cl/api"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        st.error("Error al obtener datos de la API de Mindicador")
        return None

# ============== FUNCIONES DE ANÁLISIS ESTADÍSTICO ==============
def calculate_statistics(df, value_col='valor'):
    """Calcula estadísticas descriptivas avanzadas"""
    if df.empty or value_col not in df.columns:
        return {}
    
    values = df[value_col].dropna()
    if len(values) == 0:
        return {}
    
    # Convertir a numérico si es necesario
    values = pd.to_numeric(values, errors='coerce').dropna()
    
    stats_dict = {
        'count': len(values),
        'mean': values.mean(),
        'median': values.median(),
        'std': values.std(),
        'min': values.min(),
        'max': values.max(),
        'q25': values.quantile(0.25),
        'q75': values.quantile(0.75),
        'iqr': values.quantile(0.75) - values.quantile(0.25),
        'cv': (values.std() / values.mean()) * 100 if values.mean() != 0 else 0,
        'skewness': stats.skew(values),
        'kurtosis': stats.kurtosis(values)
    }
    
    # Calcular tendencia (pendiente de regresión lineal)
    if len(values) > 1:
        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        stats_dict.update({
            'trend_slope': slope,
            'trend_r2': r_value**2,
            'trend_p_value': p_value
        })
    
    return stats_dict

def calculate_volatility(df, value_col='valor', window=30):
    """Calcula la volatilidad móvil"""
    if df.empty or value_col not in df.columns:
        return df
    
    df = df.copy()
    df[value_col] = pd.to_numeric(df[value_col], errors='coerce')
    df['returns'] = df[value_col].pct_change()
    df['volatility'] = df['returns'].rolling(window=window).std() * np.sqrt(252)  # Anualizada
    return df

def detect_anomalies(df, value_col='valor', method='iqr'):
    """Detecta valores atípicos usando IQR o Z-score"""
    if df.empty or value_col not in df.columns:
        return df
    
    df = df.copy()
    values = pd.to_numeric(df[value_col], errors='coerce')
    
    if method == 'iqr':
        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df['is_anomaly'] = (values < lower_bound) | (values > upper_bound)
    
    elif method == 'zscore':
        z_scores = np.abs(stats.zscore(values.dropna()))
        df['is_anomaly'] = False
        df.loc[values.notna(), 'is_anomaly'] = z_scores > 3
    
    return df


def map_indicator_name(name):
    mapping = {
        "uf": "UF",
        "dolar": "DÓLAR",
        "euro": "EURO",
        "ipc": "I.P.C",
        "utm": "U.T.M",
        "imacec": "IMACEC",
        "tpm": "T.P.M",
        "tasa_desempleo": "DESEMPLEO"
    }
    return mapping.get(name, name.upper())

# ============== FUNCIONES DE VISUALIZACIÓN ==============
def create_advanced_line_chart(df, title, y_col='valor', show_anomalies=True):
    """Crea un gráfico de líneas con estadísticas avanzadas"""
    if df.empty:
        return go.Figure()
    
    # Detectar anomalías
    df_with_anomalies = detect_anomalies(df, y_col) if show_anomalies else df
    
    # Calcular volatilidad
    df_with_vol = calculate_volatility(df_with_anomalies, y_col)
    
    # Crear subplot
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        subplot_titles=[title, 'Volatilidad'],
        vertical_spacing=0.1
    )
    
    # Gráfico principal
    fig.add_trace(
        go.Scatter(
            x=df['periodo'],
            y=df[y_col],
            mode='lines',
            name='Valor',
            line=dict(color='#2E86AB', width=2),
            hovertemplate='<b>%{y}</b><br>Fecha: %{x}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Añadir anomalías si existen
    if show_anomalies and 'is_anomaly' in df_with_anomalies.columns:
        anomalies = df_with_anomalies[df_with_anomalies['is_anomaly']]
        if not anomalies.empty:
            fig.add_trace(
                go.Scatter(
                    x=anomalies['periodo'],
                    y=anomalies[y_col],
                    mode='markers',
                    name='Anomalías',
                    marker=dict(color='red', size=8, symbol='x'),
                    hovertemplate='<b>Anomalía: %{y}</b><br>Fecha: %{x}<extra></extra>'
                ),
                row=1, col=1
            )
    
    # Añadir líneas de tendencia
    if len(df) > 1:
        x_numeric = np.arange(len(df))
        y_numeric = pd.to_numeric(df[y_col], errors='coerce').dropna()
        if len(y_numeric) > 1:
            slope, intercept, r_value, p_value, std_err = stats.linregress(x_numeric[:len(y_numeric)], y_numeric)
            trend_line = slope * x_numeric + intercept
            
            fig.add_trace(
                go.Scatter(
                    x=df['periodo'],
                    y=trend_line,
                    mode='lines',
                    name=f'Tendencia (R²={r_value**2:.3f})',
                    line=dict(color='orange', width=1, dash='dash'),
                    hovertemplate='Tendencia: %{y}<extra></extra>'
                ),
                row=1, col=1
            )
    
    # Gráfico de volatilidad
    if 'volatility' in df_with_vol.columns:
        fig.add_trace(
            go.Scatter(
                x=df_with_vol['periodo'],
                y=df_with_vol['volatility'],
                mode='lines',
                name='Volatilidad',
                line=dict(color='#A23B72', width=1),
                hovertemplate='Volatilidad: %{y:.4f}<extra></extra>'
            ),
            row=2, col=1
        )
    
    # Actualizar layout
    fig.update_layout(
        height=600,
        showlegend=True,
        template='plotly_white',
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="Periodo", row=2, col=1)
    fig.update_yaxes(title_text="Valor", row=1, col=1)
    fig.update_yaxes(title_text="Volatilidad", row=2, col=1)
    
    return fig

def create_distribution_chart(df, title, y_col='valor'):
    """Crea un gráfico de distribución con estadísticas"""
    if df.empty or y_col not in df.columns:
        return go.Figure()
    
    values = pd.to_numeric(df[y_col], errors='coerce').dropna()
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[f'Histograma - {title}', f'Box Plot - {title}'],
        column_widths=[0.6, 0.4]
    )
    
    # Histograma
    fig.add_trace(
        go.Histogram(
            x=values,
            nbinsx=30,
            name='Distribución',
            marker_color='#2E86AB',
            opacity=0.7
        ),
        row=1, col=1
    )
    
    # Box plot
    fig.add_trace(
        go.Box(
            y=values,
            name='Estadísticas',
            marker_color='#A23B72',
            boxpoints='outliers'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=400,
        showlegend=False,
        template='plotly_white'
    )
    
    return fig



# ============== FUNCIÓN PARA CREAR CARDS MEJORADOS ==============
def create_enhanced_card(indicador, valor_actual, stats_dict, icon="📈"):
    """Crea un card mejorado con estadísticas"""
    if stats_dict:
        trend_emoji = "📈" if stats_dict.get('trend_slope', 0) > 0 else "📉"
        volatility = stats_dict.get('cv', 0)
        vol_level = "Alta" if volatility > 10 else "Media" if volatility > 5 else "Baja"
    else:
        trend_emoji = "➖"
        vol_level = "N/A"
    
    return f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h3 style="margin: 0; font-size: 1.1em; opacity: 0.9;">{indicador}</h3>
                <h2 style="margin: 5px 0; font-size: 1.8em;">{valor_actual}</h2>
                <p style="margin: 0; font-size: 0.9em; opacity: 0.8;">
                    Tendencia: {trend_emoji} | Volatilidad: {vol_level}
                </p>
            </div>
            <div style="font-size: 2em; opacity: 0.7;">
                {icon}
            </div>
        </div>
    </div>
    """

# ============== APLICACIÓN PRINCIPAL ==============
def main():
    # Título principal con estilo
    st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); border-radius: 10px; margin-bottom: 20px;'>
        <h1 style="color:white; font-size: 3em; margin-bottom: 10px;">
            📊 Indicadores Económicos
        </h1>        
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Obtener datos
    with st.spinner("Cargando datos de indicadores económicos..."):
        data = get_daily_indicators()
        uf_data = get_uf_data()
        dolar_data = get_dolar_data()
        ipc_data = get_ipc_data()
        euro_data = get_euro_data()
        imacec_data = get_imacec_data()
        tasa_desempleo_data = get_tasa_desempleo_data()
 
    
    # Procesar DataFrames
    dfs = {}
    if uf_data:
        dfs['UF'] = pd.DataFrame(uf_data["data"], columns=uf_data["columns"])
    if dolar_data:
        dfs['DOLAR'] = pd.DataFrame(dolar_data["data"], columns=dolar_data["columns"])
    if euro_data:
        dfs['EURO'] = pd.DataFrame(euro_data["data"], columns=euro_data["columns"])
    if ipc_data:
        dfs['IPC'] = pd.DataFrame(ipc_data["data"], columns=ipc_data["columns"])
    if imacec_data:
        dfs['IMACEC'] = pd.DataFrame(imacec_data["data"], columns=imacec_data["columns"])
    if tasa_desempleo_data:
        dfs['DESEMPLEO'] = pd.DataFrame(tasa_desempleo_data["data"], columns=tasa_desempleo_data["columns"])
    
    # Sección de Cards con valores actuales
    st.subheader("📋 Resumen de Indicadores")
    
    if data:
        cols = st.columns(4)
        indicadores = ["uf", "dolar", "euro", "ipc", "utm", "imacec", "tpm", "tasa_desempleo"]
        
        for idx, indicador in enumerate(indicadores[:8]):  # Mostrar 8 indicadores
            if indicador in data:
                valor = data[indicador]["valor"]
                unidad = data[indicador]["unidad_medida"]
                
                # Formatear valor
                if unidad == "Pesos":
                    valor_formateado = format_currency(valor)
                elif unidad == "Porcentaje":
                    valor_formateado = format_percentage(valor)
                else:
                    valor_formateado = format_number(valor)
                
                # Obtener estadísticas si disponible
                indicator_name = map_indicator_name(indicador)
                stats_dict = calculate_statistics(dfs.get(indicator_name, pd.DataFrame())) if indicator_name in dfs else {}
                
                with cols[idx % 4]:
                    st.markdown(
                        create_enhanced_card(
                            indicator_name,
                            valor_formateado,
                            stats_dict,
                            ["📈", "💵", "💶", "📊", "📋", "🏭", "🏦", "👥"][idx]
                        ),
                        unsafe_allow_html=True
                    )
    
    st.markdown("---")
    
   
    
    # Gráficos detallados por indicador
    st.subheader("📈 Análisis Detallado por Indicador")
    
    # Selector de indicador
    available_indicators = list(dfs.keys())
    if available_indicators:
        selected_indicator = st.selectbox(
            "Selecciona un indicador para análisis detallado:",
            available_indicators
        )
        
        if selected_indicator and selected_indicator in dfs:
            df_selected = dfs[selected_indicator]
            
            # Calcular estadísticas
            stats = calculate_statistics(df_selected)
            
            # Mostrar estadísticas en columnas
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Promedio", format_number(stats.get('mean', 0)))
                st.metric("Mediana", format_number(stats.get('median', 0)))
            
            with col2:
                st.metric("Desv. Estándar", format_number(stats.get('std', 0)))
                st.metric("Coef. Variación", f"{stats.get('cv', 0):.2f}%")
            
            with col3:
                st.metric("Mínimo", format_number(stats.get('min', 0)))
                st.metric("Máximo", format_number(stats.get('max', 0)))
            
            with col4:
                trend_direction = "↗️" if stats.get('trend_slope', 0) > 0 else "↘️"
                st.metric("Tendencia", trend_direction)
                st.metric("R² Tendencia", f"{stats.get('trend_r2', 0):.3f}")
            
            # Gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                fig_line = create_advanced_line_chart(df_selected, selected_indicator)
                st.plotly_chart(fig_line, use_container_width=True)
            
            with col2:
                fig_dist = create_distribution_chart(df_selected, selected_indicator)
                st.plotly_chart(fig_dist, use_container_width=True)
            
            # Tabla de estadísticas detalladas
            with st.expander("📊 Estadísticas Detalladas"):
                stats_df = pd.DataFrame([
                    ["Observaciones", f"{stats.get('count', 0):,}"],
                    ["Promedio", format_number(stats.get('mean', 0))],
                    ["Mediana", format_number(stats.get('median', 0))],
                    ["Desviación Estándar", format_number(stats.get('std', 0))],
                    ["Varianza", format_number(stats.get('std', 0)**2)],
                    ["Coeficiente de Variación", f"{stats.get('cv', 0):.2f}%"],
                    ["Asimetría", f"{stats.get('skewness', 0):.3f}"],
                    ["Curtosis", f"{stats.get('kurtosis', 0):.3f}"],
                    ["Rango Intercuartílico", format_number(stats.get('iqr', 0))],
                    ["Pendiente de Tendencia", f"{stats.get('trend_slope', 0):.6f}"],
                    ["R² de Tendencia", f"{stats.get('trend_r2', 0):.3f}"],
                    ["P-valor Tendencia", f"{stats.get('trend_p_value', 1):.6f}"]
                ], columns=["Estadística", "Valor"])
                
                st.dataframe(stats_df, use_container_width=True)

if __name__ == "__main__":
    main()
   
    
 
    