import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración de la página
st.set_page_config(page_title="Dashboard Automatizado", layout="wide")

st.title("📊 Dashboard de Reportes Automatizados")
st.markdown("Descarga tu archivo Excel de la web, súbelo aquí y el análisis se generará al instante.")

# 1. Componente para subir el archivo
archivo_cargado = st.file_uploader("Elige el archivo Excel (.xlsx)", type=["xlsx"])

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
        # Define aquí las columnas que SIEMPRE deben venir en tu reporte
        # Ejemplo: COLUMNAS_REQUERIDAS = ['Fecha', 'Categoría', 'Ventas', 'Cliente']
        COLUMNAS_REQUERIDAS = list(df.columns) # Por ahora toma las que vienen
        
        # Validar que la estructura sea la correcta
        if all(col in df.columns for col in COLUMNAS_REQUERIDAS):
            st.success("¡Archivo cargado y validado con éxito!")
            
            # --- SECCIÓN DE VISTA PREVIA ---
            with st.expander("👀 Ver vista previa de los datos"):
                st.dataframe(df.head(3), use_container_width=True)
            # --------------------------------------------
            orden_horas = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3]

            orden_mesas = [
                'P1_MESA1', 'P1_MESA2', 'P1_MESA3', 'P1_MESA4', 'P1_MESA5', 'P1_MESA6', 'P1_MESA7', 'P1_MESA8',
                'P1_MESA9', 'P1_M10', 'P1_M11', 'P1_M12',
                'P2_MESA1','P2_MESA2','P2_MESA3','P2_MESA4','P2_MESA5',
                'SIN MESA'
            ]
            # -----------------------------------------------------------

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
            
            total_facturados = df_filtrado[df_filtrado['estado'] == 'Facturado']['codigo'].nunique()
            total_pendientes = df_filtrado[df_filtrado['estado'] == 'Pendiente']['codigo'].nunique()
            
            # Contamos eliminados si tienen fecha de eliminación o si el estado es 'Anulado'
            total_eliminados = df_filtrado[(df_filtrado['fecha_eliminacion'].notna()) | (df_filtrado['estado'] == 'Eliminado')]['codigo'].nunique()
            
            # El cálculo de delivery busca los códigos únicos filtrados que originalmente contienen la palabra DELIVERY
            codigos_delivery_global = df[df['producto'].str.contains('DELIVERY', case=False, na=False)]['codigo'].unique()
            total_deliveries = df_filtrado[df_filtrado['codigo'].isin(codigos_delivery_global)]['codigo'].nunique()
            
            # 2. Layout de Tarjetas en 5 columnas
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(label="🎟️ Total Pedidos", value=f"{total_pedidos_unicos}")
            with col2:
                st.metric(label="✅ Total Facturados", value=f"{total_facturados}")
            with col3:
                st.metric(label="⏳ Total Pendientes", value=f"{total_pendientes}")
            with col4:
                st.metric(label="🚨 Total Eliminados", value=f"{total_eliminados}")
            with col5:
                st.metric(label="🛵 Total Delivery", value=f"{total_deliveries}")
            
            st.markdown("---")
            
            
            # ==========================================
            #   PESTAÑAS DE TRABAJO (TABS)
            # ==========================================
            tab1, tab2, tab3, tab4, tab5 = st.tabs(
                ["🕵️ Control de Salón (Cámaras)", 
                 "🚨 Auditoría de Eliminaciones", 
                 "💰 Densidad de Dinero por Hora y Mesa",                 
                 "🔥 Densidad de Pedidos por Hora y Mesa",
                 "🗺️ Mapa de Calor (Pedidos)"])
            
            # --- PESTAÑA 1: TABLA DE CONTRASTE ---
            with tab1:
                st.subheader("📋 Consumo Cronológico por Mesa")
                st.caption("Usa esta tabla para contrastar los despachos visuales de tus cámaras con el sistema.")
                
                # Modificación: agregamos salto de línea nativo en Streamlit cambiando /n por <br> o espacio
                tabla_contraste = (df_filtrado[df_filtrado['estado'] == 'Facturado']
                    .groupby(['h_pedido', 'mesa', 'codigo'])
                    .agg(
                        Productos=('producto', lambda x: ', '.join(x.dropna())), # Cambiado a coma limpia para visualización tabular
                        Total_soles=('total', 'sum')
                    )
                    .reset_index()
                    .sort_values(by=['h_pedido', 'mesa'])
                )
                st.dataframe(tabla_contraste, use_container_width=True, hide_index=True)
            
            # --- PESTAÑA 2: AUDITORÍA DE ELIMINACIONES ---
            with tab2:
                st.subheader("⚠️ Pedidos Eliminados")
                st.caption("Monitorea de cerca qué productos fueron borrados y contrástalo con pérdidas o fraudes simulados.")
                
                tabla_eliminacion = df_filtrado[df_filtrado['fecha_eliminacion'].notna() | (df_filtrado['estado'] == 'Eliminado')].copy()
                tabla_eliminacion = tabla_eliminacion[['h_pedido', 'h_eliminacion', 'mesa', 'producto', 'total']]
                
                if not tabla_eliminacion.empty:
                    st.dataframe(tabla_eliminacion.style.highlight_null(color="#ffcccc"), use_container_width=True, hide_index=True)
                else:
                    st.info("No se registran órdenes eliminadas o anuladas bajo los filtros seleccionados.")
            
            # --- PESTAÑA 3: MAPA DE CALOR INTERACTIVO ---
            with tab3:
                st.subheader("💰 Densidad de Dinero por Hora y Mesa")
                
                # Listas de control de orden (Asegúrate de definir orden_horas y orden_mesas previamente en tu script)
                pivot_dinero = df_filtrado[df_filtrado['estado'] == 'Facturado'].pivot_table(
                    index='hora_entera', 
                    columns='mesa', 
                    values='total', 
                    aggfunc='sum'
                )
                
                # Ajuste de reindex dinámico según los filtros para evitar que crasheé Plotly
                mesas_filtradas = [m for m in orden_mesas if m in pivot_dinero.columns]
                horas_filtradas = [h for h in orden_horas if h in pivot_dinero.index]
                
                if not pivot_dinero.empty:
                    pivot_dinero = pivot_dinero.reindex(index=orden_horas, columns=orden_mesas)
                    etiquetas_horas = [f"{h}:00" for h in pivot_dinero.index]

                    fig_dinero = px.imshow(
                        pivot_dinero,
                        labels=dict(x="Mesa", y="Hora", color="Total(S/.)"),
                        x=pivot_dinero.columns,
                        y=etiquetas_horas,
                        text_auto=".1f",    
                        aspect="auto",
                        color_continuous_scale="Greens",
                        title="Dinero Acumulado (Hora vs Mesa)",
                        width=700,         # Ancho amplio para que las mesas entren rectas
                        height=600          # Alto suficiente para que no se oculte ninguna hora
                    )
                    fig_dinero.update_xaxes(
                        side='bottom',                 # Pone las mesas en la parte de arriba
                        tickangle=270,                # Fuerza a que las etiquetas estén completamente horizontales
                        showgrid=False,             # Elimina las líneas de guía del fondo
                        zeroline=False,             # Elimina la línea base cero
                        tickmode='array',           # Fuerza a Plotly a pintar TODAS las mesas de la lista
                        tickvals=list(range(len(orden_mesas))),
                        ticktext=orden_mesas
                    )

                    # 6. Configuración del Eje Y (Horas) - COMPLETO Y SIN LÍNEAS
                    fig_dinero.update_yaxes(
                        type='category',
                        showgrid=False,             # Elimina las líneas de guía del fondo
                        zeroline=False,             # Elimina la línea base cero
                        tickmode='array',           # Fuerza a Plotly a pintar TODAS las horas de la lista
                        tickvals=list(range(len(etiquetas_horas))),
                        ticktext=etiquetas_horas
                    )
                    
                    # Líneas divisorias inteligentes basadas en lo que queda disponible en el filtro
                    if 12 in horas_filtradas:
                        idx_pm = horas_filtradas.index(12) - 0.5
                        fig_dinero.add_hline(y=idx_pm, line_dash="dash", line_color="gray", annotation_text="Inicio PM")
                    if 0 in horas_filtradas:
                        idx_mn = horas_filtradas.index(0) - 0.5
                        fig_dinero.add_hline(y=idx_mn, line_dash="dash", line_color="gray", annotation_text="Madrugada")
                    
                    # Desplegar gráfico adaptativo en Streamlit
                    st.plotly_chart(fig_dinero, use_container_width=True)
                else:
                    st.warning("No hay datos suficientes para dibujar el mapa de calor con los filtros actuales.")

            # --- PESTAÑA 4: MAPA DE CALOR INTERACTIVO ---
            with tab4:
                st.subheader("🔢 Densidad de Cantidad por Hora y Mesa")
                
                # Listas de control de orden (Asegúrate de definir orden_horas y orden_mesas previamente en tu script)
                pivot_cantidad = df_filtrado[df_filtrado['estado'] == 'Facturado'].pivot_table(
                    index='hora_entera', 
                    columns='mesa', 
                    values='cantidad', 
                    aggfunc='sum', 
                    fill_value=''
                )
                
                # Ajuste de reindex dinámico según los filtros para evitar que crasheé Plotly
                mesas_filtradas = [m for m in orden_mesas if m in pivot_cantidad.columns]
                horas_filtradas = [h for h in orden_horas if h in pivot_cantidad.index]
                
                if not pivot_cantidad.empty:
                    pivot_cantidad = pivot_cantidad.reindex(index=orden_horas, columns=orden_mesas)
                    etiquetas_horas = [f"{h}:00" for h in pivot_cantidad.index]
                    
                    
                    fig_cantidad = px.imshow(
                        pivot_cantidad,
                        labels=dict(x="Mesa", y="Hora", color="Cantidad"),
                        x=pivot_cantidad.columns,
                        y=etiquetas_horas,
                        text_auto=".0f",    
                        aspect="auto",
                        color_continuous_scale="ylgn",
                        title="Cantidad Acumulada (Hora vs Mesa)",
                        width=700,         # Ancho amplio para que las mesas entren rectas
                        height=600          # Alto suficiente para que no se oculte ninguna hora
                    )

                    fig_cantidad.update_xaxes(
                        side='bottom',                 # Pone las mesas en la parte de arriba
                        tickangle=270,                # Fuerza a que las etiquetas estén completamente horizontales
                        showgrid=False,             # Elimina las líneas de guía del fondo
                        zeroline=False,             # Elimina la línea base cero
                        tickmode='array',           # Fuerza a Plotly a pintar TODAS las mesas de la lista
                        tickvals=list(range(len(orden_mesas))),
                        ticktext=orden_mesas
                    )

                    # 6. Configuración del Eje Y (Horas) - COMPLETO Y SIN LÍNEAS
                    fig_cantidad.update_yaxes(
                        type='category',
                        showgrid=False,             # Elimina las líneas de guía del fondo
                        zeroline=False,             # Elimina la línea base cero
                        tickmode='array',           # Fuerza a Plotly a pintar TODAS las horas de la lista
                        tickvals=list(range(len(etiquetas_horas))),
                        ticktext=etiquetas_horas
                    )
                    
                    # Líneas divisorias inteligentes basadas en lo que queda disponible en el filtro
                    if 12 in horas_filtradas:
                        idx_pm = horas_filtradas.index(12) - 0.5
                        fig_cantidad.add_hline(y=idx_pm, line_dash="dash", line_color="gray", annotation_text="Inicio PM")
                    if 0 in horas_filtradas:
                        idx_mn = horas_filtradas.index(0) - 0.5
                        fig_cantidad.add_hline(y=idx_mn, line_dash="dash", line_color="gray", annotation_text="Madrugada")
                    
                    # Desplegar gráfico adaptativo en Streamlit
                    st.plotly_chart(fig_cantidad, use_container_width=True)
                else:
                    st.warning("No hay datos suficientes para dibujar el mapa de calor con los filtros actuales.")

            # --- PESTAÑA 5: MAPA DE CALOR INTERACTIVO ---
            with tab5:
                st.subheader("🔥 Densidad de Pedidos por Hora y Mesa")
                
                # Listas de control de orden (Asegúrate de definir orden_horas y orden_mesas previamente en tu script)
                pivot_pedidos = df_filtrado[df_filtrado['estado'] == 'Facturado'].pivot_table(
                    index='hora_entera', 
                    columns='mesa', 
                    values='codigo', 
                    aggfunc='nunique'
                )
                
                # Ajuste de reindex dinámico según los filtros para evitar que crasheé Plotly
                mesas_filtradas = [m for m in orden_mesas if m in pivot_pedidos.columns]
                horas_filtradas = [h for h in orden_horas if h in pivot_pedidos.index]
                
                if not pivot_pedidos.empty:
                    pivot_pedidos = pivot_pedidos.reindex(index=orden_horas, columns=orden_mesas)
                    etiquetas_horas = [f"{h}:00" for h in pivot_pedidos.index]
                    
                    fig_pedidos = px.imshow(
                        pivot_pedidos,
                        labels=dict(x="Mesa", y="Hora", color="Total pedidos"),
                        x=pivot_pedidos.columns,
                        y=etiquetas_horas,
                        text_auto=".0f",    
                        aspect="auto",
                        color_continuous_scale="Reds",
                        title="Distribución de Carga de Trabajo (Pedidos Únicos)",
                        width=700,         # Ancho amplio para que las mesas entren rectas
                        height=600   
                    )
                    
                    fig_pedidos.update_xaxes(
                        side='top', # Cambiado a 'top' para mantener consistencia con el gráfico anterior de dinero
                        tickangle=0,
                        showgrid=False,
                        zeroline=False
                    )
                    
                    fig_pedidos.update_yaxes(
                        type='category',
                        showgrid=False,
                        zeroline=False
                    )
                    
                    # Líneas divisorias inteligentes basadas en lo que queda disponible en el filtro
                    if 12 in horas_filtradas:
                        idx_pm = horas_filtradas.index(12) - 0.5
                        fig_pedidos.add_hline(y=idx_pm, line_dash="dash", line_color="gray", annotation_text="Inicio PM")
                    if 0 in horas_filtradas:
                        idx_mn = horas_filtradas.index(0) - 0.5
                        fig_pedidos.add_hline(y=idx_mn, line_dash="dash", line_color="gray", annotation_text="Madrugada")
                    
                    # Desplegar gráfico adaptativo en Streamlit
                    st.plotly_chart(fig_pedidos, use_container_width=True)
                else:
                    st.warning("No hay datos suficientes para dibujar el mapa de calor con los filtros actuales.")
                                              
            # --- SECCIÓN EXTRA: RATIOS DE ESTADO EN EL SIDEBAR O AL FINAL ---
            #with st.sidebar.expander("📈 Ver Ratios de Estado (Muestra total)"):
            #    ratios_estado = df['estado'].value_counts().reset_index()
            #    ratios_estado.columns = ['Estado', 'Total']
            #    st.dataframe(ratios_estado, hide_index=True)
        else:
            st.error("🚨 El archivo no coincide con la estructura de columnas requerida.")
            
    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
else:
    st.info("💡 Esperando que subas el archivo Excel para iniciar el análisis...")