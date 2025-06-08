from flask import Flask, render_template, request, jsonify, redirect
import requests
from datetime import datetime
import time
import urllib.parse

app = Flask(__name__)

MOCK_RESULTS = [
    {"title": "iPhone 15", "retailer": "Currys", "price": 599.00, "delivery_fee": 0.00, "total": 599.00, "url": "/redirect?url=https%3A%2F%2Fcurrys.co.uk%2Fproduct%2F123%3Fawc%3Dfetch123_iphone15", "fvs": 92, "pressure": "3 viewing", "category": "electronics", "stock": "In Stock", "pulse": "Dropped 3%", "sub_id": "iphone15"},
    {"title": "iPhone 15", "retailer": "Apple", "price": 799.00, "delivery_fee": 0.00, "total": 799.00, "url": "/redirect?url=https%3A%2F%2Fapple.com%2Fuk%2Fshop%2Fbuy-iphone%2Fiphone-15%3Fappleaff%3Dfetch123_iphone15", "fvs": 88, "pressure": "", "category": "electronics", "stock": "In Stock", "pulse": "", "sub_id": "iphone15"},
    {"title": "iPhone 15", "retailer": "O2", "price": 30.00, "delivery_fee": 0.00, "total": 720.00, "url": "/redirect?url=https%3A%2F%2Fo2.co.uk%2Fshop%2Fphones%2Fapple%2Fiphone-15%3Fawc%3Dfetch123_iphone15", "fvs": 85, "pressure": "Only 2 left!", "category": "electronics", "stock": "In Stock", "pulse": "", "sub_id": "iphone15"}
]

GENERIC_TERMS = ['milk', 'bread', 'shoes', 'shirt', 'jeans']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/redirect')
def redirect_url():
    url = urllib.parse.unquote(request.args.get('url', ''))
    if url:
        return redirect(url, code=302)
    return render_template('error.html', message="Invalid redirect URL", query="")

@app.route('/set-alert', methods=['GET', 'POST'])
def set_alert():
    if request.method == 'POST':
        product = request.form.get('product')
        retailer = request.form.get('retailer')
        email = request.form.get('email')
        desired_price = float(request.form.get('desired_price', 0))
        current_price = float(request.form.get('current_price', 0))
        if not (product and retailer and email and desired_price):
            return render_template('alert.html', message="Please fill all fields!", product=product, retailer=retailer, current_price=current_price)
        alert = {'product': product, 'retailer': retailer, 'email': email, 'desired_price': desired_price, 'current_price': current_price}
        try:
            requests.post('https://fetch-backend.vercel.app/api/alerts', json=alert)
            return render_template('alert.html', message="Alert set! We'll email you when the price drops.")
        except:
            return render_template('alert.html', message="Error setting alert.", product=product, retailer=retailer, current_price=current_price)
    product = request.args.get('product')
    retailer = request.args.get('retailer')
    current_price = request.args.get('current_price')
    return render_template('alert.html', product=product, retailer=retailer, current_price=current_price)

@app.route('/check-alerts', methods=['POST'])
def check_alerts():
    try:
        alerts = requests.get('https://fetch-backend.vercel.app/api/alerts').json()
        for alert in alerts:
            product = alert['product']
            response = requests.get(f"https://fetch-backend.vercel.app/api/price?product={product}&country=UK")
            data = response.json()
            current_price = float(data['price'])
            if current_price <= alert['desired_price']:
                email_data = {
                    'to': alert['email'],
                    'subject': f"Price Drop Alert: {product}",
                    'body': f"{product} at {alert['retailer']} dropped to £{current_price}! Buy now: {data['url']}"
                }
                requests.post('https://fetch-backend.vercel.app/api/email', json=email_data)
                requests.delete(f"https://fetch-backend.vercel.app/api/alerts/{alert['id']}")
        return jsonify({'success': True})
    except Exception as e:
        print(f"Check alerts error: {e}")
        return jsonify({'error': 'Failed to check alerts'}), 500

@app.route('/product/<product>')
def product(product):
    return render_template('product.html', product=product)

@app.route('/category/<category>/<subcategory>')
def category(category, subcategory):
    return render_template('category.html', category=category, subcategory=subcategory)

@app.route('/deal/<category>')
def deal(category):
    return render_template('deal.html', category=category)

@app.route('/price-history/<product>')
def price_history(product):
    return render_template('price_history.html', product=product)

