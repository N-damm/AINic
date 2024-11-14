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
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Productos", len(df))
    with col2:
        st.metric("Con Stock", len(df[df['available_quantity'] > 0]))
    with col3:
        st.metric("Sin Stock", len(df[df['available_quantity'] == 0]))

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
        ["Todas", "Sin Responder", "Respondidas"]
    )
    
    status_map = {
        "Todas": "all",
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
    days = st.slider("Período de análisis (días)", 7, 90, 30)
    
    # Cargar métricas
    with st.spinner("Calculando métricas..."):
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
    
    # Gráficos
    st.plotly_chart(
        st.session_state.analytics.plot_sales_trend(days),
        use_container_width=True
    )

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