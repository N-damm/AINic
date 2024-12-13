import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config import ML_CONFIG, DB_PATH
from ml_api import MLApi
from database import Database
from analytics import Analytics

def init_session_state():
    """Inicializa las variables de sesión"""
    if 'ml_api' not in st.session_state:
        st.session_state.ml_api = MLApi(
            ML_CONFIG['client_id'],
            ML_CONFIG['client_secret'],
            ML_CONFIG['seller_id']
        )
    if 'db' not in st.session_state:
        st.session_state.db = Database(DB_PATH)
    if 'analytics' not in st.session_state:
        st.session_state.analytics = Analytics(
            st.session_state.ml_api,
            st.session_state.db
        )

def show_products_page():
    """Página de productos"""
    st.title("Productos")
    
    # Spinner mientras carga
    with st.spinner('Cargando productos...'):
        products = st.session_state.ml_api.get_products()
        
    if not products:
        st.warning("No se encontraron productos")
        return
        
    # Convertir a DataFrame y seleccionar columnas relevantes
    df = pd.DataFrame(products)
    df = df[[
        'id',
        'title',
        'price',
        'available_quantity',
        'status',
        'permalink'  # URL de la publicación
    ]].copy()
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filtrar por Estado",
            ["Todos", "Activos", "Pausados", "Finalizados"]
        )
    with col2:
        stock_filter = st.selectbox(
            "Filtrar por Stock",
            ["Todos", "Con Stock", "Sin Stock"]
        )

    # Búsqueda
    search = st.text_input("Buscar por título:")

    # Aplicar filtros
    filtered_df = df.copy()
    
    if status_filter != "Todos":
        status_map = {
            "Activos": "active",
            "Pausados": "paused",
            "Finalizados": "closed"
        }
        filtered_df = filtered_df[filtered_df['status'] == status_map[status_filter]]
        
    if stock_filter != "Todos":
        if stock_filter == "Con Stock":
            filtered_df = filtered_df[filtered_df['available_quantity'] > 0]
        else:
            filtered_df = filtered_df[filtered_df['available_quantity'] == 0]
    
    if search:
        filtered_df = filtered_df[filtered_df['title'].str.contains(search, case=False, na=False)]
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Productos", len(filtered_df))
    with col2:
        st.metric("Con Stock", len(filtered_df[filtered_df['available_quantity'] > 0]))
    with col3:
        st.metric("Sin Stock", len(filtered_df[filtered_df['available_quantity'] == 0]))
        
    # Crear columna de link
    filtered_df['Ver publicación'] = filtered_df['permalink'].apply(
        lambda x: f'<a href="{x}" target="_blank">Ver</a>'
    )
    
    # Mostrar DataFrame
    st.markdown("### Lista de Productos")
    st.dataframe(
        filtered_df[[
            'id',
            'title',
            'price',
            'available_quantity',
            'status',
            'Ver publicación'
        ]].style.format({
            'price': '${:,.2f}',
            'Ver publicación': lambda x: x  # Para que muestre el HTML
        }),
        hide_index=True,
        column_config={
            'id': st.column_config.TextColumn('MLA'),
            'title': st.column_config.TextColumn('Título'),
            'price': st.column_config.NumberColumn('Precio'),
            'available_quantity': st.column_config.NumberColumn('Stock'),
            'status': st.column_config.TextColumn('Estado'),
            'Ver publicación': st.column_config.TextColumn('Ver'),
        },
        height=500,
        use_container_width=True
    )
    
    # Exportar a Excel
    if st.download_button(
        "📥 Descargar Excel",
        filtered_df.to_csv(index=False).encode('utf-8'),
        "productos.csv",
        "text/csv",
        key='download-csv'
    ):
        st.success('¡Archivo descargado!')

