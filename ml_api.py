# ml_api.py
import requests
from datetime import datetime, timedelta
from config import ML_CONFIG

class MLApi:
    def __init__(self, client_id, client_secret, seller_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.seller_id = seller_id
        self.access_token = None

    def _get_access_token(self):
        try:
            auth_url = "https://api.mercadolibre.com/oauth/token"
            payload = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            response = requests.post(auth_url, data=payload)
            response.raise_for_status()
            self.access_token = response.json()['access_token']
            return self.access_token
        except Exception as e:
            print(f"Error obteniendo token: {str(e)}")
            return None

    def _get_headers(self):
        if not self.access_token:
            self._get_access_token()
        return {'Authorization': f'Bearer {self.access_token}'}

    def get_products(self):
        try:
            # Primero obtenemos los IDs de todos los productos
            items_url = f"https://api.mercadolibre.com/users/{self.seller_id}/items/search"
            offset = 0
            limit = 50
            products = []
    
            while True:
                params = {
                    'offset': offset,
                    'limit': limit
                }
                items_response = requests.get(items_url, headers=self._get_headers(), params=params)
                
                if items_response.status_code != 200:
                    print(f"Error obteniendo lista de items: {items_response.text}")
                    break
    
                items_data = items_response.json()
                item_ids = items_data.get('results', [])
    
                if not item_ids:
                    break
    
                # Luego obtenemos la información detallada de cada producto
                for item_id in item_ids:
                    product = self.get_item_info(item_id)
                    if product:
                        products.append(product)
    
                offset += limit
    
            return products
    
        except Exception as e:
            print(f"Error obteniendo productos: {str(e)}")
            return []

    def get_item_info(self, item_id):
        try:
            url = f"https://api.mercadolibre.com/items/{item_id}"
            response = requests.get(url, headers=self._get_headers())
            if response.status_code == 200:
                return response.json()
            print(f"Error obteniendo info del item {item_id}: {response.text}")
            return None
        except Exception as e:
            print(f"Error obteniendo info del item {item_id}: {str(e)}")
            return None

    def get_questions(self, status='all'):
        try:
            url = "https://api.mercadolibre.com/my/received_questions/search"
            params = {
                'seller_id': self.seller_id,
                'status': status,
                'limit': 50
            }
            
            all_questions = []
            offset = 0
            
            while True:
                params['offset'] = offset
                response = requests.get(url, headers=self._get_headers(), params=params)
                
                if response.status_code != 200:
                    print(f"Error obteniendo preguntas: {response.text}")
                    break
                    
                data = response.json()
                questions = data.get('questions', [])
                
                if not questions:
                    break
                    
                # Obtener información completa del producto para cada pregunta
                for question in questions:
                    if 'item_id' in question:
                        item_info = self.get_item_info(question['item_id'])
                        if item_info:
                            question['item'] = item_info
                    
                all_questions.extend(questions)
                
                if len(questions) < 50:
                    break
                    
                offset += 50
            
            return all_questions
            
        except Exception as e:
            print(f"Error obteniendo preguntas: {str(e)}")
            return []
        
    def get_sales(self, days=1):
        """
        Obtiene las ventas de los últimos X días
        
        Args:
            days (int): Número de días hacia atrás para obtener ventas
            
        Returns:
            list: Lista de órdenes de venta
        """
        try:
            # Si es 1 día, tomar desde 00:00 hasta 23:59:59 del día actual
            if days == 1:
                from_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                to_date = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            else:
                # Para más días, tomar desde las 00:00 del día inicial
                from_date = (datetime.now() - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
                to_date = datetime.now()

            # URL para obtener órdenes
            url = "https://api.mercadolibre.com/orders/search"
            
            params = {
                'seller': self.seller_id,
                'order.status': 'paid',  # Solo órdenes pagadas
                'order.date_created.from': from_date.strftime("%Y-%m-%dT%H:%M:%S.000-00:00"),
                'order.date_created.to': to_date.strftime("%Y-%m-%dT%H:%M:%S.000-00:00"),
                'sort': 'date_desc'
            }
            
            all_orders = []
            offset = 0
            limit = 50
            
            while True:
                params['offset'] = offset
                params['limit'] = limit
                
                response = requests.get(
                    url, 
                    headers=self._get_headers(),
                    params=params
                )
                
                if response.status_code != 200:
                    print(f"Error obteniendo órdenes: {response.text}")
                    break
                    
                data = response.json()
                results = data.get('results', [])
                
                if not results:
                    break
                    
                all_orders.extend(results)
                
                # Si recibimos menos resultados que el límite, llegamos al final
                if len(results) < limit:
                    break
                    
                offset += limit
                
            return all_orders
            
        except Exception as e:
            print(f"Error obteniendo ventas: {str(e)}")
            return []