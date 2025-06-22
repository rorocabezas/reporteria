# -*- coding: utf-8 -*-
# pages/dtes.py
import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from menu import generarMenu
from utils import format_currency, format_percentage

# Configuración de página
st.set_page_config(page_title="Dashboard DTEs", layout="wide")

# Generar el menú
generarMenu()

# Título principal con estilo
st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%); border-radius: 10px; margin-bottom: 20px;'>
        <h1 style="color:white; font-size: 3em; margin-bottom: 10px;">
            	🏷️ DTE - Documentos Tributarios Electrónicos
        </h1>        
    </div>
    """, unsafe_allow_html=True)
st.markdown("---")

# Función para obtener datos de un endpoint
@st.cache_data(ttl=300)  # Cache por 5 minutos
def fetch_data_from_endpoint(endpoint, rut=None):
    try:
        if endpoint == "sucursales" and rut:
            # Usar el endpoint sucursales_rut si se proporciona un rut
            response = requests.get(f"http://localhost:8000/sucursales_rut", params={"rut": rut})
        else:
            # Para otros endpoints, usar la URL normal
            response = requests.get(f"http://localhost:8000/{endpoint}")

        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data['data'], columns=data['columns'])
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Error al obtener datos del endpoint {endpoint}: {e}")
        return pd.DataFrame()

# Obtener datos
rut = None
if 'user_info' in st.session_state and 'rut' in st.session_state.user_info:
    rut = st.session_state.user_info['rut']

with st.spinner('Cargando datos...'):
    df_abonados = fetch_data_from_endpoint("abonados")
    st.write(df_abonados)
    df_sucursales = fetch_data_from_endpoint("sucursales", rut=rut)  # Pasar el rut al endpoint de sucursales
    st.write(df_sucursales)
    df_periodos = fetch_data_from_endpoint("periodos")

# Procesar datos
dte_final = df_abonados.merge(df_sucursales, on='branch_office_id', how='left')
dte_final = dte_final.merge(df_periodos, left_on='period', right_on='period', how='left')

# Verificar la fusión
st.write("DataFrame después de la fusión:")
st.write(dte_final[['branch_office_id', 'responsable']].drop_duplicates())

dte_final = dte_final.rename(columns={
    "rut_x": "rut",
    "branch_office": "sucursal",
    "dte_type_id": "tipo",
    "amount": "monto"
})

# Asegúrate de que no hay valores NaN en la columna 'responsable'
dte_final['responsable'] = dte_final['responsable'].fillna('Sin Responsable')

# Verificar la limpieza de datos
st.write("Valores únicos en 'responsable' después de la limpieza:")
st.write(dte_final['responsable'].unique())

dte_final['comment'] = dte_final['comment'].astype(str)
dte_final['contador'] = dte_final['tipo'].apply(lambda x: 1 if x in [33, 39] else 1)
dte_final['link'] = dte_final['comment'].apply(lambda x: 'sí' if 'Código de autorización' in str(x) else 'no')
dte_final['folio'] = dte_final['folio'].astype(str)
ultimo_mes = dte_final['Periodo'].max()

# Columnas a mostrar
columns_to_show = ['rut', 'cliente', 'razon_social', 'folio', 'sucursal', 'responsable', 'tipo', 'status', 'total', 'Periodo', 'Año', 'comment', 'contador', 'link']
df_status_dte = dte_final[columns_to_show]

# Verificar el DataFrame final
st.write("DataFrame final:")
st.write(df_status_dte[['sucursal', 'responsable']].drop_duplicates())

# SIDEBAR - FILTROS
st.sidebar.title('🔍 Filtros Disponibles')
periodos = df_status_dte['Periodo'].unique()

# Obtener responsables únicos sin valores NaN
responsables = df_status_dte['responsable'].unique()
status_options = df_status_dte['status'].unique()

status_seleccionados = st.sidebar.multiselect('📊 Seleccione Status:', status_options, default=status_options)
responsable_seleccionados = st.sidebar.multiselect('👥 Seleccione Responsables:', responsables)

# Obtener sucursales basadas en los responsables seleccionados
if responsable_seleccionados:
    branch_offices = df_status_dte[df_status_dte['responsable'].isin(responsable_seleccionados)]['sucursal'].unique()
else:
    branch_offices = df_status_dte['sucursal'].unique()

branch_office_seleccionadas = st.sidebar.multiselect('🏢 Seleccione Sucursales:', branch_offices)
periodos_seleccionados = st.sidebar.multiselect('📅 Seleccione Periodo:', periodos, default=[ultimo_mes])

# Aplicar filtros
df_filtrado = df_status_dte[
    (df_status_dte['status'].isin(status_seleccionados) if status_seleccionados else True) &
    (df_status_dte['Periodo'].isin(periodos_seleccionados) if periodos_seleccionados else True) &
    (df_status_dte['responsable'].isin(responsable_seleccionados) if responsable_seleccionados else True) &
    (df_status_dte['sucursal'].isin(branch_office_seleccionadas) if branch_office_seleccionadas else True)
]

# MÉTRICAS PRINCIPALES
st.subheader("📈 Métricas Principales")

# Calcular métricas
monto_pagada = df_filtrado[df_filtrado['status'] == 'Imputada Pagada']['total'].sum()
monto_por_pagar = df_filtrado[df_filtrado['status'] == 'Imputada por Pagar']['total'].sum()
cantidad_pagada = df_filtrado[df_filtrado['status'] == 'Imputada Pagada']['contador'].sum()
cantidad_por_pagar = df_filtrado[df_filtrado['status'] == 'Imputada por Pagar']['contador'].sum()    
cantidad_link_si = df_filtrado[df_filtrado['link'] == 'sí']['contador'].sum()
contador_total = df_filtrado['contador'].sum()
monto_total = df_filtrado['total'].sum()

# Mostrar métricas en columnas
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        label="💰 Total DTEs",
        value=f"{contador_total:,}",
        delta=f"{format_currency(monto_total)}"
    )

with col2:
    st.metric(
        label="✅ Pagadas",
        value=f"{cantidad_pagada:,}",
        delta=f"{format_currency(monto_pagada)}"
    )

with col3:
    st.metric(
        label="⏳ Por Pagar",
        value=f"{cantidad_por_pagar:,}",
        delta=f"{format_currency(monto_por_pagar)}"
    )

with col4:
    porc_pagados = (cantidad_pagada / contador_total * 100) if contador_total > 0 else 0
    st.metric(
        label="📊 % Pagadas",
        value=f"{format_percentage(porc_pagados)}"
    )

with col5:
    porc_link = (cantidad_link_si / contador_total * 100) if contador_total > 0 else 0
    st.metric(
        label="🔗 % Con Link",
        value=f"{format_percentage(porc_link)}"
    )

st.markdown("---")

# GRÁFICOS PRINCIPALES
col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Distribución por Status")
    
    # Gráfico de dona - Status
    status_counts = df_filtrado['status'].value_counts()
    status_amounts = df_filtrado.groupby('status')['total'].sum()
    
    fig_status = go.Figure(data=[go.Pie(
        labels=status_counts.index,
        values=status_counts.values,
        hole=.3,
        textinfo='label+percent',
        textposition='outside'
    )])
    
    fig_status.update_layout(
        title="Cantidad de DTEs por Status",
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig_status, use_container_width=True)

with col2:
    st.subheader("💹 Montos por Status")
    
    # Gráfico de barras - Montos por Status
    fig_montos = px.bar(
        x=status_amounts.index,
        y=status_amounts.values,
        title="Montos Totales por Status",
        labels={'x': 'Status', 'y': 'Monto Total'},
        color=status_amounts.values,
        color_continuous_scale='Blues'
    )
    
    fig_montos.update_layout(height=400)
    st.plotly_chart(fig_montos, use_container_width=True)

# ANÁLISIS POR PERÍODO Y SUCURSAL
st.markdown("---")
st.subheader("📈 Análisis Temporal y Geográfico")

col1, col2 = st.columns(2)

with col1:
    # Evolución por período
    st.subheader("📅 Evolución por Período")
    
    periodo_analysis = df_filtrado.groupby(['Periodo', 'status']).agg({
        'contador': 'sum',
        'total': 'sum'
    }).reset_index()
    
    fig_periodo = px.line(
        periodo_analysis, 
        x='Periodo', 
        y='contador', 
        color='status',
        title="Evolución de DTEs por Período",
        markers=True
    )
    
    fig_periodo.update_layout(height=400)
    st.plotly_chart(fig_periodo, use_container_width=True)

with col2:
    # Top sucursales
    st.subheader("🏢 Top 10 Sucursales")
    
    sucursal_analysis = df_filtrado.groupby('sucursal').agg({
        'contador': 'sum',
        'total': 'sum'
    }).reset_index().sort_values('total', ascending=False).head(10)
    
    fig_sucursales = px.bar(
        sucursal_analysis,
        x='contador',
        y='sucursal',
        orientation='h',
        title="Top 10 Sucursales por Cantidad de DTEs",
        color='total',
        color_continuous_scale='Viridis'
    )
    
    fig_sucursales.update_layout(height=400)
    st.plotly_chart(fig_sucursales, use_container_width=True)

# ANÁLISIS POR RESPONSABLE
if responsable_seleccionados:
    st.markdown("---")
    st.subheader("👥 Análisis por Responsable")
    
    responsable_analysis = df_filtrado.groupby(['responsable', 'status']).agg({
        'contador': 'sum',
        'total': 'sum'
    }).reset_index()
    
    fig_responsables = px.sunburst(
        responsable_analysis,
        path=['responsable', 'status'],
        values='contador',
        title="Distribución de DTEs por Responsable y Status"
    )
    
    fig_responsables.update_layout(height=500)
    st.plotly_chart(fig_responsables, use_container_width=True)

# TABLA DE RESUMEN DETALLADO
st.markdown("---")
st.subheader("📋 Resumen Detallado")

# Crear tabs para diferentes vistas
tab1, tab2, tab3 = st.tabs(["📊 Resumen por Sucursal", "👥 Resumen por Responsable", "📅 Resumen por Período"])

with tab1:
    resumen_sucursal = df_filtrado.groupby('sucursal').agg({
        'contador': 'sum',
        'total': ['sum', 'mean'],
        'status': lambda x: x.value_counts().to_dict()
    }).round(2)
    
    # Aplanar columnas multinivel
    resumen_sucursal.columns = ['Total_DTEs', 'Monto_Total', 'Monto_Promedio', 'Status_Detail']
    resumen_sucursal = resumen_sucursal.sort_values('Monto_Total', ascending=False)
    
    st.dataframe(resumen_sucursal, use_container_width=True)

with tab2:
    if not df_filtrado.empty:
        resumen_responsable = df_filtrado.groupby('responsable').agg({
            'contador': 'sum',
            'total': ['sum', 'mean'],
            'sucursal': 'nunique'
        }).round(2)
        
        resumen_responsable.columns = ['Total_DTEs', 'Monto_Total', 'Monto_Promedio', 'Num_Sucursales']
        resumen_responsable = resumen_responsable.sort_values('Monto_Total', ascending=False)
        
        st.dataframe(resumen_responsable, use_container_width=True)

with tab3:
    resumen_periodo = df_filtrado.groupby('Periodo').agg({
        'contador': 'sum',
        'total': ['sum', 'mean'],
        'sucursal': 'nunique',
        'responsable': 'nunique'
    }).round(2)
    
    resumen_periodo.columns = ['Total_DTEs', 'Monto_Total', 'Monto_Promedio', 'Num_Sucursales', 'Num_Responsables']
    resumen_periodo = resumen_periodo.sort_values('Periodo', ascending=False)
    
    st.dataframe(resumen_periodo, use_container_width=True)

# DATOS DETALLADOS
st.markdown("---")
st.subheader("🔍 Datos Detallados")

# Checkbox para mostrar/ocultar datos
if st.checkbox("Mostrar datos detallados"):
    st.dataframe(
        df_filtrado[columns_to_show],
        use_container_width=True,
        height=400
    )

# INFORMACIÓN ADICIONAL
st.sidebar.markdown("---")
st.sidebar.info(f"""
**Información del Dataset:**
- Total registros: {len(df_status_dte):,}
- Registros filtrados: {len(df_filtrado):,}
- Último período: {ultimo_mes}
- Sucursales únicas: {df_status_dte['sucursal'].nunique()}
- Responsables únicos: {df_status_dte_filtrado['responsable'].nunique()}
""")

# Footer
st.markdown("---")
st.markdown("*Dashboard actualizado automáticamente con los últimos datos disponibles*")