import streamlit as st
import pandas as pd
import plotly.express as px

#--------------------------------------------------------------------------
st.set_page_config(page_title="Escalinata Cafeteria - Daily Report", layout="wide")

st.title("📊 Reporte Diario de Pedidos")
st.markdown("Descargar el archivo Excel desde SENDA, súbelo aquí y el análisis se generará al instante.")

# --- Componente para subir el archivo ---
archivo_cargado = st.file_uploader("Elige el archivo Excel (.xlsx)", type=["xlsx"])
        # Limpieza y estandarización de nombres de columnas, manejo de fechas y conversión de tipos numéricos
if archivo_cargado is not None:
    try:
        nuevos_nombres = [
            'estado', 'codigo', 'fecha_pedido', 'fecha_eliminacion', 
            'mesa', 'mozo', 'observaciones', 'unidad', 'producto', 
            'cantidad', 'precio_unitario', 'total'
        ]
        numericos=['cantidad', 'precio_unitario', 'total']

        df= pd.read_excel(
            archivo_cargado, 
            sheet_name="Reporte Pedidos detallado", 
            usecols="A:L",
            engine="calamine",
            header=0,              
            names=nuevos_nombres   
        )
        df = (df.assign(
            fecha_pedido = lambda x: pd.to_datetime(x['fecha_pedido'], format='%d/%m/%Y %H:%M:%S', errors='coerce'),
            fecha_eliminacion = lambda x: pd.to_datetime(x['fecha_eliminacion'], format='%d/%m/%Y %H:%M:%S', errors='coerce'),
            f_pedido = lambda x: x['fecha_pedido'].dt.strftime('%d/%m/%Y'), 
            h_pedido = lambda x: x['fecha_pedido'].dt.strftime('%H:%M:%S'),
            f_eliminacion = lambda x: x['fecha_eliminacion'].dt.strftime('%d/%m/%Y'), 
            h_eliminacion = lambda x: x['fecha_eliminacion'].dt.strftime('%H:%M:%S')
        ).dropna( # filtro nulas (ultima fila q totaliza)
            subset=['estado']
        ).assign(**{col: df[col].apply(pd.to_numeric, errors='coerce') for col in numericos})
        )
  
# --- CONFIGURACIÓN DE COLUMNAS ---
        COLUMNAS_REQUERIDAS = list(df.columns) # Por ahora toma las que vienen
        
        # Validar que la estructura sea la correcta
        if all(col in df.columns for col in COLUMNAS_REQUERIDAS):
            st.success("¡Archivo cargado y validado con éxito!")
            
            #  orden necesario para que no ordene alfabéticamente
            orden_horas = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3]

            orden_mesas = [
                'P1_MESA1', 'P1_MESA2', 'P1_MESA3', 'P1_MESA4', 'P1_MESA5', 'P1_MESA6', 'P1_MESA7', 'P1_MESA8',
                'P1_MESA9', 'P1_M10', 'P1_M11', 'P1_M12',
                'P2_MESA1','P2_MESA2','P2_MESA3','P2_MESA4','P2_MESA5',
                'SIN MESA'
            ]
# ==========================================
#   BARRA LATERAL: FILTROS DINÁMICOS
# ==========================================
            st.sidebar.header("🛠️ Filtros del Tablero")
            # 1. Filtro de Estado
            estados_disponibles = sorted(df['estado'].dropna().unique())
            estados_seleccionados = st.sidebar.multiselect(
                "Selecciona los Estados:", 
                options=estados_disponibles, 
                default=estados_disponibles
            )
            
            # 2. Filtro de Hora (Asegurando que existe 'hora_entera')
            if 'hora_entera' not in df.columns and 'h_pedido' in df.columns:
                df['hora_entera'] = df['h_pedido'].str[:2].astype(int)
                
            horas_disponibles = sorted(df['hora_entera'].dropna().unique())
            horas_seleccionadas = st.sidebar.multiselect(
                "Selecciona el Rango de Horas:", 
                options=horas_disponibles, 
                default=horas_disponibles,
                format_func=lambda x: f"{x}:00"
            )
            
            # 3. Filtro de Mesa
            mesas_disponibles = sorted(df['mesa'].dropna().unique())
            mesas_seleccionadas = st.sidebar.multiselect(
                "Selecciona las Mesas:", 
                options=mesas_disponibles, 
                default=mesas_disponibles
            )
            
            # APLICAR FILTROS AL DATAFRAME COPIA
            # Nota: Mantenemos el df original intacto por si necesitas cálculos globales (ej. Deliveries)
            df_filtrado = df[
                (df['estado'].isin(estados_seleccionados)) &
                (df['hora_entera'].isin(horas_seleccionadas)) &
                (df['mesa'].isin(mesas_seleccionadas))
            ].copy()
            
