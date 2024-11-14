import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import plotly.graph_objects as go

class Analytics:
    def __init__(self, ml_api, database):
        self.ml = ml_api
        self.db = database
            
    def get_questions_metrics(self):
        """Obtiene métricas de preguntas"""
        try:
            all_questions = self.ml.get_questions('all')
            unanswered = self.ml.get_questions('UNANSWERED')
            
            total = len(all_questions)
            pending = len(unanswered)
            answered = total - pending
            
            # Calcular tiempo promedio de respuesta
            response_times = []
            for q in all_questions:
                if q.get('answer'):
                    question_date = datetime.fromisoformat(q['date_created'][:-6])
                    answer_date = datetime.fromisoformat(q['answer']['date_created'][:-6])
                    response_time = (answer_date - question_date).total_seconds() / 3600  # en horas
                    response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            return {
                'total_questions': total,
                'answered': answered,
                'pending': pending,
                'avg_response_time': avg_response_time
            }
        except Exception as e:
            print(f"Error calculando métricas de preguntas: {str(e)}")
            return {
                'total_questions': 0,
                'answered': 0,
                'pending': 0,
                'avg_response_time': 0
            }
        
    def get_sales_metrics(self, days=30):
        """Obtiene métricas básicas de ventas"""
        try:
            sales = self.ml.get_sales(days)
            
            if not sales:
                return {
                    'total_sales': 0,
                    'total_revenue': 0,
                    'avg_price': 0,
                    'total_items': 0
                }
            
            total_sales = len(sales)
            
            # Calcular ingresos totales usando el precio real de la transacción
            total_revenue = 0
            total_items = 0
            
            for order in sales:
                # Obtener items y cantidades
                for item in order.get('order_items', []):
                    quantity = int(item.get('quantity', 0))
                    # Usar unit_price que es el precio real al que se vendió
                    price = float(item.get('unit_price', 0))
                    total_items += quantity
                    total_revenue += price * quantity
            
            # Calcular precio promedio
            avg_price = total_revenue / total_items if total_items > 0 else 0
            
            return {
                'total_sales': total_sales,  # Número de órdenes
                'total_revenue': total_revenue,  # Ingreso total real
                'avg_price': avg_price,  # Precio promedio por item
                'total_items': total_items  # Cantidad total de items
            }
            
        except Exception as e:
            print(f"Error calculando métricas de ventas: {str(e)}")
            return {
                'total_sales': 0,
                'total_revenue': 0,
                'avg_price': 0,
                'total_items': 0
            }

    def plot_sales_trend(self, days=30):
        """Genera gráfico de tendencia de ventas"""
        try:
            sales = self.ml.get_sales(days)
            
            if not sales:
                # Crear un gráfico vacío con mensaje
                fig = go.Figure()
                fig.add_annotation(
                    text="No hay datos de ventas disponibles",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False
                )
                fig.update_layout(
                    title='Ventas Diarias',
                    xaxis_title='Fecha',
                    yaxis_title='Ventas'
                )
                return fig
            
            # Crear DataFrame con las ventas
            sales_data = []
            for order in sales:
                # Convertir a datetime local
                date = datetime.fromisoformat(
                    order['date_created'].replace('Z', '+00:00')
                ).replace(tzinfo=None)
                
                # Calcular total de items y revenue por orden
                order_items = 0
                order_revenue = 0
                
                for item in order.get('order_items', []):
                    quantity = int(item.get('quantity', 0))
                    price = float(item.get('unit_price', 0))
                    order_items += quantity
                    order_revenue += price * quantity
                
                sales_data.append({
                    'date': date,
                    'sales': order_items,  # Cantidad de items vendidos
                    'revenue': order_revenue  # Ingreso real de la venta
                })
            
            df = pd.DataFrame(sales_data)
            
            if days == 1:
                # Para un día, agrupar por hora
                df['date_hour'] = df['date'].dt.strftime('%H:00')
                daily_metrics = df.groupby('date_hour').agg({
                    'sales': 'sum',
                    'revenue': 'sum'
                }).reset_index()
                x_axis = 'date_hour'
                title = 'Ventas por Hora (Hoy)'
                xaxis_title = 'Hora'
            else:
                # Para más días, agrupar por fecha
                df['date_day'] = df['date'].dt.date
                daily_metrics = df.groupby('date_day').agg({
                    'sales': 'sum',
                    'revenue': 'sum'
                }).reset_index()
                x_axis = 'date_day'
                title = f'Ventas Diarias (Últimos {days} días)'
                xaxis_title = 'Fecha'
            
            # Crear gráfico con dos ejes Y
            fig = go.Figure()
            
            # Agregar línea de ventas
            fig.add_trace(
                go.Scatter(
                    x=daily_metrics[x_axis],
                    y=daily_metrics['sales'],
                    name='Unidades vendidas',
                    line=dict(color='blue')
                )
            )
            
            # Agregar línea de ingresos en el eje Y secundario
            fig.add_trace(
                go.Scatter(
                    x=daily_metrics[x_axis],
                    y=daily_metrics['revenue'],
                    name='Ingresos ($)',
                    yaxis='y2',
                    line=dict(color='green')
                )
            )
            
            # Configurar layout
            fig.update_layout(
                title=title,
                xaxis_title=xaxis_title,
                yaxis_title='Unidades vendidas',
                yaxis2=dict(
                    title='Ingresos ($)',
                    overlaying='y',
                    side='right'
                ),
                hovermode='x unified'
            )
            
            # Formatear los valores en el hover
            fig.update_traces(
                hovertemplate="<br>".join([
                    "%{x}",
                    "Unidades: %{y:,.0f}",
                    "Ingresos: $%{y:,.2f}"
                ])
            )
            
            return fig
            
        except Exception as e:
            print(f"Error generando gráfico de ventas: {str(e)}")
            # Crear un gráfico de error
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error al generar el gráfico de ventas: {str(e)}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                showarrow=False
            )
            fig.update_layout(
                title='Ventas Diarias',
                xaxis_title='Fecha',
                yaxis_title='Ventas'
            )
            return fig