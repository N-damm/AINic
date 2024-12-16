from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta, timezone
import requests
import os
import json
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

    def get_products(self, offset=0, limit=50):
        try:
            print(f"Obteniendo productos con offset={offset}, limit={limit}")
            
            # Verificar token de acceso
            if not self.access_token:
                print("No hay token de acceso, obteniendo uno nuevo...")
                self._get_access_token()
            
            response = requests.get(
                f"https://api.mercadolibre.com/users/{self.seller_id}/items/search",
                headers=self._get_headers(),
                params={'offset': offset, 'limit': limit}
            )
            
            print(f"Status code de búsqueda: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Error en la respuesta de la API: {response.text}")
                if response.status_code == 401:  # Token expirado
                    print("Token expirado, obteniendo uno nuevo...")
                    self._get_access_token()
                    return self.get_products(offset, limit)  # Reintentar con nuevo token
                return {'products': [], 'total': 0, 'has_more': False}

            data = response.json()
            print(f"Datos recibidos: {data}")
            
            total = data.get('paging', {}).get('total', 0)
            items = data.get('results', [])
            
            print(f"Total de items: {total}")
            print(f"Items encontrados: {len(items)}")
            
            products = []
            for item_id in items:
                print(f"Obteniendo detalles para item {item_id}")
                item_response = requests.get(
                    f"https://api.mercadolibre.com/items/{item_id}",
                    headers=self._get_headers()
                )
                print(f"Status code de item {item_id}: {item_response.status_code}")
                
                if item_response.status_code == 200:
                    product_data = item_response.json()
                    
                    # Obtener precios promocionales
                    prices_response = requests.get(
                        f"https://api.mercadolibre.com/items/{item_id}/prices",
                        headers=self._get_headers()
                    )
                    
                    if prices_response.status_code == 200:
                        prices_data = prices_response.json()
                        if "prices" in prices_data:
                            promo_price = next(
                                (p["amount"] for p in prices_data["prices"] if p.get("type") == "promotion"),
                                None
                            )
                            if promo_price:
                                product_data['promo_price'] = promo_price
                    
                    products.append(product_data)
                else:
                    print(f"Error obteniendo item {item_id}: {item_response.text}")
            
            result = {
                'products': products,
                'total': total,
                'has_more': offset + limit < total
            }
            
            print(f"Retornando {len(products)} productos")
            return result
            
        except Exception as e:
            print(f"Error obteniendo productos: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'products': [], 'total': 0, 'has_more': False}
    
    def get_questions(self, offset=0, limit=50, status='UNANSWERED'):
        try:
            if status not in ['ANSWERED', 'UNANSWERED']:
                status = 'UNANSWERED'

            params = {
                'seller_id': self.seller_id,
                'status': status,
                'offset': offset,
                'limit': limit
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

            return {
                'questions': questions,
                'total': total,
                'has_more': offset + limit < total
            }
                
        except Exception as e:
            print(f"Error obteniendo preguntas: {str(e)}")
            return {'questions': [], 'total': 0, 'has_more': False}
    
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
        try:
            tz = timezone(timedelta(hours=-3))  # Argentina timezone
            end_date = datetime.now(tz)
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

    def get_product_skus(self, product_data):
        """Obtiene todos los SKUs de un producto"""
        skus = []
        
        # Buscar SKU en las variaciones
        if 'variations' in product_data:
            for variation in product_data['variations']:
                if 'attributes' in variation:
                    for attr in variation['attributes']:
                        if attr.get('id') == 'SELLER_SKU':
                            skus.append(attr.get('value_name'))
                            break

        # Buscar en atributos principales
        if 'attributes' in product_data:
            for attr in product_data['attributes']:
                if attr.get('id') == 'SELLER_SKU':
                    skus.append(attr.get('value_name'))
                    break

        # Si no hay SKU, intentar con el número de pieza
        if not skus and 'attributes' in product_data:
            for attr in product_data['attributes']:
                if attr.get('id') == 'PART_NUMBER':
                    skus.append(attr.get('value_name'))
                    break

        # Si aún no hay SKUs, usar el ID del producto
        if not skus:
            skus.append(f"ML{product_data.get('id', '').replace('MLA', '')}")

        return sorted(set(skus))  # Eliminar duplicados y ordenar

    def get_recent_sales(self, limit=5):
        try:
            tz = timezone(timedelta(hours=-3))
            
            # Obtener órdenes recientes
            response = requests.get(
                "https://api.mercadolibre.com/orders/search",
                headers=self._get_headers(),
                params={
                    'seller': self.seller_id,
                    'order.status': 'paid',
                    'sort': 'date_desc',
                    'limit': 50  # Pedimos más para asegurar tener suficientes
                }
            )
            
            if response.status_code != 200:
                print(f"Error en la respuesta de orders/search: {response.status_code}")
                return []

            sales_data = response.json()
            print("\n=== RESPUESTA INICIAL DE BÚSQUEDA DE ÓRDENES ===")
            print(json.dumps(sales_data, indent=2, ensure_ascii=False))

            recent_sales = []
            processed_orders = set()
            
            for sale in sales_data.get('results', []):
                try:
                    order_id = sale['id']
                    
                    if order_id in processed_orders:
                        continue
                    
                    print(f"\n=== PROCESANDO ORDEN {order_id} ===")
                    
                    # Obtener detalles completos de la orden
                    order_response = requests.get(
                        f"https://api.mercadolibre.com/orders/{order_id}",
                        headers=self._get_headers()
                    )
                    
                    if order_response.status_code != 200:
                        continue
                        
                    order_data = order_response.json()
                    print(f"Datos de la orden: {json.dumps(order_data, indent=2, ensure_ascii=False)}")
                    
                    # Si la orden es parte de un pack, procesar todo el pack
                    pack_id = order_data.get('pack_id')
                    all_order_items = []
                    
                    if pack_id:
                        print(f"Orden parte del pack {pack_id}, obteniendo todas las órdenes")
                        pack_response = requests.get(
                            f"https://api.mercadolibre.com/packs/{pack_id}",
                            headers=self._get_headers()
                        )
                        
                        if pack_response.status_code == 200:
                            pack_data = pack_response.json()
                            for pack_order in pack_data.get('orders', []):
                                if pack_order['id'] not in processed_orders:
                                    pack_order_response = requests.get(
                                        f"https://api.mercadolibre.com/orders/{pack_order['id']}",
                                        headers=self._get_headers()
                                    )
                                    if pack_order_response.status_code == 200:
                                        pack_order_data = pack_order_response.json()
                                        all_order_items.extend(pack_order_data.get('order_items', []))
                                        processed_orders.add(pack_order['id'])
                    else:
                        all_order_items = order_data.get('order_items', [])
                    
                    # Procesar todos los items únicos
                    items_detail = []
                    seen_items = set()
                    
                    for item in all_order_items:
                        item_id = item['item']['id']
                        if item_id not in seen_items:
                            seen_items.add(item_id)
                            
                            item_response = requests.get(
                                f"https://api.mercadolibre.com/items/{item_id}",
                                headers=self._get_headers()
                            )
                            
                            if item_response.status_code == 200:
                                item_data = item_response.json()
                                
                                # Obtener SKU con la lógica de prioridad correcta
                                sku = (
                                    item['item'].get('seller_sku') or
                                    item_data.get('seller_custom_field') or
                                    next((attr.get('value_name') for attr in item_data.get('attributes', [])
                                        if attr.get('id') == 'SELLER_SKU'), None) or
                                    f"ML{item_data['id'].replace('MLA', '')}"
                                )

                                items_detail.append({
                                    'id': item_id,
                                    'title': item['item']['title'],
                                    'quantity': int(item.get('quantity', 1)),
                                    'unit_price': float(item.get('unit_price', 0)),
                                    'sku': sku,
                                    'thumbnail': (
                                        item_data.get('thumbnail') or
                                        (item_data.get('pictures', [{}])[0].get('url') if item_data.get('pictures') else None)
                                    )
                                })

                    if items_detail:
                        # Obtener información del comprador y facturación
                        buyer = order_data.get('buyer', {})
                        billing_info = order_data.get('billing_info', {})

                        # Obtener información de envío detallada
                        shipping = order_data.get('shipping', {})
                        receiver_address = shipping.get('receiver_address', {})
                        
                        # Obtener detalles de pago y costos
                        payments = order_data.get('payments', [{}])[0]
                        mediations = order_data.get('mediations', [])
                        
                        # Calcular totales y fees
                        total_products = sum(item['unit_price'] * item['quantity'] for item in items_detail)
                        shipping_cost = shipping.get('cost', 0)
                        taxes_amount = payments.get('taxes_amount', 0)
                        marketplace_fee = payments.get('marketplace_fee', 0)

                        sale_data = {
                            'id': pack_id or order_id,
                            'buyer': {
                                'id': buyer.get('id'),
                                'nickname': buyer.get('nickname', 'Usuario'),
                                'full_name': f"{buyer.get('first_name', '')} {buyer.get('last_name', '')}".strip(),
                            },
                            'date': datetime.fromisoformat(order_data['date_created'].replace('Z', '+00:00')).astimezone(tz).strftime('%d/%m/%Y %H:%M'),
                            'items': items_detail,
                            'total': total_products
                        }                        
                        recent_sales.append(sale_data)
                    
                    if len(recent_sales) >= limit:
                        break

                except Exception as e:
                    print(f"Error procesando venta: {str(e)}")
                    continue

            return recent_sales[:limit]
                    
        except Exception as e:
            print(f"Error general obteniendo ventas recientes: {str(e)}")
            return []
                    
    def _process_order_items(self, order_data):
        """Procesa los items de una orden y retorna la lista de items procesados"""
        items_detail = []
        
        for item in order_data.get('order_items', []):
            try:
                item_response = requests.get(
                    f"https://api.mercadolibre.com/items/{item['item']['id']}",
                    headers=self._get_headers()
                )
                
                if item_response.status_code == 200:
                    item_data = item_response.json()
                    
                    # Obtener cantidad y precio exactamente como viene de la orden
                    quantity = int(item.get('quantity', 1))
                    unit_price = float(item.get('unit_price', 0))
                    subtotal = quantity * unit_price  # Calculamos el subtotal por item

                    # Obtener SKU
                    sku = (
                        item['item'].get('seller_sku') or
                        item_data.get('seller_custom_field') or
                        next((attr.get('value_name') for attr in item_data.get('attributes', [])
                            if attr.get('id') == 'SELLER_SKU'), None) or
                        f"ML{item_data['id'].replace('MLA', '')}"
                    )

                    items_detail.append({
                        'id': item['item']['id'],
                        'title': item['item']['title'],
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'subtotal': subtotal,  # Agregamos el subtotal al item
                        'sku': sku,
                        'thumbnail': (
                            item_data.get('thumbnail') or
                            (item_data.get('pictures', [{}])[0].get('url') if item_data.get('pictures') else None)
                        )
                    })
                    
            except Exception as e:
                print(f"Error procesando item: {str(e)}")
                
        return items_detail
                    
ml_api = MLApi()

@app.route('/api/dashboard/summary')
def get_dashboard_summary():
    try:
        # Obtener solo las últimas 5 ventas
        recent_sales = ml_api.get_recent_sales(limit=5)
        
        # Calcular el total de ventas del día
        tz = timezone(timedelta(hours=-3))
        today = datetime.now(tz).date()
        today_total = sum(
            sale['total'] for sale in recent_sales 
            if datetime.strptime(sale['date'], '%d/%m/%Y %H:%M').date() == today
        )
        
        # Obtener productos con stock bajo
        products_data = ml_api.get_products(limit=50)
        products = products_data['products']
        
        out_of_stock = []
        low_stock = []
        
        for product in products:
            skus = ml_api.get_product_skus(product)
            stock = product.get('available_quantity', 0)
            
            if stock == 0:
                out_of_stock.append({
                    'id': product['id'],
                    'title': product['title'],
                    'stock': stock,
                    'status': product.get('status', 'unknown'),
                    'sku': ', '.join(skus)
                })
            elif stock <= 5:
                low_stock.append({
                    'id': product['id'],
                    'title': product['title'],
                    'stock': stock,
                    'status': product.get('status', 'unknown'),
                    'sku': ', '.join(skus)
                })

        # Obtener preguntas sin responder
        questions_data = ml_api.get_questions(status='UNANSWERED')
        
        return jsonify({
            'sales': {
                'today_total': today_total,
                'recent': recent_sales
            },
            'products': {
                'out_of_stock': len(out_of_stock),
                'low_stock': len(low_stock),
                'alerts': sorted(out_of_stock + low_stock, key=lambda x: (x['stock'], x['title']))
            },
            'questions': {
                'pending': questions_data['total'],
                'urgent': []  # Implementar lógica de preguntas urgentes si es necesario
            }
        })
        
    except Exception as e:
        print(f"Error en dashboard summary: {str(e)}")
        return jsonify({
            'sales': {'today_total': 0, 'recent': []},
            'products': {'out_of_stock': 0, 'low_stock': 0, 'alerts': []},
            'questions': {'pending': 0, 'urgent': []}
        })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/products')
def products():
    return render_template('products.html')

@app.route('/questions')
def questions():
    return render_template('questions.html')

@app.route('/metrics')
def metrics():
    return render_template('metrics.html')

@app.route('/api/products')
def get_products():
    try:
        print("Recibiendo solicitud de productos")
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 50, type=int)
        print(f"Parámetros: offset={offset}, limit={limit}")
        
        response = ml_api.get_products(offset, limit)
        print(f"Respuesta obtenida con {len(response['products'])} productos")
        return jsonify(response)
        
    except Exception as e:
        print(f"Error en ruta /api/products: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'products': [], 'total': 0, 'has_more': False})
        
@app.route('/api/products/<product_id>/details')
def get_product_details(product_id):
    try:
        # Primero obtenemos los datos básicos del producto
        response = requests.get(
            f"https://api.mercadolibre.com/items/{product_id}",
            headers=ml_api._get_headers()
        )
        
        if response.status_code != 200:
            print(f"Error en la API de ML: {response.status_code}")
            return jsonify({'error': 'Producto no encontrado'}), 404
            
        product = response.json()
        
        # Obtener precios (regular y promocional)
        prices_response = requests.get(
            f"https://api.mercadolibre.com/items/{product_id}/prices",
            headers=ml_api._get_headers()
        )
        
        price = product.get('price', 0)
        promo_price = None
        
        if prices_response.status_code == 200:
            prices_data = prices_response.json()
            if "prices" in prices_data:
                prices = prices_data["prices"]
                promo_price_data = next(
                    (p for p in prices if p.get("type") == "promotion"),
                    None
                )
                if promo_price_data:
                    promo_price = float(promo_price_data["amount"])

        # Obtener SKU y resto de la lógica existente...
        sku = None
        if 'attributes' in product:
            for attr in product['attributes']:
                if attr.get('id') == 'SELLER_SKU':
                    sku = attr.get('value_name')
                    break
        
        if not sku and 'variations' in product:
            for variation in product['variations']:
                if 'attributes' in variation:
                    for attr in variation['attributes']:
                        if attr.get('id') == 'SELLER_SKU':
                            sku = attr.get('value_name')
                            break
                if sku:
                    break
        
        if not sku:
            sku = product.get('seller_custom_field') or f"ML{product['id'].replace('MLA', '')}"

        # Buscar última venta
        sales_response = requests.get(
            "https://api.mercadolibre.com/orders/search",
            headers=ml_api._get_headers(),
            params={
                'seller': ml_api.seller_id,
                'order.status': 'paid',
                'q': product_id
            }
        )
        
        last_sale = None
        if sales_response.status_code == 200:
            sales = sales_response.json().get('results', [])
            if sales:
                last_sale = sales[0]['date_created']

        # Incluir el precio promocional en la respuesta
        return jsonify({
            'id': product['id'],
            'title': product.get('title', 'No disponible'),
            'price': price,
            'promo_price': promo_price,  # Nuevo campo
            'available_quantity': product.get('available_quantity', 0),
            'status': product.get('status', 'unknown'),
            'permalink': product.get('permalink', ''),
            'seller_custom_field': sku,
            'last_sale': last_sale,
            'category_id': product.get('category_id'),
            'listing_type_id': product.get('listing_type_id'),
            'thumbnail': product.get('thumbnail', '')
        })
        
    except Exception as e:
        print(f"Error obteniendo detalles del producto: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500
            
@app.route('/api/questions')
def get_questions():
    try:
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 50, type=int)
        status = request.args.get('status', 'UNANSWERED')
        
        # Obtener preguntas básicas
        questions_data = ml_api.get_questions(offset, limit, status)
        
        # Expandir la información de cada pregunta con detalles del producto
        for question in questions_data['questions']:
            if 'item_id' in question:
                try:
                    # Obtener detalles del producto
                    product_response = requests.get(
                        f"https://api.mercadolibre.com/items/{question['item_id']}",
                        headers=ml_api._get_headers()
                    )
                    
                    if product_response.status_code == 200:
                        product_data = product_response.json()
                        
                        # Obtener SKU
                        sku = None
                        if 'attributes' in product_data:
                            for attr in product_data['attributes']:
                                if attr.get('id') == 'SELLER_SKU':
                                    sku = attr.get('value_name')
                                    break
                        
                        # Si no hay SKU en atributos, buscar en variaciones
                        if not sku and 'variations' in product_data:
                            for variation in product_data['variations']:
                                if 'attributes' in variation:
                                    for attr in variation['attributes']:
                                        if attr.get('id') == 'SELLER_SKU':
                                            sku = attr.get('value_name')
                                            break
                                if sku:
                                    break
                        
                        # Si aún no hay SKU, usar el ID como fallback
                        if not sku:
                            sku = f"ML{product_data['id'].replace('MLA', '')}"
                        
                        # Agregar información expandida del producto
                        question['product_details'] = {
                            'id': product_data['id'],
                            'title': product_data['title'],
                            'sku': sku,
                            'thumbnail': product_data.get('pictures', [{}])[0].get('url') if product_data.get('pictures') else None,
                            'permalink': product_data.get('permalink')
                        }
                except Exception as e:
                    print(f"Error obteniendo detalles del producto {question['item_id']}: {str(e)}")
                    continue
        
        return jsonify(questions_data)
        
    except Exception as e:
        print(f"Error en get_questions: {str(e)}")
        return jsonify({'questions': [], 'total': 0, 'has_more': False})

@app.route('/api/questions/answer', methods=['POST'])
def answer_question():
    data = request.json
    success = ml_api.answer_question(data['question_id'], data['answer'])
    return jsonify({'success': success})


def format_recent_sales(sales, tz):
    formatted_sales = []
    for sale in sales:
        try:
            total = sum(
                float(item['unit_price']) * int(item['quantity'])
                for item in sale.get('order_items', [])
            )
            
            formatted_sales.append({
                'id': sale['id'],
                'date': datetime.fromisoformat(sale['date_created'].replace('Z', '+00:00')).astimezone(tz).strftime('%d/%m/%Y %H:%M'),
                'total': total,
                'items': len(sale.get('order_items', [])),
                'buyer': sale.get('buyer', {}).get('nickname', 'N/A')
            })
        except Exception as e:
            print(f"Error formateando venta: {str(e)}")
            continue
            
    return formatted_sales

def format_product_alerts(products):
    alerts = []
    for product in products:
        try:
            alerts.append({
                'id': product['id'],
                'title': product['title'],
                'stock': product.get('available_quantity', 0),
                'status': product.get('status', 'unknown'),
                'type': 'Sin stock' if product.get('available_quantity', 0) == 0 else 'Stock bajo'
            })
        except Exception as e:
            print(f"Error formateando alerta de producto: {str(e)}")
            continue
            
    return sorted(alerts, key=lambda x: (x['stock'], x['title']))[:10]

def format_urgent_questions(questions):
    tz = timezone(timedelta(hours=-3))
    now = datetime.now(tz)
    urgent = []
    
    for question in questions:
        try:
            question_date = datetime.fromisoformat(question['date_created'].replace('Z', '+00:00')).astimezone(tz)
            hours_waiting = (now - question_date).total_seconds() / 3600
            
            if hours_waiting > 12:
                urgent.append({
                    'id': question['id'],
                    'text': question['text'],
                    'date_created': question_date.strftime('%d/%m/%Y %H:%M'),
                    'hours_waiting': int(hours_waiting)
                })
        except Exception as e:
            print(f"Error formateando pregunta urgente: {str(e)}")
            continue
            
    return urgent

if __name__ == '__main__':
    app.run(debug=True)