def show_questions_page():
    """Página de preguntas"""
    st.title("Preguntas")
    
    # Selector de estado
    status = st.selectbox(
        "Filtrar preguntas por estado:",
        ["Sin Responder", "Respondidas"]
    )
    
    status_map = {
        "Sin Responder": "UNANSWERED",
        "Respondidas": "ANSWERED"
    }
    
    # Cargar preguntas
    with st.spinner("Cargando preguntas..."):
        questions = st.session_state.ml_api.get_questions(status_map[status])
    
    if not questions:
        st.info(f"No hay preguntas {status.lower()}")
        return
    
    # Ordenar por fecha
    questions.sort(key=lambda x: x['date_created'], reverse=True)
    
    # Mostrar preguntas
    for q in questions:
        # Crear título para el expander
        product_title = q.get('item', {}).get('title', 'Producto sin título')
        question_preview = q['text'][:50] + "..." if len(q['text']) > 50 else q['text']
        expander_title = f"{product_title} - {question_preview}"
        
        with st.expander(expander_title):
            # Información del producto
            st.markdown("**Producto:**")
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(product_title)
            with col2:
                if 'permalink' in q.get('item', {}):
                    st.markdown(f"[Ver publicación]({q['item']['permalink']})")
            
            # Pregunta y respuesta
            st.markdown("**Pregunta:**")
            st.write(q['text'])
            
            if q.get('answer'):
                st.markdown("**Respuesta:**")
                st.write(q['answer']['text'])
            
            # Fechas y MLA
            col1, col2, col3 = st.columns(3)
            with col1:
                date_created = datetime.fromisoformat(q['date_created'][:-6])
                st.write(f"📅 Pregunta: {date_created.strftime('%d/%m/%Y %H:%M')}")
            with col2:
                if q.get('answer'):
                    answer_date = datetime.fromisoformat(q['answer']['date_created'][:-6])
                    st.write(f"📅 Respuesta: {answer_date.strftime('%d/%m/%Y %H:%M')}")
            with col3:
                st.write(f"🏷️ MLA: {q.get('item', {}).get('id', 'N/A')}")
            
            # Separador
            st.markdown("---")

