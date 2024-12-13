from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

class MLApi:
    def __init__(self):
        self.client_id = os.getenv('ML_CLIENT_ID')
        self.client_secret = os.getenv('ML_CLIENT_SECRET')
        self.seller_id = os.getenv('ML_SELLER_ID')
        self.access_token = None
    
    def _get_access_token(self):
        try:
            response = requests.post(
                "https://api.mercadolibre.com/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            self.access_token = response.json()['access_token']
        except Exception as e:
            print(f"Error de autenticación: {str(e)}")
    
    def _get_headers(self):
        if not self.access_token:
            self._get_access_token()
        return {'Authorization': f'Bearer {self.access_token}'}
    
    def get_products(self, offset=0, limit=20):
        """
        Obtiene productos con paginación
        """
        try:
            response = requests.get(
                f"https://api.mercadolibre.com/users/{self.seller_id}/items/search",
                headers=self._get_headers(),
                params={'offset': offset, 'limit': limit}
            )
            
            data = response.json()
            total = data.get('paging', {}).get('total', 0)
            items = data.get('results', [])
            
            products = []
            for item_id in items:
                item_response = requests.get(
                    f"https://api.mercadolibre.com/items/{item_id}",
                    headers=self._get_headers()
                )
                if item_response.status_code == 200:
                    products.append(item_response.json())
            
            return {
                'products': products,
                'total': total,
                'has_more': offset + limit < total
            }
            
        except Exception as e:
            print(f"Error obteniendo productos: {str(e)}")
            return {'products': [], 'total': 0, 'has_more': False}
        
    def answer_question(self, question_id, answer_text):
        try:
            response = requests.post(
                "https://api.mercadolibre.com/answers",
                headers=self._get_headers(),
                json={
                    "question_id": question_id,
                    "text": answer_text
                }
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Error respondiendo pregunta: {str(e)}")
            return False
    
    def get_sales(self, days=30):
        """
        Obtiene las ventas de los últimos X días
        """
        try:
            # Calcular fechas en UTC-3 (hora de Argentina)
            end_date = datetime.now() - timedelta(hours=3)
            start_date = end_date - timedelta(days=days)
            
            response = requests.get(
                "https://api.mercadolibre.com/orders/search",
                headers=self._get_headers(),
                params={
                    'seller': self.seller_id,
                    'order.status': 'paid',
                    'order.date_created.from': start_date.strftime("%Y-%m-%dT%H:%M:%S-03:00"),
                    'order.date_created.to': end_date.strftime("%Y-%m-%dT%H:%M:%S-03:00")
                }
            )
            
            if response.status_code != 200:
                print(f"Error en la respuesta de la API: {response.text}")
                return []
                
            return response.json().get('results', [])
        except Exception as e:
            print(f"Error obteniendo ventas: {str(e)}")
            return []

    def get_questions(self, offset=0, limit=20, status='UNANSWERED'):
        """
        Obtiene preguntas con paginación y ordenadas por fecha
        """
        try:
            if status not in ['ANSWERED', 'UNANSWERED']:
                status = 'UNANSWERED'

            params = {
                'seller_id': self.seller_id,
                'status': status,
                'offset': offset,
                'limit': limit,
                'sort_fields': 'date_created',
                'sort_types': 'DESC'
            }
            
            response = requests.get(
                "https://api.mercadolibre.com/my/received_questions/search",
                headers=self._get_headers(),
                params=params
            )
            
            if response.status_code != 200:
                print(f"Error en la respuesta de la API: {response.text}")
                return {'questions': [], 'total': 0, 'has_more': False}

            data = response.json()
            questions = data.get('questions', [])
            total = data.get('paging', {}).get('total', 0)

            # Obtener información del producto para cada pregunta
            for question in questions:
                if 'item_id' in question:
                    item_response = requests.get(
                        f"https://api.mercadolibre.com/items/{question['item_id']}",
                        headers=self._get_headers()
                    )
                    if item_response.status_code == 200:
                        question['item'] = item_response.json()

            return {
                'questions': questions,  # Ya vienen ordenadas por la API
                'total': total,
                'has_more': offset + limit < total
            }
                
        except Exception as e:
            print(f"Error obteniendo preguntas: {str(e)}")
            return {'questions': [], 'total': 0, 'has_more': False}

ml_api = MLApi()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products')
def products():
    return render_template('products.html')

@app.route('/api/products')
def get_products():
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 20, type=int)
    return jsonify(ml_api.get_products(offset, limit))

@app.route('/questions')
def questions():
    return render_template('questions.html')

@app.route('/api/questions')
def get_questions():
    offset = request.args.get('offset', 0, type=int)
    limit = request.args.get('limit', 20, type=int)
    status = request.args.get('status', 'all')
    return jsonify(ml_api.get_questions(offset, limit, status))

@app.route('/api/questions/answer', methods=['POST'])
def answer_question():
    data = request.json
    success = ml_api.answer_question(data['question_id'], data['answer'])
    return jsonify({'success': success})

@app.route('/metrics')
def metrics():
    return render_template('metrics.html')

@app.route('/api/sales')
def get_sales():
    days = request.args.get('days', 30, type=int)
    sales = ml_api.get_sales(days)
    return jsonify(sales)

if __name__ == '__main__':
    app.run(debug=True)