@app.route('/blog')
def blog():
    return render_template('blog.html')

@app.route('/blog/<slug>')
def blog_post(slug):
    return render_template('blog_post.html', slug=slug)

@app.route('/cheapest-finder')
def cheapest_finder():
    return render_template('cheapest_finder.html')

@app.route('/search', methods=['POST'])
def search():
    query = request.form.get('query', '').strip().lower()
    country = request.form.get('country', 'UK').strip().upper()
    page = int(request.form.get('page', 1))
    if not query:
        return render_template('error.html', message="Please enter a product!", query="")
    
    if query in GENERIC_TERMS:
        suggestion = {
            'milk': 'semi-skimmed milk 2L', 'bread': 'wholemeal bread loaf',
            'shoes': 'Nike Air Max shoes', 'shirt': 'white cotton shirt', 'jeans': 'Levi’s 501 jeans'
        }.get(query, 'a specific product')
        return render_template('error.html', message=f"Please be more specific, e.g., '{suggestion}'.", query=query)
    
    electronics_keywords = ['phone', 'laptop', 'air fryer', 'headphones', 'smartwatch']
    is_electronics = any(k in query.lower() for k in electronics_keywords)
    
    try:
        response = requests.get(f"https://fetch-backend.vercel.app/api/price?product={query}&country={country}", timeout=2)
        data = response.json()
        if 'error' in data:
            return render_template('error.html', message="No deals found. Try another product!", query=query)
        
        results = [
            {
                'title': data['title'],
                'retailer': data['retailer'],
                'price': float(data['price']),
                'delivery_fee': float(data['delivery_fee']),
                'total': float(data['total']),
                'url': data['url'],
                'fvs': data.get('fvs', 90),
                'pressure': data.get('pressure', ''),
                'category': data.get('category', 'general'),
                'pulse': data.get('pulse', ''),
                'stock': data.get('stock', 'In Stock'),
                'sub_id': data.get('sub_id', '')
            }
        ] + [
            {
                'title': alt['title'],
                'retailer': alt['retailer'],
                'price': float(alt['price']),
                'delivery_fee': float(alt['delivery_fee']),
                'total': float(alt['total']),
                'url': alt['url'],
                'fvs': alt.get('fvs', 90),
                'pressure': alt.get('pressure', ''),
                'category': alt.get('category', 'general'),
                'pulse': alt.get('pulse', ''),
                'stock': alt.get('stock', 'In Stock'),
                'sub_id': alt.get('sub_id', '')
            }
            for alt in data.get('alternatives', [])
        ] or MOCK_RESULTS

        results = [r for r in results if r['stock'] == 'In Stock']
        per_page = 10
        total_pages = (len(results) + per_page - 1) // per_page
        start = (page - 1) * per_page
        end = start + per_page
        paginated_results = results[start:end]
        return render_template('results.html', results=paginated_results, query=query, is_electronics=is_electronics, country=country, page=page, total_pages=total_pages)

    except Exception as e:
        print(f"Error: {e}")
        return render_template('error.html', message="Something went wrong!", query=query)

@app.route('/analytics', methods=['POST'])
def analytics():
    data = request.json
    try:
        requests.post('https://fetch-backend.vercel.app/api/analytics', json={
            'userId': data.get('userId'),
            'ref': data.get('ref'),
            'url': data.get('url'),
            'retailer': data.get('retailer'),
            'action': data.get('action'),
            'category': data.get('category'),
            'savings': float(data.get('savings', 0)),
            'subId': data.get('subId'),
            'timestamp': data.get('timestamp')
        })
        return jsonify({'success': True})
    except:
        return jsonify({'error': 'Failed to track'}), 400

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback = request.form.get('feedback', '')
        rating = request.form.get('rating', '')
        if feedback and rating:
            try:
                requests.post('https://fetch-backend.vercel.app/api/analytics', json={
                    'userId': 'anon_' + str(int(time.time())),
                    'action': 'feedback',
                    'feedback': feedback,
                    'rating': rating,
                    'timestamp': datetime.now().isoformat()
                })
                return render_template('feedback.html', message="Thanks for your feedback!")
            except:
                return render_template('feedback.html', message="Error submitting feedback.")
        return render_template('feedback.html', message="Please provide feedback and rating.")
    return render_template('feedback.html')

@app.route('/sitemap.xml')
def sitemap():
    return app.send_static_file('sitemap.xml')

if __name__ == '__main__':
    app.run(debug=True)