def show_metrics_page():
    """Página de métricas"""
    st.title("Métricas")
    
    # Selector de período
    days = st.slider(
        "Período de análisis (días)", 
        min_value=1,
        max_value=90, 
        value=30,
        help="Selecciona el número de días para analizar"
    )
    
    # Cargar métricas
    with st.spinner("Calculando métricas..."):
        try:
            sales_metrics = st.session_state.analytics.get_sales_metrics(days)
            questions_metrics = st.session_state.analytics.get_questions_metrics()
        
            # Mostrar métricas principales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Ventas Totales",
                    sales_metrics['total_sales']
                )
            with col2:
                st.metric(
                    "Ingresos",
                    f"${sales_metrics['total_revenue']:,.2f}"
                )
            with col3:
                st.metric(
                    "Preguntas Pendientes",
                    questions_metrics['pending']
                )
            with col4:
                st.metric(
                    "Tiempo Resp. Promedio",
                    f"{questions_metrics['avg_response_time']:.1f}h"
                )
            
            # Gráfico de ventas
            sales_chart = st.session_state.analytics.plot_sales_trend(days)
            if sales_chart is not None:
                st.plotly_chart(sales_chart, use_container_width=True)
            else:
                st.warning("No se pudo generar el gráfico de ventas")
                
            # Productos más vendidos
            st.markdown("### Productos más vendidos")
            
            # Crear un contenedor con margen inferior para las opciones de ordenamiento
            with st.container():
                st.write("Ordenar por:")
                sort_by = st.radio(
                    label="Ordenar por",
                    options=["Cantidad vendida", "Monto vendido"],
                    label_visibility="collapsed"
                )
                st.markdown("---")
            
            # Obtener ventas del período seleccionado
            sales = st.session_state.ml_api.get_sales(days)
            
            if not sales:
                st.info("No hay ventas en el período seleccionado")
            else:
                # Agrupar ventas por producto
                product_sales = {}
                for order in sales:
                    for item in order.get('order_items', []):
                        product_id = item['item']['id']
                        
                        # Obtener información completa del item para obtener el SKU
                        item_info = st.session_state.ml_api.get_item_info(product_id)
                        
                        # Obtener SKU
                        seller_sku = "N/A"
                        if item_info and 'attributes' in item_info:
                            for attr in item_info['attributes']:
                                if attr['id'] == 'SELLER_SKU':
                                    seller_sku = attr['value_name']
                                    break
                        
                        if product_id not in product_sales:
                            product_sales[product_id] = {
                                'title': item['item']['title'],
                                'seller_sku': seller_sku,
                                'quantity': 0,
                                'total_amount': 0
                            }
                        product_sales[product_id]['quantity'] += item['quantity']
                        product_sales[product_id]['total_amount'] += item['quantity'] * float(item['unit_price'])
                
                # Convertir a DataFrame
                df_product_sales = pd.DataFrame(product_sales.values())
                
                if sort_by == "Cantidad vendida":
                    df_product_sales.sort_values(by='quantity', ascending=False, inplace=True)
                else:
                    df_product_sales.sort_values(by='total_amount', ascending=False, inplace=True)
                
                # Mostrar tabla de productos más vendidos
                for _, row in df_product_sales.iterrows():
                    with st.container():
                        st.markdown(f"**{row['title']}**")
                        st.markdown(f"SKU: {row['seller_sku']}")
                        st.markdown(f"Cantidad vendida: {row['quantity']}")
                        st.markdown(f"Monto vendido: ${row['total_amount']:.2f}")
                        st.markdown("---")
                        
            # Detalle de ventas
            st.markdown("### Detalle de Ventas")
            
            if not sales:
                st.info("No hay ventas en el período seleccionado")
            else:
                for order in sales:
                    date_created = (
                        datetime.fromisoformat(order['date_created'].replace('Z', '+00:00'))
                        + timedelta(hours=1)
                    ).strftime('%d/%m/%Y %H:%M')
                    
                    order_total = sum(
                        float(item.get('unit_price', 0)) * float(item.get('quantity', 1))
                        for item in order.get('order_items', [])
                    )
                    
                    expander_title = f"Orden #{order['id']} - {date_created} - Total: ${order_total:,.2f}"
                    with st.expander(expander_title):
                        buyer = order.get('buyer', {})
                        st.markdown(f"**Comprador:** {buyer.get('nickname', 'N/A')}")
                        
                        products_data = []
                        for item in order.get('order_items', []):
                            # Obtener información completa del item para el SKU
                            item_info = st.session_state.ml_api.get_item_info(item['item']['id'])
                            
                            # Obtener SKU
                            seller_sku = "N/A"
                            if item_info and 'attributes' in item_info:
                                for attr in item_info['attributes']:
                                    if attr['id'] == 'SELLER_SKU':
                                        seller_sku = attr['value_name']
                                        break
                                        
                            products_data.append({
                                'SKU': seller_sku,
                                'Producto': item.get('item', {}).get('title', 'N/A'),
                                'Cantidad': item.get('quantity', 0),
                                'Precio Unit.': f"${float(item.get('unit_price', 0)):,.2f}",
                                'Subtotal': f"${float(item.get('unit_price', 0)) * float(item.get('quantity', 1)):,.2f}"
                            })
                        
                        df = pd.DataFrame(products_data)
                        st.dataframe(
                            df,
                            hide_index=True,
                            use_container_width=True
                        )
                        
                        shipping = order.get('shipping', {})
                        if shipping:
                            st.markdown(f"**Envío ID:** {shipping.get('id', 'N/A')}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Estado:** {order.get('status', 'N/A')}")
                        with col2:
                            tags = order.get('tags', [])
                            if tags:
                                st.markdown(f"**Tags:** {', '.join(tags)}")
                
                if st.download_button(
                    "📥 Descargar Detalle de Ventas",
                    create_sales_excel(sales),
                    "ventas_detalle.csv",
                    "text/csv",
                    key='download-sales'
                ):
                    st.success('¡Archivo descargado!')
                
        except Exception as e:
            st.error(f"Error al cargar las métricas: {str(e)}")

