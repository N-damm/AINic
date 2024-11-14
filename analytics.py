import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

class Analytics:
    def __init__(self, ml_api, database):
        self.ml = ml_api
        self.db = database
        
    def get_sales_metrics(self, days=30):
        """Obtiene métricas básicas de ventas"""
        try:
            sales = self.ml.get_sales(days)
            df = pd.DataFrame(sales)
            
            if df.empty:
                return {
                    'total_sales': 0,
                    'total_revenue': 0,
                    'avg_price': 0,
                    'total_items': 0
                }
            
            # Calcular métricas
            total_sales = len(df)
            total_revenue = df['total_amount'].sum() if 'total_amount' in df.columns else 0
            avg_price = total_revenue / total_sales if total_sales > 0 else 0
            total_items = df['order_items'].apply(len).sum() if 'order_items' in df.columns else 0
            
            return {
                'total_sales': total_sales,
                'total_revenue': total_revenue,
                'avg_price': avg_price,
                'total_items': total_items
            }
        except Exception as e:
            print(f"Error calculando métricas de ventas: {str(e)}")
            return {
                'total_sales': 0,
                'total_revenue': 0,
                'avg_price': 0,
                'total_items': 0
            }
    
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
    
    def plot_sales_trend(self, days=30):
        """Genera gráfico de tendencia de ventas"""
        try:
            sales = self.ml.get_sales(days)
            df = pd.DataFrame(sales)
            
            if df.empty:
                return None
                
            df['date'] = pd.to_datetime(df['date_created']).dt.date
            daily_sales = df.groupby('date').size().reset_index(name='sales')
            
            fig = px.line(daily_sales, x='date', y='sales',
                         title='Ventas Diarias',
                         labels={'sales': 'Ventas', 'date': 'Fecha'})
            
            return fig
        except Exception as e:
            print(f"Error generando gráfico de ventas: {str(e)}")
            return None
    
    def plot_price_distribution(self, products):
        """Genera gráfico de distribución de precios"""
        try:
            df = pd.DataFrame(products)
            
            if df.empty:
                return None
                
            fig = px.histogram(df, x='price',
                             title='Distribución de Precios',
                             labels={'price': 'Precio', 'count': 'Cantidad de Productos'})
            
            return fig
        except Exception as e:
            print(f"Error generando gráfico de precios: {str(e)}")
            return None
    
    def plot_stock_distribution(self, products):
        """Genera gráfico de distribución de stock"""
        try:
            df = pd.DataFrame(products)
            
            if df.empty:
                return None
                
            stock_status = pd.cut(df['available_quantity'],
                                bins=[-1, 0, 5, 10, 20, float('inf')],
                                labels=['Sin stock', '1-5', '6-10', '11-20', 'Más de 20'])
            
            stock_counts = stock_status.value_counts()
            
            fig = px.pie(values=stock_counts.values,
                        names=stock_counts.index,
                        title='Distribución de Stock')
            
            return fig
        except Exception as e:
            print(f"Error generando gráfico de stock: {str(e)}")
            return None