# ==========================================
#   SECCIÓN DE KPIs / MÉTRICAS PRINCIPALES
# ==========================================
            st.markdown("## 📊 Indicadores Clave del Día")
            
            # 1. Cálculos de métricas basados en el DataFrame filtrado
            total_pedidos_unicos = df_filtrado['codigo'].nunique()

            soles_facturados = df_filtrado[df_filtrado['estado'] == 'Facturado']['total'].sum().round(1)
            soles_pendientes = df_filtrado[df_filtrado['estado'] == 'Pendiente']['total'].sum().round(1)
            
            total_facturados = df_filtrado[df_filtrado['estado'] == 'Facturado']['codigo'].nunique()
            total_pendientes = df_filtrado[df_filtrado['estado'] == 'Pendiente']['codigo'].nunique()
            
            # Contamos eliminados si tienen fecha de eliminación o si el estado es 'Anulado'
            total_eliminados = df_filtrado[(df_filtrado['fecha_eliminacion'].notna()) | (df_filtrado['estado'] == 'Eliminado')]['codigo'].nunique()
            
            # El cálculo de delivery busca los códigos únicos filtrados que originalmente contienen la palabra DELIVERY
            codigos_delivery_global = df[df['producto'].str.contains('DELIVERY', case=False, na=False)]['codigo'].unique()
            total_deliveries = df_filtrado[df_filtrado['codigo'].isin(codigos_delivery_global)]['codigo'].nunique()
            
            # 2. Layout de Tarjetas en 5 columnas
            st.markdown("### 💰 Control de Caja")
            primaria_col1, primaria_col2 = st.columns(2)
            
            with primaria_col1:
                st.metric(label="💵 SOLES FACTURADOS (Caja Real)", value=f"S/. {soles_facturados}")
            with primaria_col2:
                st.metric(label="⏳ SOLES PENDIENTES (Por Cobrar)", value=f"S/. {soles_pendientes}")
                
            st.markdown("<br>", unsafe_allow_html=True) # Pequeño espacio de respiro visual
            
            
            # --- 3. FILA INFERIOR: MÉTRICAS SECUNDARIAS (CANTIDAD DE TICKETS) ---
            # Dividimos en 5 columnas compactas para el conteo operativo
            st.markdown("##### 🎟️ Movimiento de Tickets")
            secundaria_col1, secundaria_col2, secundaria_col3, secundaria_col4, secundaria_col5 = st.columns(5)
            
            with secundaria_col1:
                st.metric(label="Total Pedidos", value=f"{total_pedidos_unicos}")
            with secundaria_col2:
                st.metric(label="Tickets Facturados", value=f"{total_facturados}")
            with secundaria_col3:
                st.metric(label="Tickets Pendientes", value=f"{total_pendientes}")
            with secundaria_col4:
                st.metric(label="Tickets Eliminados", value=f"{total_eliminados}")
            with secundaria_col5:
                st.metric(label="Tickets Delivery", value=f"{total_deliveries}")
            
            st.markdown("---")
                  