def create_sales_excel(sales):
    """Crea el archivo Excel con el detalle de ventas"""
    orders_data = []
    for order in sales:
        date_created = (
            datetime.fromisoformat(order['date_created'].replace('Z', '+00:00'))
            + timedelta(hours=1)  # Ajustar de UTC-4 a UTC-3
        ).strftime('%d/%m/%Y %H:%M')
        
        for item in order.get('order_items', []):
            orders_data.append({
                'Fecha': date_created,
                'Orden ID': order['id'],
                'Comprador': order.get('buyer', {}).get('nickname', 'N/A'),
                'Producto': item.get('item', {}).get('title', 'N/A'),
                'Cantidad': item.get('quantity', 0),
                'Precio Unitario': float(item.get('unit_price', 0)),
                'Subtotal': float(item.get('unit_price', 0)) * float(item.get('quantity', 1)),
                'Estado': order.get('status', 'N/A'),
                'Tags': ', '.join(order.get('tags', []))
            })
    
    df_export = pd.DataFrame(orders_data)
    return df_export.to_csv(index=False).encode('utf-8')

def show_questions_page():
    """Página de preguntas"""
    st.title("Preguntas")
    
    # Selector de estado
    status = st.selectbox(
        "Filtrar preguntas por estado:",
        ["Sin Responder", "Respondidas"]
    )
    
    status_map = {
        "Sin Responder": "UNANSWERED",
        "Respondidas": "ANSWERED"
    }
    
    # Cargar preguntas
    with st.spinner("Cargando preguntas..."):
        questions = st.session_state.ml_api.get_questions(status_map[status])
    
    if not questions:
        st.info(f"No hay preguntas {status.lower()}")
        return
    
    # Ordenar por fecha
    questions.sort(key=lambda x: x['date_created'], reverse=True)
    
    # Mostrar preguntas
    for q in questions:
        # Crear título para el expander
        product_title = q.get('item', {}).get('title', 'Producto sin título')
        question_preview = q['text'][:50] + "..." if len(q['text']) > 50 else q['text']
        expander_title = f"{product_title} - {question_preview}"
        
        with st.expander(expander_title):
            # Información del producto
            st.markdown("**Producto:**")
            col1, col2 = st.columns([3,1])
            with col1:
                st.write(product_title)
            with col2:
                if 'permalink' in q.get('item', {}):
                    st.markdown(f"[Ver publicación]({q['item']['permalink']})")
            
            # Pregunta y respuesta
            st.markdown("**Pregunta:**")
            st.write(q['text'])
            
            if q.get('answer'):
                st.markdown("**Respuesta:**")
                st.write(q['answer']['text'])
            else:
                # Campo para responder
                answer_text = st.text_area(
                    "Responder:",
                    key=f"answer_{q['id']}"
                )
                
                # Botón para enviar respuesta
                if st.button("Enviar Respuesta", key=f"send_{q['id']}"):
                    if answer_text.strip():
                        with st.spinner("Enviando respuesta..."):
                            if st.session_state.ml_api.answer_question(q['id'], answer_text):
                                st.success("¡Respuesta enviada exitosamente!")
                                st.rerun()  # Recargar la página
                            else:
                                st.error("Error al enviar la respuesta")
                    else:
                        st.warning("Por favor, escribe una respuesta")
            
            # Fechas y MLA
            col1, col2, col3 = st.columns(3)
            with col1:
                date_created = datetime.fromisoformat(q['date_created'][:-6])
                st.write(f"📅 Pregunta: {date_created.strftime('%d/%m/%Y %H:%M')}")
            with col2:
                if q.get('answer'):
                    answer_date = datetime.fromisoformat(q['answer']['date_created'][:-6])
                    st.write(f"📅 Respuesta: {answer_date.strftime('%d/%m/%Y %H:%M')}")
            with col3:
                st.write(f"🏷️ MLA: {q.get('item', {}).get('id', 'N/A')}")
            
            # Separador
            st.markdown("---")

def main():
    st.set_page_config(
        page_title="ML Manager",
        page_icon="📊",
        layout="wide"
    )
    
    # Inicializar sesión
    init_session_state()
    
    # Sidebar
    st.sidebar.title("ML Manager")
    page = st.sidebar.selectbox(
        "Navegación",
        ["Productos", "Preguntas", "Métricas"]
    )
    
    # Mostrar página seleccionada
    if page == "Productos":
        show_products_page()
    elif page == "Preguntas":
        show_questions_page()
    elif page == "Métricas":
        show_metrics_page()

if __name__ == "__main__":
    main()

