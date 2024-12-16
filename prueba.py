import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

class MLTest:
    def __init__(self):
        self.client_id = os.getenv('ML_CLIENT_ID')
        self.client_secret = os.getenv('ML_CLIENT_SECRET')
        self.seller_id = os.getenv('ML_SELLER_ID')
        self.access_token = None
    
    def _get_access_token(self):
        response = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
        )
        self.access_token = response.json()['access_token']
    
    def _get_headers(self):
        if not self.access_token:
            self._get_access_token()
        return {'Authorization': f'Bearer {self.access_token}'}

    def test_search_orders(self):
        # Buscar órdenes recientes
        print("\nBuscando órdenes recientes...")
        search_response = requests.get(
            "https://api.mercadolibre.com/orders/search",
            headers=self._get_headers(),
            params={
                'seller': self.seller_id,
                'order.status': 'paid',
                'sort': 'date_desc'  # Ordenadas por fecha descendente
            }
        )
        
        print("\nRESPUESTA DE BÚSQUEDA DE ÓRDENES:")
        print(json.dumps(search_response.json(), indent=2, ensure_ascii=False))

        # Si queremos ver los detalles de una orden específica
        orders = search_response.json().get('results', [])
        if orders:
            order_id = orders[0]['id']  # Tomamos la primera orden
            print(f"\nObteniendo detalles de la orden {order_id}...")
            order_response = requests.get(
                f"https://api.mercadolibre.com/orders/{order_id}",
                headers=self._get_headers()
            )
            print("\nRESPUESTA DETALLE DE ORDEN:")
            print(json.dumps(order_response.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    ml_test = MLTest()
    ml_test.test_search_orders()