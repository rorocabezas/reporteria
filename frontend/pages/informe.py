# pages/informe.py
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from menu import generarMenu
from utils import format_currency, format_percentage, calcular_variacion, calcular_ticket_promedio, calcular_variacion_total, calcular_ticket_total
import warnings
import numpy as np
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

# Configuración de página
st.set_page_config(
    page_title="Dashboard Ventas Avanzado",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# CSS personalizado mejorado
st.markdown("""
<style>
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
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-card-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        transition: transform 0.3s ease;
    }
    .metric-card-blue:hover {
        transform: translateY(-5px);
    }
    .metric-card-green {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        transition: transform 0.3s ease;
    }
    .metric-card-green:hover {
        transform: translateY(-5px);
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        transition: transform 0.3s ease;
    }
    .metric-card-orange:hover {
        transform: translateY(-5px);
    }
    .metric-card-purple {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        transition: transform 0.3s ease;
    }
    .metric-card-purple:hover {
        transform: translateY(-5px);
    }
    .alert-box {
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .alert-success { 
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%); 
        border-left: 5px solid #28a745; 
        color: #155724;
    }
    .alert-warning { 
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%); 
        border-left: 5px solid #ffc107; 
        color: #856404;
    }
    .alert-danger { 
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%); 
        border-left: 5px solid #dc3545; 
        color: #721c24;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.2rem;
        font-weight: 700;
    }
    .filter-container {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        text-align: center;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .performance-indicator {
        padding: 0.5rem;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        text-align: center;
    }
    .performance-good { background-color: #28a745; }
    .performance-warning { background-color: #ffc107; color: #212529; }
    .performance-danger { background-color: #dc3545; }
</style>
""", unsafe_allow_html=True)

# Título principal con estilo
st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); border-radius: 10px; margin-bottom: 20px;'>
        <h1 style="color:white; font-size: 3em; margin-bottom: 10px;">
            📊 Dashboard - Ingresos
        </h1>
               
    </div>
    """, unsafe_allow_html=True)

# Generar el menú
generarMenu()

# Función para obtener datos de endpoints
@st.cache_data(ttl=300, show_spinner=False)
def fetch_data_from_endpoint(endpoint):
    try:
        with st.spinner(f'🔄 Cargando datos de {endpoint}...'):
            response = requests.get(f"http://localhost:8000/{endpoint}", timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'data' not in data or 'columns' not in data:
                st.error(f"❌ Formato de datos incorrecto en {endpoint}")
                return pd.DataFrame()

            df = pd.DataFrame(data['data'], columns=data['columns'])
            return df
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error de conexión en {endpoint}: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Error inesperado al cargar datos de {endpoint}: {e}")
        return pd.DataFrame()

# Función para crear cards mejoradas
def create_enhanced_card(title, value, icon, color_class, description="", trend=""):
    return f"""
    <div class="{color_class}">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <div>
                <h3 style="margin: 0; font-size: 0.9rem; opacity: 0.9;">{title}</h3>
                <h1 style="margin: 0.5rem 0; font-size: 1.8rem; font-weight: bold;">{value}</h1>
                <p style="margin: 0; font-size: 0.8rem; opacity: 0.8;">{description}</p>
            </div>
            <div style="font-size: 2rem; opacity: 0.7;">
                {icon}
            </div>
        </div>
        {f'<div style="margin-top: 0.5rem; font-size: 0.8rem; font-weight: bold;">{trend}</div>' if trend else ''}
    </div>
    """




# Función para calcular indicadores de performance
def calculate_performance_indicators(df_group):
    # Inicializar el diccionario con valores predeterminados
    indicators = {
        'growth_rate': 0,
        'budget_achievement': 0,
        'avg_per_branch': 0,
        'avg_ticket': 0,
        'total_branches': 0
    }

    # Verificar si las columnas necesarias están presentes
    required_columns = ['Ingresos_SSS_2025', 'Ingresos_SSS_2024', 'Ingresos_2025', 'Presupuesto', 'ticket_number_2025']
    for column in required_columns:
        if column not in df_group.columns:
            print(f"Advertencia: La columna '{column}' no está presente en el DataFrame.")
            return indicators

    try:
        # Crecimiento vs año anterior
        total_2025 = df_group['Ingresos_SSS_2025'].iloc[-1] if not df_group.empty else 0
        total_2024 = df_group['Ingresos_SSS_2024'].iloc[-1] if not df_group.empty else 0
        growth_rate = ((total_2025 - total_2024) / total_2024 * 100) if total_2024 > 0 else 0

        # Cumplimiento presupuesto
        total_actual = df_group['Ingresos_2025'].iloc[-1] if not df_group.empty else 0
        total_budget = df_group['Presupuesto'].iloc[-1] if not df_group.empty else 0
        budget_achievement = (total_actual / total_budget * 100) if total_budget > 0 else 0

        # Productividad por sucursal
        avg_per_branch = total_actual / (len(df_group) - 1) if len(df_group) > 1 else 0

        # Ticket promedio
        total_tickets = df_group['ticket_number_2025'].iloc[-1] if not df_group.empty else 0
        avg_ticket = total_actual / total_tickets if total_tickets > 0 else 0

        # Actualizar el diccionario de indicadores
        indicators.update({
            'growth_rate': growth_rate,
            'budget_achievement': budget_achievement,
            'avg_per_branch': avg_per_branch,
            'avg_ticket': avg_ticket,
            'total_branches': len(df_group) - 1 if len(df_group) > 1 else 0
        })
    except Exception as e:
        print(f"Error al calcular indicadores: {e}")

    return indicators




# Función principal mejorada
def display_informe_ventas():
    # Cargar los datos primero
    df_total = fetch_data_from_endpoint("ingresos_acum_dia")
    df_ppto = fetch_data_from_endpoint("ingresos_acum_dia_ppto")
    df_sucursales = fetch_data_from_endpoint("sucursales")
    
    if df_total.empty or df_ppto.empty or df_sucursales.empty:
        st.error("No se pudieron cargar todos los datos necesarios")
        return pd.DataFrame()

    # Procesamiento de datos (mantener la lógica original)
    # INGRESOS ACTUAL 2025  
    df_ingresos_2025 = df_total[(df_total['año'] == 2025)]
    df_ingresos_2025['date'] = pd.to_datetime(df_ingresos_2025['date'])
    df_ingresos_2025['date'] = df_ingresos_2025['date'].dt.strftime('%Y-%m-%d')
    df_ingresos_2025 = df_ingresos_2025.rename(columns={'date': 'fecha'})
    df_ingresos_2025_grouped = df_ingresos_2025.groupby(['fecha', 'branch_office_id'])[["ticket_number", "cash_amount", "cash_net_amount", "card_amount", 
                       "card_net_amount", "subscribers", "venta_neta", "venta_bruta", "ingresos_neto", "venta_sss", "ingresos_sss"]].sum().reset_index()
    
    # INGRESOS ANTERIOR 2024
    df_ingresos_2024 = df_total[(df_total['año'] == 2024)]
    df_ingresos_2024['date'] = pd.to_datetime(df_ingresos_2024['date'])
    df_ingresos_2024['fecha'] = df_ingresos_2024['date'] + pd.Timedelta(days=366)
    df_ingresos_2024['fecha'] = df_ingresos_2024['fecha'].dt.strftime('%Y-%m-%d')
    df_ingresos_2024['date'] = df_ingresos_2024['date'].dt.strftime('%Y-%m-%d')
    df_ingresos_2024_grouped = df_ingresos_2024.groupby(['fecha', 'branch_office_id'])[["ticket_number", "cash_amount", "cash_net_amount", "card_amount", 
                       "card_net_amount", "subscribers", "venta_neta", "venta_bruta", "ingresos_neto", "venta_sss", "ingresos_sss"]].sum().reset_index()
    
    # PPTO 2025
    df_ppto_2025 = df_ppto[(df_ppto['año'] == 2025)]
    df_ppto_2025['date'] = pd.to_datetime(df_ppto_2025['date'])
    df_ppto_2025['date'] = df_ppto_2025['date'].dt.strftime('%Y-%m-%d')
    df_ppto_2025 = df_ppto_2025.rename(columns={'date': 'fecha'})
    df_ppto_2025_grouped = df_ppto_2025.groupby(['fecha', 'branch_office_id'])[['ppto']].sum().reset_index()
    
    # CONCAT DE INGRESOS (mantener lógica original)
    df_concat = pd.merge(df_ingresos_2025_grouped, df_ingresos_2024_grouped, on=['fecha', 'branch_office_id'], how='outer').reset_index(drop=True)
    df_concat = df_concat.rename(columns={'ticket_number_x': 'ticket_number_2025', 'ticket_number_y': 'ticket_number_2024', 
                                          'cash_amount_x': 'efectivo_2025', 'cash_amount_y': 'efectivo_2024', 
                                          'card_amount_x': 'tarjeta_2025', 'card_amount_y': 'tarjeta_2024',
                                          'cash_net_amount_x': 'efectivo_neto_2025', 'cash_net_amount_y': 'efectivo_neto_2024', 
                                          'card_net_amount_x': 'tarjeta_neto_2025', 'card_net_amount_y': 'tarjeta_neto_2024',
                                          'subscribers_x': 'abonados_2025', 'subscribers_y': 'abonados_2024',
                                          'venta_neta_x': 'venta_neta_2025', 'venta_neta_y': 'venta_neta_2024',
                                          'venta_bruta_x': 'venta_bruta_2025', 'venta_bruta_y': 'venta_bruta_2024',
                                          'ingresos_neto_x': 'ingresos_neto_2025', 'ingresos_neto_y': 'ingresos_neto_2024',
                                          'venta_sss_x': 'venta_sss_2025', 'venta_sss_y': 'venta_sss_2024',
                                          'ingresos_sss_x': 'ingresos_sss_2025', 'ingresos_sss_y': 'ingresos_sss_2024'
                                          })
    
    # Completar datos faltantes
    columns_to_fill = ['ingresos_neto_2025', 'ingresos_neto_2024', 'ingresos_sss_2025', 'ingresos_sss_2024', 'ticket_number_2025', 'ticket_number_2024']
    for col in columns_to_fill:
        df_concat[col] = df_concat[col].fillna(0)
    
    # AGREGAR COLUMNAS PPTO Y SUCURSAL
    df_concat = pd.merge(df_concat, df_ppto_2025_grouped, on=['fecha', 'branch_office_id'], how='outer')
    df_concat = df_concat.rename(columns={'ppto': 'Presupuesto'})
    df_concat['Presupuesto'] = df_concat['Presupuesto'].fillna(0)
    
    df_sucursales['branch_office_id'] = df_sucursales['branch_office_id'].astype(int)
    df_concat = pd.merge(df_concat, df_sucursales, on='branch_office_id', how='left')
    
    # Crear columnas renombradas para mejor visualización
    df_concat['Ingresos_2025'] = df_concat['ingresos_neto_2025']  
    df_concat['Ingresos_2024'] = df_concat['ingresos_neto_2024']
    df_concat['Ingresos_SSS_2025'] = df_concat['ingresos_sss_2025']
    df_concat['Ingresos_SSS_2024'] = df_concat['ingresos_sss_2024']

    # FILTROS EN EL SIDEBAR MEJORADOS
    st.sidebar.markdown("### 🎛️ Filtros de Análisis")
    
    # Selector de período de análisis
    st.sidebar.markdown("#### 📅 Período de Análisis")
    date_range = st.sidebar.date_input(
        "Seleccionar rango de fechas",
        value=(datetime.now() - timedelta(days=30), datetime.now()),
        help="Selecciona el período que deseas analizar"
    )
    
    # Filtros existentes mejorados
    responsables = df_sucursales['responsable'].unique().tolist()
    responsables.insert(0, 'Todos')
    
    st.sidebar.markdown("#### 👤 Responsables")
    selected_responsable = st.sidebar.multiselect(
        'Selecciona responsables:', 
        responsables, 
        default='Todos',
        help="Filtra por responsable de sucursal"
    )

    # Filtrar los datos según el responsable seleccionado
    if selected_responsable == ['Todos']:
        df_filtered = df_concat
    else:
        df_filtered = df_concat[df_concat['responsable'].isin(selected_responsable)]

    # Filtro de sucursales
    branch_office_list = df_filtered['branch_office'].unique().tolist()
    branch_office_list.insert(0, 'Todos')

    st.sidebar.markdown("#### 🏢 Sucursales")
    selected_branch_office = st.sidebar.multiselect(
        'Selecciona sucursales:', 
        branch_office_list, 
        default='Todos',
        help="Filtra por sucursal específica"
    )

    # Filtrar los datos según la branch_office seleccionada
    if selected_branch_office == ['Todos']:
        df_filtered = df_filtered
    else:
        df_filtered = df_filtered[df_filtered['branch_office'].isin(selected_branch_office)]

    # Actualizar el DataFrame df_concat_show
    columns_to_show = ['fecha', 'branch_office', 'responsable', 'Ingresos_2025', 'Ingresos_2024', 'Ingresos_SSS_2025', 'Ingresos_SSS_2024', 'Presupuesto', 'ticket_number_2025', 'ticket_number_2024']
    df_concat_show = df_filtered.reindex(columns=columns_to_show)

    # Convertir la columna 'fecha' a datetime si no lo está ya
    df_concat_show['fecha'] = pd.to_datetime(df_concat_show['fecha'])

    # Aplicar el filtro de fechas
    start_date, end_date = date_range
    df_concat_show = df_concat_show[(df_concat_show['fecha'] >= pd.to_datetime(start_date)) &
                                    (df_concat_show['fecha'] <= pd.to_datetime(end_date))]

    # TABLA AGRUPADOS (mantener lógica original)
    df_grupo_total = df_concat_show.groupby(['branch_office'])[['Ingresos_2025', 'Ingresos_2024', 'Presupuesto','Ingresos_SSS_2025', 'Ingresos_SSS_2024', 'ticket_number_2025', 'ticket_number_2024']].sum().reset_index()
    df_grupo_total['Variacion'] = df_grupo_total.apply(lambda row: calcular_variacion(pd.DataFrame({'Ingresos_SSS_2025': [row['Ingresos_SSS_2025']], 'Ingresos_SSS_2024': [row['Ingresos_SSS_2024']]}), 'Ingresos_SSS_2025', 'Ingresos_SSS_2024'), axis=1)
    df_grupo_total['Desviacion'] = df_grupo_total.apply(lambda row: calcular_variacion(pd.DataFrame({'Ingresos_2025': [row['Ingresos_2025']], 'Presupuesto': [row['Presupuesto']]}), 'Ingresos_2025', 'Presupuesto'), axis=1)
    df_grupo_total['Ticket Promedio'] = df_grupo_total.apply(lambda row: calcular_ticket_promedio(pd.DataFrame({'Ingresos_2025': [row['Ingresos_2025']], 'ticket_number_2025': [row['ticket_number_2025']]}), 'Ingresos_2025', 'ticket_number_2025'), axis=1)
    
    # Agregar fila de totales
    totales = df_grupo_total[['branch_office', 'Ingresos_2025', 'Ingresos_2024', 'Presupuesto', 'Ingresos_SSS_2025', 'Ingresos_SSS_2024', 'ticket_number_2025', 'ticket_number_2024']].sum()
    fila_total = [None] * len(df_grupo_total.columns)
    fila_total[df_grupo_total.columns.get_loc('branch_office')] = 'Total'
    fila_total[df_grupo_total.columns.get_loc('Ingresos_2025')] = totales['Ingresos_2025']
    fila_total[df_grupo_total.columns.get_loc('Ingresos_2024')] = totales['Ingresos_2024']
    fila_total[df_grupo_total.columns.get_loc('Variacion')] = calcular_variacion_total(df_grupo_total, 'Ingresos_SSS_2025', 'Ingresos_SSS_2024')
    fila_total[df_grupo_total.columns.get_loc('Presupuesto')] = totales['Presupuesto']
    fila_total[df_grupo_total.columns.get_loc('Desviacion')] = calcular_variacion_total(df_grupo_total, 'Ingresos_2025', 'Presupuesto')
    fila_total[df_grupo_total.columns.get_loc('ticket_number_2025')] = totales['ticket_number_2025']
    fila_total[df_grupo_total.columns.get_loc('ticket_number_2024')] = totales['ticket_number_2024']
    fila_total[df_grupo_total.columns.get_loc('Ticket Promedio')] = calcular_ticket_total(df_grupo_total, 'Ingresos_2025', 'ticket_number_2025')
    
    df_grupo_total.loc['Totales'] = fila_total
    df_grupo_total = df_grupo_total.set_index('branch_office')[['Ingresos_2025', 'Ingresos_2024', 'Variacion', 'Presupuesto', 'Desviacion', 'ticket_number_2025', 'ticket_number_2024', 'Ticket Promedio']]

    
    
    # ==================== DASHBOARD PRINCIPAL ====================
    
    # Calcular indicadores de performance
    indicators = calculate_performance_indicators(df_grupo_total)
    
    # SECCIÓN DE ALERTAS Y RESUMEN EJECUTIVO
    st.markdown('<div class="section-header">📈 RESUMEN EJECUTIVO</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        growth_class = "alert-success" if indicators['growth_rate'] > 0 else "alert-danger" if indicators['growth_rate'] < -5 else "alert-warning"
        st.markdown(f"""
        <div class="alert-box {growth_class}">
            <strong>Crecimiento vs 2024:</strong> {indicators['growth_rate']:.2f}%<br>
            {'📈 Excelente performance' if indicators['growth_rate'] > 10 else 
             '📊 Crecimiento moderado' if indicators['growth_rate'] > 0 else 
             '⚠️ Requiere atención'}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        budget_class = "alert-success" if indicators['budget_achievement'] >= 100 else "alert-warning" if indicators['budget_achievement'] >= 90 else "alert-danger"
        st.markdown(f"""
        <div class="alert-box {budget_class}">
            <strong>Cumplimiento Presupuesto:</strong> {indicators['budget_achievement']:.1f}%<br>
            {'🎯 Meta alcanzada' if indicators['budget_achievement'] >= 100 else 
             '⚠️ Cerca de la meta' if indicators['budget_achievement'] >= 90 else 
             '🚨 Por debajo de meta'}
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_performance = indicators['avg_per_branch']
        st.markdown(f"""
        <div class="alert-box alert-success">
            <strong>Productividad Promedio:</strong><br>
            ${avg_performance:,.0f} por sucursal<br>
            🏢 {indicators['total_branches']} sucursales activas
        </div>
        """, unsafe_allow_html=True)

    # TARJETAS DE MÉTRICAS PRINCIPALES MEJORADAS
    st.markdown('<div class="section-header">💰 MÉTRICAS CLAVE</div>', unsafe_allow_html=True)
    
    total_2025 = df_grupo_total['Ingresos_2025'].iloc[-1] if not df_grupo_total.empty else 0
    total_2024 = df_grupo_total['Ingresos_2024'].iloc[-1] if not df_grupo_total.empty else 0
    total_budget = df_grupo_total['Presupuesto'].iloc[-1] if not df_grupo_total.empty else 0
    var_sss = df_grupo_total['Variacion'].iloc[-1] if not df_grupo_total.empty else "0%"
    desviacion = df_grupo_total['Desviacion'].iloc[-1] if not df_grupo_total.empty else "0%"
    ticket_prom = df_grupo_total['Ticket Promedio'].iloc[-1] if not df_grupo_total.empty else 0
    
    # Tendencias
    growth_trend = f"{'📈' if indicators['growth_rate'] > 0 else '📉'} {indicators['growth_rate']:+.1f}% vs 2024"
    budget_trend = f"{'✅' if indicators['budget_achievement'] >= 100 else '⏳'} {indicators['budget_achievement']:.1f}% cumplimiento"
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(create_enhanced_card(
            "Ingresos 2025", f"${total_2025:,.0f}", "💰", "metric-card-blue",
            "Ingresos totales año actual", growth_trend
        ), unsafe_allow_html=True)
        
    with col2:
        st.markdown(create_enhanced_card(
            "Presupuesto 2025", f"${total_budget:,.0f}", "🎯", "metric-card-green",
            "Meta establecida", budget_trend
        ), unsafe_allow_html=True)
        
    with col3:
        st.markdown(create_enhanced_card(
            "Variación SSS", str(var_sss), "📊", "metric-card-orange",
            "Same Store Sales", f"vs período anterior"
        ), unsafe_allow_html=True)
        
    with col4:
        st.markdown(create_enhanced_card(
            "Ticket Promedio", f"${ticket_prom:,.0f}", "🧾", "metric-card-purple",
            "Valor promedio por transacción", f"{df_grupo_total['ticket_number_2025'].iloc[-1]:,.0f} transacciones"
        ), unsafe_allow_html=True)
        
        
    # Gráfico de Tendencias
    fig_tendencias = px.line(
        df_concat_show,
        x='fecha',
        y=['Ingresos_2025', 'Ingresos_2024'],
        title='Tendencias de Ingresos 2024 vs 2025',
        labels={'value': 'Ingresos', 'variable': 'Año'},
        color_discrete_map={'Ingresos_2025': '#1f77b4', 'Ingresos_2024': '#ff7f0e'}
    )

    # Gráfico de Tendencias 2
    fig_tendencias2 = px.line(
        df_concat_show,
        x='fecha',
        y=['ticket_number_2025', 'ticket_number_2024'],
        title='Número de Tickets 2024 vs 2025',
        labels={'value': 'Número de Tickets', 'variable': 'Año'},
        color_discrete_map={'ticket_number_2025': '#1f77b4', 'ticket_number_2024': '#ff7f0e'}
    )

    # Gráfico por Sucursal
    fig_branches = px.bar(
        df_grupo_total.reset_index(),
        x='branch_office',
        y=['Ingresos_2025', 'Ingresos_2024'],
        title='Ingresos por Sucursal',
        labels={'value': 'Ingresos', 'variable': 'Año', 'branch_office': 'Sucursal'},
        barmode='group',
        color_discrete_map={'Ingresos_2025': '#1f77b4', 'Ingresos_2024': '#ff7f0e'}
    )

    # Gráfico de Métodos de Pago
    # Asegúrate de tener las columnas 'efectivo_2025', 'tarjeta_2025', etc., en tu DataFrame
    fig_payments = px.pie(
        df_concat_show,
        names=['Efectivo', 'Tarjeta'],
        values=['efectivo_2025', 'tarjeta_2025'],
        title='Distribución de Métodos de Pago 2025'
    )

    # Gráfico Comparativo
    fig_comparatives = px.bar(
        df_grupo_total.reset_index(),
        x='branch_office',
        y=['Variacion', 'Desviacion'],
        title='Variación y Desviación por Sucursal',
        labels={'value': 'Porcentaje', 'variable': 'Métrica', 'branch_office': 'Sucursal'},
        barmode='group',
        color_discrete_map={'Variacion': '#1f77b4', 'Desviacion': '#ff7f0e'}
    )

    # Gráficos Temporales
    fig_temporal = px.line(
        df_concat_show,
        x='fecha',
        y='Ingresos_SSS_2025',
        title='Ingresos SSS 2025'
    )

    fig_temporal2 = px.line(
        df_concat_show,
        x='fecha',
        y='Ingresos_SSS_2024',
        title='Ingresos SSS 2024'
    )

    fig_temporal3 = px.line(
        df_concat_show,
        x='fecha',
        y='ticket_number_2025',
        title='Número de Tickets 2025'
    )

    fig_temporal4 = px.line(
        df_concat_show,
        x='fecha',
        y='ticket_number_2024',
        title='Número de Tickets 2024'
    )

    fig_temporal5 = px.line(
        df_concat_show,
        x='fecha',
        y='Presupuesto',
        title='Presupuesto 2025'
    )

    fig_temporal6 = px.line(
        df_concat_show,
        x='fecha',
        y='Ingresos_2025',
        title='Ingresos vs Presupuesto 2025'
    )



    # SECCIÓN DE GRÁFICOS AVANZADOS
    st.markdown('<div class="section-header">📊 ANÁLISIS VISUAL AVANZADO</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Tendencias", "🏢 Por Sucursal", "💳 Métodos de Pago", "📊 Comparativas"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Gráfico de tendencias mejorado
            st.plotly_chart(fig_tendencias, use_container_width=True)
        
        with col2:
            # Gráfico de tendencias mejorado
            st.plotly_chart(fig_tendencias2, use_container_width=True)

    with tab2:
        st.plotly_chart(fig_branches, use_container_width=True)
        
    with tab3:
        st.plotly_chart(fig_payments, use_container_width=True)
        
    with tab4:
        st.plotly_chart(fig_comparatives, use_container_width=True)
        
    # SECCIÓN DE GRÁFICOS SIMPLES
    st.markdown('<div class="section-header">📊 GRÁFICOS SIMPLES</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(fig_temporal, use_container_width=True)
        
    with col2:
        st.plotly_chart(fig_temporal2, use_container_width=True)
        
    # SECCIÓN DE GRÁFICOS SIMPLES 2
    st.markdown('<div class="section-header">📊 GRÁFICOS SIMPLES 2</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(fig_temporal3, use_container_width=True)
        
    with col2:
        st.plotly_chart(fig_temporal4, use_container_width=True)
        
    # SECCIÓN DE GRÁFICOS SIMPLES 3
    st.markdown('<div class="section-header">📊 GRÁFICOS SIMPLES 3</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(fig_temporal5, use_container_width=True)
        
    with col2:
        st.plotly_chart(fig_temporal6, use_container_width=True)
        
# Llamar a la función principal para mostrar el informe
display_informe_ventas()
