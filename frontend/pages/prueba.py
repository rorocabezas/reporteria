# pages/ventas.py respaldo
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from menu import generarMenu
from utils import format_currency, format_percentage
import warnings
import numpy as np
from datetime import datetime, timedelta
import calendar

warnings.filterwarnings('ignore')

# Configuración de página
st.set_page_config(
    page_title="Dashboard Ventas Avanzado",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# CSS personalizado para mejorar la UI
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
    }
    .metric-card-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-card-green {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
        margin: 0.5rem 0;
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
</style>
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
    except Exception as e:
        st.error(f"❌ Error al cargar datos de {endpoint}: {e}")
        return pd.DataFrame()

# Función para procesar y limpiar datos de ingresos
def process_sales_data(df_ingresos, df_sucursales, df_periodos):
    """
    Procesa los datos de ingresos agregando información de sucursales.
    """
    if df_ingresos.empty:
        return df_ingresos

    # Agregar información de sucursales si está disponible
    if not df_sucursales.empty and 'branch_office' in df_sucursales.columns:
        # Intentar hacer merge con la información de sucursales usando branch_office_id en ambos DataFrames
        if 'branch_office_id' in df_ingresos.columns and 'branch_office_id' in df_sucursales.columns:
            df_ingresos = df_ingresos.merge(
                df_sucursales,
                left_on='branch_office_id',
                right_on='branch_office_id',
                how='left'
            )

    # Asegurar que tenemos la columna branch_office
    if 'branch_office' not in df_ingresos.columns:
        # Si no hay columna branch_office, crear una genérica
        df_ingresos['branch_office'] = 'sucursal ' + df_ingresos['branch_office_id'].astype(str)

    # Asegurar que la columna responsable exista después del merge
    if 'responsable' not in df_ingresos.columns and 'responsable' in df_sucursales.columns:
        # Si responsable no está en df_ingresos pero sí en df_sucursales, se añade desde df_sucursales
        df_ingresos['responsable'] = df_ingresos['branch_office_id'].map(
            df_sucursales.set_index('branch_office_id')['responsable']
        )

    # Si aún no existe la columna responsable, crear responsables genéricos basados en sucursal
    if 'responsable' not in df_ingresos.columns:
        unique_sucursales = df_ingresos['branch_office'].unique()
        responsable_map = {suc: f"Responsable {i+1}" for i, suc in enumerate(unique_sucursales)}
        df_ingresos['responsable'] = df_ingresos['branch_office'].map(responsable_map)

    return df_ingresos


# Cargar y procesar datos
@st.cache_data(ttl=600)
def load_and_process_data():
    # Cargar datos desde los endpoints
    df_ingresos = fetch_data_from_endpoint("ingresos_acum_dia")
    df_ppto = fetch_data_from_endpoint("ingresos_acum_dia_ppto")
    df_sucursales = fetch_data_from_endpoint("sucursales")
    df_periodos = fetch_data_from_endpoint("periodos")

    # Verifica si df_ingresos está vacío y muestra un mensaje de error si es así
    if df_ingresos.empty:
        st.error("❌ No se pudieron cargar los datos de ingresos desde la API.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # Mostrar información de debug en un expander de Streamlit
    with st.expander("🔍 Información de Debug de los Datos"):
        st.write("**Columnas en df_ingresos:**", list(df_ingresos.columns))
        st.write("**Muestra de datos de ingresos:**")
        st.write(df_ingresos.head())

        if not df_ppto.empty:
            st.write("**Columnas en df_ppto:**", list(df_ppto.columns))
            st.write("**Muestra de datos de presupuesto:**")
            st.write(df_ppto.head())

        if not df_sucursales.empty:
            st.write("**Columnas en df_sucursales:**", list(df_sucursales.columns))
            st.write("**Datos de sucursales:**")
            st.write(df_sucursales)

    # Procesar datos de ingresos utilizando la función process_sales_data
    df_ingresos_processed = process_sales_data(df_ingresos, df_sucursales, df_periodos)

    # Asegurar que tenemos la columna año
    if 'año' not in df_ingresos_processed.columns:
        # Crear la columna 'año' con el año actual por defecto si no existe
        current_year = pd.Timestamp.now().year
        df_ingresos_processed['año'] = current_year
        st.warning("⚠️ No se encontró columna de año. Usando año actual por defecto.")
    else:
        # Convertir la columna 'año' a tipo entero si existe
        df_ingresos_processed['año'] = df_ingresos_processed['año'].astype(int)

  

    # Crear la columna 'mes' si no existe, usando 'periodo' si está disponible
    if 'mes' not in df_ingresos_processed.columns:
        if 'periodo' in df_ingresos_processed.columns:
            # Usar la columna 'periodo' como 'mes'
            df_ingresos_processed['mes'] = df_ingresos_processed['periodo']
        elif 'fecha' in df_ingresos_processed.columns:
            # Convertir la columna 'fecha' a tipo datetime y extraer el mes
            df_ingresos_processed['fecha'] = pd.to_datetime(df_ingresos_processed['fecha'])
            df_ingresos_processed['mes'] = df_ingresos_processed['fecha'].dt.month
        else:
            # Usar el mes actual si no hay columna 'fecha' ni 'periodo'
            df_ingresos_processed['mes'] = pd.Timestamp.now().month

    # Obtener el año actual
    current_year = pd.Timestamp.now().year

    # Filtrar los datos por año actual y año anterior
    df_ingresos_current = df_ingresos_processed[df_ingresos_processed['año'] == current_year]
    df_ingresos_previous = df_ingresos_processed[df_ingresos_processed['año'] == current_year - 1]

    # Si no hay datos del año anterior, crear un DataFrame vacío con las mismas columnas
    if df_ingresos_previous.empty:
        df_ingresos_previous = pd.DataFrame(columns=df_ingresos_current.columns)
        st.warning(f"⚠️ No se encontraron datos para el año {current_year - 1}")

    # Retornar los DataFrames de ingresos para el año actual, año anterior y el DataFrame de presupuesto
    return df_ingresos_current, df_ingresos_previous, df_ppto



# Header del dashboard
st.markdown("""
<div class='main-header'>
    <h1>📊 Dashboard de Ventas Avanzado</h1>
    <h3>Análisis Comparativo Año Actual vs Año Anterior</h3>
</div>
""", unsafe_allow_html=True)

# Cargar datos
df_current, df_previous, df_budget = load_and_process_data()

if df_current.empty:
    st.error("❌ No se pudieron cargar los datos correctamente.")
    st.stop()

# Detectar la columna de ventas automáticamente
ventas_columns = [col for col in df_current.columns if any(keyword in col.lower() for keyword in ['venta', 'ingreso', 'monto', 'total', 'importe'])]
if ventas_columns:
    ventas_column = ventas_columns[0]
else:
    # Si no se encuentra, usar la primera columna numérica
    numeric_cols = df_current.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        ventas_column = numeric_cols[0]
    else:
        st.error("❌ No se encontró una columna numérica para las ventas.")
        st.stop()

st.info(f"📊 Usando la columna '{ventas_column}' como métrica de ventas.")

st.write(df_current.head())
# Sidebar con filtros
with st.sidebar:
    st.markdown("### 🎛️ Filtros de Análisis")

    # Filtro por sucursal
    sucursales_disponibles = sorted(df_current['branch_office'].unique())
    sucursal_selected = st.multiselect(
        "🏢 Seleccionar Sucursales:",
        options=sucursales_disponibles,
        default=sucursales_disponibles,
        help="Selecciona las sucursales a analizar"
    )

    # Filtro por responsable si existe la columna
    if 'responsable' in df_current.columns:
        responsables_disponibles = sorted(df_current['responsable'].unique())
        responsable_selected = st.multiselect(
            "👤 Seleccionar Responsables:",
            options=responsables_disponibles,
            default=responsables_disponibles,
            help="Selecciona los responsables a analizar"
        )
    else:
        responsable_selected = []

    # Filtro por período (meses)
    if 'periodo' in df_current.columns:
        # Obtener los valores únicos disponibles en la columna 'periodo' y ordenarlos
        periodos_disponibles = sorted(df_current['periodo'].unique())

        # Crear un widget de selección múltiple en Streamlit para seleccionar los períodos
        periodos_selected = st.multiselect(
            "📅 Seleccionar Períodos:",  # Etiqueta del widget
            options=periodos_disponibles,  # Opciones disponibles para seleccionar
            default=periodos_disponibles,  # Opciones seleccionadas por defecto
            help="Selecciona los períodos a analizar"  # Texto de ayuda para el usuario
        )
    else:
        # Si no hay columna 'periodo', asignar una lista vacía a periodos_selected
        periodos_selected = []

# Aplicar filtros
if sucursal_selected:
    df_current_filtered = df_current[df_current['branch_office'].isin(sucursal_selected)]
    df_previous_filtered = df_previous[df_previous['branch_office'].isin(sucursal_selected)]
else:
    df_current_filtered = df_current
    df_previous_filtered = df_previous

if responsable_selected and 'responsable' in df_current.columns:
    df_current_filtered = df_current_filtered[df_current_filtered['responsable'].isin(responsable_selected)]
    df_previous_filtered = df_previous_filtered[df_previous_filtered['responsable'].isin(responsable_selected)]

if periodos_selected and 'periodo' in df_current.columns:
    df_current_filtered = df_current_filtered[df_current_filtered['periodo'].isin(periodos_selected)]
    df_previous_filtered = df_previous_filtered[df_previous_filtered['periodo'].isin(periodos_selected)]

if df_current_filtered.empty or df_previous_filtered.empty:
    st.error("❌ No se encontraron datos para los filtros seleccionados.")
    st.stop()

# Calcular métricas principales
current_year = datetime.now().year

total_ventas_current = df_current[ventas_column].sum()
total_ventas_previous = df_previous[ventas_column].sum() if not df_previous.empty else 0
crecimiento = ((total_ventas_current - total_ventas_previous) / total_ventas_previous) * 100 if total_ventas_previous > 0 else 0

# Calcular promedios mensuales
if 'periodo' in df_current.columns and not df_current.empty:
    promedio_mensual_current = df_current.groupby('periodo')[ventas_column].sum().mean()
else:
    promedio_mensual_current = total_ventas_current / 12

if 'periodo' in df_previous.columns and not df_previous.empty:
    promedio_mensual_previous = df_previous.groupby('periodo')[ventas_column].sum().mean()
else:
    promedio_mensual_previous = total_ventas_previous / 12

# Encontrar la mejor sucursal
if not df_current.empty:
    mejor_sucursal = df_current.groupby('branch_office')[ventas_column].sum().idxmax()
else:
    mejor_sucursal = "N/A"

# Métricas principales
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class='metric-card'>
        <h3>💰 Ventas {current_year}</h3>
        <h2>${total_ventas_current:,.0f}</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class='metric-card-blue'>
        <h3>📈 Crecimiento</h3>
        <h2>{crecimiento:+.1f}%</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class='metric-card-green'>
        <h3>📅 Promedio Mensual</h3>
        <h2>${promedio_mensual_current:,.0f}</h2>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class='metric-card-orange'>
        <h3>🏆 Mejor Sucursal</h3>
        <h2>{mejor_sucursal}</h2>
    </div>
    """, unsafe_allow_html=True)

# Mostrar información sobre presupuesto si está disponible
if not df_budget.empty:
    col1, col2 = st.columns(2)
    with col1:
        total_presupuesto = df_budget[ventas_column].sum() if ventas_column in df_budget.columns else 0
        if total_presupuesto > 0:
            cumplimiento = (total_ventas_current / total_presupuesto) * 100
            st.markdown(f"""
            <div class='alert-box alert-{"success" if cumplimiento >= 100 else "warning"}'>
                <h4>🎯 Cumplimiento de Presupuesto</h4>
                <p><strong>Presupuesto:</strong> ${total_presupuesto:,.0f}</p>
                <p><strong>Realizado:</strong> ${total_ventas_current:,.0f}</p>
                <p><strong>Cumplimiento:</strong> {cumplimiento:.1f}%</p>
            </div>
            """, unsafe_allow_html=True)

# Tabs para diferentes análisis
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Análisis General", "🏢 Por Sucursal", "👤 Por Responsable", "📅 Tendencias", "📋 Datos Detallados"])

with tab1:
    st.markdown("### 📊 Análisis Comparativo General")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de comparación anual
        fig_comparison = go.Figure()
        
        fig_comparison.add_trace(go.Bar(
            name=f'Año {current_year-1}',
            x=['Ventas Totales'],
            y=[total_ventas_previous],
            marker_color='lightblue'
        ))
        
        fig_comparison.add_trace(go.Bar(
            name=f'Año {current_year}',
            x=['Ventas Totales'],
            y=[total_ventas_current],
            marker_color='darkblue'
        ))
        
        fig_comparison.update_layout(
            title="Comparación de Ventas Anuales",
            yaxis_title="Ventas ($)",
            barmode='group',
            height=400
        )
        st.plotly_chart(fig_comparison, use_container_width=True)
    
    with col2:
        # Gráfico de crecimiento por sucursal
        if not df_current_filtered.empty:
            ventas_por_sucursal_current = df_current_filtered.groupby('branch_office')[ventas_column].sum()
            
            if not df_previous_filtered.empty:
                ventas_por_sucursal_previous = df_previous_filtered.groupby('branch_office')[ventas_column].sum()
                
                crecimiento_por_sucursal = []
                sucursales_labels = []
                for sucursal in ventas_por_sucursal_current.index:
                    if sucursal in ventas_por_sucursal_previous.index and ventas_por_sucursal_previous[sucursal] > 0:
                        crecimiento_suc = ((ventas_por_sucursal_current[sucursal] - ventas_por_sucursal_previous[sucursal]) 
                                         / ventas_por_sucursal_previous[sucursal]) * 100
                        crecimiento_por_sucursal.append(crecimiento_suc)
                        sucursales_labels.append(sucursal)
                
                if crecimiento_por_sucursal:
                    fig_growth = px.bar(
                        x=sucursales_labels,
                        y=crecimiento_por_sucursal,
                        title="Crecimiento por Sucursal (%)",
                        labels={'x': 'Sucursal', 'y': 'Crecimiento (%)'},
                        color=crecimiento_por_sucursal,
                        color_continuous_scale='RdYlGn'
                    )
                    fig_growth.update_layout(height=400)
                    st.plotly_chart(fig_growth, use_container_width=True)
                else:
                    st.info("📊 No hay datos suficientes para calcular el crecimiento por sucursal")
            else:
                # Mostrar solo ventas actuales si no hay datos anteriores
                fig_current_only = px.bar(
                    x=ventas_por_sucursal_current.index,
                    y=ventas_por_sucursal_current.values,
                    title="Ventas por Sucursal (Año Actual)",
                    labels={'x': 'Sucursal', 'y': 'Ventas ($)'},
                    color=ventas_por_sucursal_current.values,
                    color_continuous_scale='Blues'
                )
                fig_current_only.update_layout(height=400)
                st.plotly_chart(fig_current_only, use_container_width=True)

with tab2:
    st.markdown("### 🏢 Análisis por Sucursal")
    
    # Ventas por sucursal - comparativo
    ventas_por_sucursal_current = df_current_filtered.groupby('branch_office')[ventas_column].sum().reset_index()
    ventas_por_sucursal_previous = df_previous_filtered.groupby('branch_office')[ventas_column].sum().reset_index()
    
    fig_sucursal = go.Figure()
    
    fig_sucursal.add_trace(go.Bar(
        name=f'Año {current_year-1}',
        x=ventas_por_sucursal_previous['branch_office'],
        y=ventas_por_sucursal_previous[ventas_column],
        marker_color='lightcoral'
    ))
    
    fig_sucursal.add_trace(go.Bar(
        name=f'Año {current_year}',
        x=ventas_por_sucursal_current['branch_office'],
        y=ventas_por_sucursal_current[ventas_column],
        marker_color='steelblue'
    ))
    
    fig_sucursal.update_layout(
        title="Ventas por Sucursal - Comparativo",
        xaxis_title="Sucursal",
        yaxis_title="Ventas ($)",
        barmode='group',
        height=500
    )
    st.plotly_chart(fig_sucursal, use_container_width=True)
    
    # Tabla de ranking de sucursales
    st.markdown("#### 🏆 Ranking de Sucursales")
    ranking_data = []
    for sucursal in ventas_por_sucursal_current['branch_office']:
        current_sales = ventas_por_sucursal_current[ventas_por_sucursal_current['branch_office'] == sucursal][ventas_column].iloc[0]
        previous_sales = ventas_por_sucursal_previous[ventas_por_sucursal_previous['branch_office'] == sucursal][ventas_column].iloc[0] if sucursal in ventas_por_sucursal_previous['branch_office'].values else 0
        growth = ((current_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
        
        ranking_data.append({
            'Sucursal': sucursal,
            f'Ventas {current_year}': f"${current_sales:,.0f}",
            f'Ventas {current_year-1}': f"${previous_sales:,.0f}",
            'Crecimiento (%)': f"{growth:+.1f}%"
        })
    
    ranking_df = pd.DataFrame(ranking_data)
    st.dataframe(ranking_df, use_container_width=True)

with tab3:
    if 'responsable' in df_current_filtered.columns:
        st.markdown("### 👤 Análisis por Responsable")
        
        # Ventas por responsable
        ventas_por_responsable_current = df_current_filtered.groupby('responsable')[ventas_column].sum().reset_index()
        ventas_por_responsable_previous = df_previous_filtered.groupby('responsable')[ventas_column].sum().reset_index()
        
        # Gráfico de dona
        fig_dona = px.pie(
            ventas_por_responsable_current, 
            values=ventas_column, 
            names='responsable',
            title=f"Distribución de Ventas por Responsable - {current_year}",
            hole=0.4
        )
        fig_dona.update_layout(height=500)
        st.plotly_chart(fig_dona, use_container_width=True)
        
        # Comparativo por responsable
        col1, col2 = st.columns(2)
        
        with col1:
            fig_resp_comp = go.Figure()
            
            fig_resp_comp.add_trace(go.Bar(
                name=f'Año {current_year-1}',
                x=ventas_por_responsable_previous['responsable'],
                y=ventas_por_responsable_previous[ventas_column],
                marker_color='lightgreen'
            ))
            
            fig_resp_comp.add_trace(go.Bar(
                name=f'Año {current_year}',
                x=ventas_por_responsable_current['responsable'],
                y=ventas_por_responsable_current[ventas_column],
                marker_color='darkgreen'
            ))
            
            fig_resp_comp.update_layout(
                title="Ventas por Responsable - Comparativo",
                xaxis_title="Responsable",
                yaxis_title="Ventas ($)",
                barmode='group',
                height=400
            )
            st.plotly_chart(fig_resp_comp, use_container_width=True)
        
        with col2:
            # Top performers
            st.markdown("#### 🌟 Top Performers")
            top_performers = ventas_por_responsable_current.nlargest(5, ventas_column)
            for i, (_, row) in enumerate(top_performers.iterrows(), 1):
                st.markdown(f"**{i}. {row['responsable']}**: ${row[ventas_column]:,.0f}")
    else:
        st.info("📝 No hay datos de responsables disponibles en el dataset actual.")

with tab4:
    st.markdown("### 📅 Análisis de Tendencias")
    
  
    
    if 'mes' in df_current_filtered.columns:
        # Tendencia mensual
        ventas_mensual_current = df_current_filtered.groupby('mes')[ventas_column].sum().reset_index()
        ventas_mensual_previous = df_previous_filtered.groupby('mes')[ventas_column].sum().reset_index()
        
     
        fig_tendencia = go.Figure()
        
        fig_tendencia.add_trace(go.Scatter(
            x=ventas_mensual_previous['periodo'],  # Usar directamente los valores de la columna 'periodo'
            y=ventas_mensual_previous[ventas_column],
            mode='lines+markers',
            name=f'Año {current_year-1}',
            line=dict(color='red', width=3)
        ))

        fig_tendencia.add_trace(go.Scatter(
            x=[calendar.month_name[m] for m in ventas_mensual_current['periodo']],
            y=ventas_mensual_current[ventas_column],
            mode='lines+markers',
            name=f'Año {current_year}',
            line=dict(color='blue', width=3)
        ))
        
        fig_tendencia.update_layout(
            title="Tendencia de Ventas Mensuales",
            xaxis_title="Mes",
            yaxis_title="Ventas ($)",
            height=500,
            hovermode='x unified'
        )
        st.plotly_chart(fig_tendencia, use_container_width=True)
        
        # Análisis de estacionalidad
        col1, col2 = st.columns(2)
        
        with col1:
            # Mejor y peor mes
            mejor_mes_current = ventas_mensual_current.loc[ventas_mensual_current[ventas_column].idxmax(), 'periodo']
            peor_mes_current = ventas_mensual_current.loc[ventas_mensual_current[ventas_column].idxmin(), 'periodo']
            
            st.markdown(f"""
            <div class='alert-box alert-success'>
                <h4>📈 Mejor Mes {current_year}</h4>
                <p><strong>{calendar.month_name[mejor_mes_current]}</strong> con ${ventas_mensual_current[ventas_mensual_current['periodo'] == mejor_mes_current][ventas_column].iloc[0]:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='alert-box alert-warning'>
                <h4>📉 Mes con Menores Ventas {current_year}</h4>
                <p><strong>{calendar.month_name[peor_mes_current]}</strong> con ${ventas_mensual_current[ventas_mensual_current['periodo'] == peor_mes_current][ventas_column].iloc[0]:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Volatilidad
            volatilidad_current = ventas_mensual_current[ventas_column].std()
            volatilidad_previous = ventas_mensual_previous[ventas_column].std()
            
            st.markdown(f"""
            <div class='alert-box alert-success' style='background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);'>
                <h4>📊 Análisis de Volatilidad</h4>
                <p><strong>{current_year}:</strong> ${volatilidad_current:,.0f}</p>
                <p><strong>{current_year-1}:</strong> ${volatilidad_previous:,.0f}</p>
                <p><strong>Cambio:</strong> {((volatilidad_current - volatilidad_previous) / volatilidad_previous * 100):+.1f}%</p>
            </div>
            """, unsafe_allow_html=True)

with tab5:
    st.markdown("### 📋 Datos Detallados")
    
    # Mostrar datos filtrados
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"#### 📊 Datos {current_year}")
        st.dataframe(df_current_filtered, use_container_width=True)
    
    with col2:
        st.markdown(f"#### 📊 Datos {current_year-1}")
        st.dataframe(df_previous_filtered, use_container_width=True)
    
    # Estadísticas descriptivas
    st.markdown("#### 📈 Estadísticas Descriptivas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Año {current_year}:**")
        st.write(df_current_filtered[ventas_column].describe())
    
    with col2:
        st.markdown(f"**Año {current_year-1}:**")
        st.write(df_previous_filtered[ventas_column].describe())

# Footer con información adicional
st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 10px; margin-top: 20px;'>
    <p style='margin: 0; color: #6c757d;'>📊 Dashboard de Ventas - Actualizado automáticamente cada 5 minutos</p>
    <p style='margin: 0; color: #6c757d;'>Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
</div>
""".format(datetime=datetime), unsafe_allow_html=True)