# ==========================================
#   PESTAÑAS DE TRABAJO (TABS)
# ==========================================
            #tab1, tab2, tab3 = st.tabs(
            #    ["🕵️ Gestion de Salon", 
            #     "🚨 Auditoría de Eliminaciones",
            #     "🗒️ Reporte para Stock"
            #     ])
            st.markdown("### 🔍 Módulos de Inspección")

            # --- PESTAÑA 1: TABLA DE CONTRASTE ---
            with st.expander("🕵️ Abrir Gestión de Salón solo Facturado", expanded=False):
                st.subheader("🕵️ Gestión de Salón (Monitoreo por Tarjetas)")
                st.caption("Se ve lo facturado por mesa, hora y monto.")

                # Filtramos para trabajar solo con los pedidos facturados dentro del df_filtrado
                df_salon = df_filtrado[df_filtrado['estado'] == 'Facturado']

                if not df_salon.empty:
                    # 1. Agrupamos por pedido para obtener las cabeceras y totales
                    pedidos_resumen = (df_salon.groupby(['codigo', 'h_pedido', 'mesa'])
                        .agg(
                            Total_Soles=('total', 'sum'),
                            Total_Productos=('cantidad', 'sum')
                        )
                        .reset_index()
                    )

                    # 2. COMPONENTE DE ORDENAMIENTO INTERNO (Solo ordena, no filtra)
                    st.markdown("##### 🔀 Ordenar tarjetas por:")
                    opcion_orden = st.radio(
                        "Selecciona el criterio de ordenamiento (Ascendente):",
                        options=["Hora", "Mesa", "Monto"],
                        horizontal=True,
                        label_visibility="collapsed" # Oculta el título del radio para que se vea más limpio
                    )

                    # 3. Aplicar la lógica de orden según la opción seleccionada
                    if opcion_orden == "Hora":
                        pedidos_resumen = pedidos_resumen.sort_values(by='h_pedido', ascending=False)
                    elif opcion_orden == "Mesa":
                        # Usamos el orden_mesas establecido previamente para que no ordene de forma alfabética simple (ej. P1_M10 antes que P1_M2)
                        pedidos_resumen['mesa'] = pd.Categorical(pedidos_resumen['mesa'], categories=orden_mesas, ordered=True)
                        pedidos_resumen = pedidos_resumen.sort_values(by='mesa')
                    elif opcion_orden == "Monto":
                        pedidos_resumen = pedidos_resumen.sort_values(by='Total_Soles', ascending=False)

                    # 4. Configuración de la cuadrícula: 3 tarjetas por fila
                    tarjetas_por_fila = 3
                    
                    # Iteramos sobre los pedidos ya ordenados
                    for i in range(0, len(pedidos_resumen), tarjetas_por_fila):
                        bloque_pedidos = pedidos_resumen.iloc[i : i + tarjetas_por_fila]
                        cols_fila = st.columns(tarjetas_por_fila)
                        
                        for idx, (_, row) in enumerate(bloque_pedidos.iterrows()):
                            with cols_fila[idx]:
                                # Contenedor con borde (Efecto visual de Tarjeta)
                                with st.container(border=True):
                                    
                                    # --- FILA SUPERIOR DE LA TARJETA ---
                                    head_col1, head_col2, head_col3 = st.columns([1.2, 1.6, 1.2])
                                    
                                    with head_col1:
                                        st.markdown(f"<p style='margin:0; font-size:14px; color:gray;'>🕒 {row['h_pedido']}</p>", unsafe_allow_html=True)
                                    
                                    with head_col2:
                                        st.markdown(f"<p style='text-align:center; margin:0; font-weight:bold; color:#FF4B4B;'>#{row['codigo']}</p>", unsafe_allow_html=True)
                                    
                                    with head_col3:
                                        st.markdown(f"<p style='text-align:right; margin:0; font-weight:bold; color:#1E88E5;'> {row['mesa']}</p>", unsafe_allow_html=True)
                                    
                                    st.markdown("<hr style='margin:8px 0; border:0; border-top:1px solid #ddd;'>", unsafe_allow_html=True)
                                    
                                    # --- CUERPO DE LA TARJETA ---
                                    body_col1, body_col2 = st.columns(2)
                                    with body_col1:
                                        st.metric(label="💰 Total Soles", value=f"S/. {row['Total_Soles']:.1f}")
                                    with body_col2:
                                        st.metric(label="📦 Cant. Total", value=f"{int(row['Total_Productos'])} und")
                                    
                                    # --- MENÚ EXPANDIBLE (Detalle) ---
                                                                   
                                    productos_del_pedido = df_salon[df_salon['codigo'] == row['codigo']][['producto', 'cantidad', 'estado']]
                                    
                                    with st.expander("📋 Ver lista de productos"):
                                        for _, prod in productos_del_pedido.iterrows():
                                            # Determinar el color según el estado del producto
                                            estado_prod = str(prod['estado']).strip().lower()
                                            
                                            if estado_prod in ['anulado', 'eliminado']:
                                                color_fuente = "#FF4B4B"  # Rojo Streamlit
                                            elif estado_prod == 'pendiente':
                                                color_fuente = "#FFAA00"  # Amarillo/Naranja visible
                                            else:
                                                color_fuente = "inherit"  # Color normal del tema (blanco o negro según modo oscuro/claro)
                                            
                                            # Construimos la línea con HTML para aplicar el color
                                            texto_producto = f"• **{int(prod['cantidad'])}x** {prod['producto']}"
                                            st.markdown(
                                                f"<span style='color: {color_fuente};'>{texto_producto}</span>", 
                                                unsafe_allow_html=True
                                            )
                else:
                    st.info("No se registran pedidos para armar las tarjetas con los filtros actuales.")            
            
            # --- PESTAÑA 2: AUDITORÍA DE ELIMINACIONES ---
            with st.expander("🚨 Abrir Auditoría de Eliminaciones", expanded=False):
                st.subheader("⚠️ Pedidos Anulados o Eliminados")
                st.caption("Monitorea de cerca qué productos fueron borrados.")
                
                tabla_eliminacion = df_filtrado[df_filtrado['fecha_eliminacion'].notna() | (df_filtrado['estado'] == 'Eliminado')].copy()
                tabla_eliminacion = tabla_eliminacion[['h_pedido', 'h_eliminacion', 'mesa', 'producto', 'total']]
                
                if not tabla_eliminacion.empty:
                    st.dataframe(tabla_eliminacion.style.highlight_null(color="#ffcccc"), use_container_width=True, hide_index=True)
                else:
                    st.info("No se registran órdenes eliminadas o anuladas bajo los filtros seleccionados.")
                        
            # --- PESTAÑA 3: PENDIENTES DE FACTURAR ---
            with st.expander("🚨 Abrir Mesas pendientes de Facturación", expanded=False):
                st.subheader("⚠️ Pedidos Pendientes")
                st.caption("Monitorea pedidos realizados pendientes de facturación.")
                
                tabla_pendientes = df_filtrado[df_filtrado['fecha_eliminacion'].notna() | (df_filtrado['estado'] == 'Pendiente')].copy()
                tabla_pendientes = tabla_pendientes[['h_pedido', 'h_eliminacion', 'mesa', 'producto', 'total']]
                
                if not tabla_pendientes.empty:
                    st.dataframe(tabla_pendientes.style.highlight_null(color="#ffcccc"), use_container_width=True, hide_index=True)
                else:
                    st.info("No se registran órdenes pendientes bajo los filtros seleccionados.")
                    
            #-------PESTAÑA 4: TABLA PRODUCTOS ---
            with st.expander("🗒️ Abrir Reporte para Stock", expanded=False):
                st.subheader("🗒️ Reporte para Stock")
                st.caption("Resumen de cantidades vendidas por producto.")

                reporte_stock = (df_filtrado
                    .groupby(['estado', 'producto'])['cantidad']
                    .sum()
                    .reset_index()
                )
                reporte_stock.columns = ['Estado', 'Producto', 'Cantidad Vendida (Unidades)']
                reporte_stock = reporte_stock.sort_values(by=['Estado', 'Cantidad Vendida (Unidades)'], ascending=[True, False])

                if not reporte_stock.empty:
                    st.dataframe(reporte_stock, use_container_width=True, hide_index=True)
                    total_unidades = int(reporte_stock['Cantidad Vendida (Unidades)'].sum())
                    st.info(f"📦 **Volumen Total Movido:** Se han registrado un total de **{total_unidades} unidades** de productos.")
                else:
                    st.warning("No hay registros de productos vendidos bajo los filtros seleccionados actualmente.")
        else:
            st.error("🚨 El archivo no coincide con la estructura de columnas requerida.")
            
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.info("💡 Esperando que subas el archivo Excel para iniciar el análisis...")