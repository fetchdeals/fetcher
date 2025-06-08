import requests
import re
from bs4 import BeautifulSoup
from cache import get, set
import os
import asyncio
import aiohttp
import random
import urllib.parse

def handler(req):
    query = req.get('product', '').strip().lower()
    country = req.get('country', 'UK').upper()
    if not query:
        return {'error': 'Missing product'}, 400

    cache_key = f"{query}_{country}"
    cached = get(cache_key)
    if cached:
        return cached, 200

    def is_similar(title1, title2):
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())
        common = len(words1 & words2)
        return common / max(len(words1), len(words2)) > 0.75

    electronics_keywords = {'phone', 'laptop', 'air fryer', 'headphones', 'smartwatch'}
    fashion_keywords = {'jeans', 'dress', 'shirt', 'shoes', 'jacket'}
    grocery_keywords = {'milk', 'bread', 'eggs', 'cheese', 'rice'}
    is_electronics = any(k in query.lower() for k in electronics_keywords)
    is_fashion = any(k in query for k in fashion_keywords)
    is_grocery = any(k in query for k in grocery_keywords)

    async def fetch_retailer(session, retailer, query, country='UK'):
        retailers = {
            'UK': {
                'Currys': {'url': f'https://www.currys.co.uk/search?q={query}', 'api': os.environ.get('CURRYS_API_KEY')},
                'Amazon': {'url': f'https://www.amazon.co.uk/s?k={query}', 'api': None},
                'ASOS': {'url': f'https://www.asos.com/search?q={query}', 'api': None},
                'Tesco': {'url': f'https://www.tesco.com/groceries/en-GB/search?q={query}', 'api': None},
                'Sainsbury’s': {'url': f'https://www.sainsburys.co.uk/search?q={query}', 'api': None},
                'John Lewis': {'url': f'https://www.johnlewis.com/search?q={query}', 'api': None},
                'Apple': {'url': f'https://www.apple.com/uk/shop/buy-iphone/iphone-15?q={query}', 'api': None},
                'O2': {'url': f'https://www.o2.co.uk/shop/phones/apple/iphone-15?q={query}', 'api': None},
                'Vodafone': {'url': f'https://www.vodafone.co.uk/mobile/phones/pay-monthly/apple-iphone-15?q={query}', 'api': None}
            }
        }
        config = retailers.get(country, retailers['UK']).get(retailer, {'url': f'https://www.{retailer.lower()}.co.uk/search?q={query}', 'api': None})
        try:
            async with session.get(config['url'], timeout=1.5) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                offer = soup.select_one('.product, .item, .price-container')
                price_text = offer.select_one('.price').text if offer and offer.select_one('.price') else ''
                price = float(re.search(r'[\d.]+', price_text).group() or 0) if price_text else 0
                delivery_fee = 3.0 if 'tesco' in retailer.lower() or 'sainsbury' in retailer.lower() else 0.0
                stock = offer.select_one('.stock').text.strip() if offer and offer.select_one('.stock') else 'In Stock'
                url = offer.find('a')['href'] if offer and offer.find('a') else config['url']
                sub_id = query.replace(' ', '_')
                affiliate_param = (
                    f'?awc=fetch123_{sub_id}' if 'currys' in retailer.lower() or 'o2' in retailer.lower() or 'vodafone' in retailer.lower() or 'asos' in retailer.lower() or 'tesco' in retailer.lower() else
                    f'?tag=fetch123_{sub_id}&addToCart=1' if 'amazon' in retailer.lower() else
                    f'?rakuten=fetch123_{sub_id}' if 'johnlewis' in retailer.lower() else
                    f'?appleaff=fetch123_{sub_id}' if 'apple' in retailer.lower() else ''
                )
                fvs = calculate_fvs(price, delivery_fee, retailer)
                return {
                    'title': query,
                    'price': price,
                    'delivery_fee': delivery_fee,
                    'total': price + delivery_fee,
                    'url': f'/redirect?url={urllib.parse.quote(url + affiliate_param)}',
                    'retailer': retailer,
                    'priority': 3 if 'currys' in retailer.lower() or 'o2' in retailer.lower() or 'vodafone' in retailer.lower() else 1,
                    'fvs': fvs,
                    'pressure': random.choice(['3 viewing', 'Only 2 left!', '']) if random.random() > 0.5 else '',
                    'category': 'electronics' if is_electronics else 'fashion' if is_fashion else 'groceries' if is_grocery else 'general',
                    'pulse': f'Price dropped {random.randint(1,5)}%' if random.random() > 0.7 else '',
                    'stock': stock,
                    'sub_id': sub_id
                }
        except Exception as e:
            print(f'{retailer} error: {e}')
            return None

    async def fetch_aggregator(session, url, name):
        try:
            async with session.get(url, timeout=1.5) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, 'html.parser')
                offers = soup.select('.offer-item, .product-offer, .gsc-result')
                results = []
                for offer in offers:
                    price_text = offer.select_one('.price').text if offer.select_one('.price') else ''
                    price = float(re.search(r'[\d.]+', price_text).group() or 0) if price_text else 0
                    retailer = offer.select_one('.retailer-name').text.strip() if offer.select_one('.retailer-name') else name
                    url = offer.find('a')['href'] if offer.find('a') else f'https://www.amazon.co.uk/s?k={query}'
                    stock = 'In Stock'
                    sub_id = query.replace(' ', '_')
                    affiliate_param = f'?awc=fetch123_{sub_id}' if name.lower() in ['pricerunner', 'kelkoo', 'shopzilla', 'pricegrabber'] else ''
                    fvs = calculate_fvs(price, 0.0, retailer)
                    results.append({
                        'title': query,
                        'price': price,
                        'delivery_fee': 0.0,
                        'total': price,
                        'url': f'/redirect?url={urllib.parse.quote(url + affiliate_param)}',
                        'retailer': retailer,
                        'priority': 1,
                        'fvs': fvs,
                        'pressure': '',
                        'category': 'general',
                        'pulse': '',
                        'stock': stock,
                        'sub_id': sub_id
                    })
                return results
        except Exception as e:
            print(f'Aggregator {name} error: {e}')
            return []

    def calculate_fvs(price, delivery_fee, retailer):
        price_score = min(100, 100 - (price / 100) * 50)  # 70%
        delivery_score = 100 - (delivery_fee * 15)  # 15%
        brand_reliability = {
            'Currys': 95, 'Amazon': 90, 'ASOS': 85, 'Tesco': 90, 'Sainsbury’s': 85, 'John Lewis': 95,
            'Apple': 95, 'O2': 85, 'Vodafone': 85,
            'PriceRunner': 80, 'Idealo': 80, 'PriceSpy': 80, 'Google Shopping': 75, 'Kelkoo': 75,
            'Shopzilla': 75, 'PriceGrabber': 75
        }.get(retailer, 75)  # 15%
        return round((price_score * 0.7) + (delivery_score * 0.15) + (brand_reliability * 0.15))

    try:
        async with aiohttp.ClientSession() as session:
            retailer_tasks = [
                fetch_retailer(session, r, query)
                for r in ['Currys', 'Amazon', 'ASOS', 'Tesco', 'Sainsbury’s', 'John Lewis', 'Apple', 'O2', 'Vodafone']
            ]
            aggregator_tasks = [
                fetch_aggregator(session, url, name)
                for name, url in [
                    ('PriceRunner', f'https://www.pricerunner.com/search?q={query}'),
                    ('Idealo', f'https://www.idealo.co.uk/search?q={query}'),
                    ('PriceSpy', f'https://pricespy.co.uk/search?q={query}'),
                    ('Google Shopping', f'https://www.google.com/search?tbm=shop&q={query}'),
                    ('Kelkoo', f'https://www.kelkoo.co.uk/search?q={query}'),
                    ('Shopzilla', f'https://www.shopzilla.co.uk/search?q={query}'),
                    ('PriceGrabber', f'https://www.pricegrabber.com/search?q={query}')
                ]
            ]
            results = []
            for r in await asyncio.gather(*retailer_tasks):
                if r and r.get('price', 0) > 0 and r['stock'] == 'In Stock':
                    results.append(r)
            for agg_results in await asyncio.gather(*aggregator_tasks):
                results.extend([r for r in agg_results if r.get('price', 0) > 0 and r['stock'] == 'In Stock'])

            # Deduplicate results
            seen_results = set()
            unique_results = []
            for r in sorted(results, key=lambda x: (-x['fvs'], x['total'], -x['priority'])):
                key = (r['retailer'].lower(), round(r['total'], 1))
                if key not in seen_results and is_similar(r['title'], query):
                    seen_results.add(key)
                    unique_results.append(r)

            if not unique_results:
                unique_results.append({
                    'title': query,
                    'price': 0.0,
                    'delivery_fee': 0.0,
                    'total': 0.0,
                    'url': f'/redirect?url={urllib.parse.quote(f"https://www.amazon.co.uk/s?k={query}&tag=fetch123_{query.replace(' ', '_')}")}',
                    'retailer': 'Amazon',
                    'priority': 1,
                    'fvs': 80,
                    'pressure': '',
                    'category': 'general',
                    'pulse': '',
                    'stock': 'In Stock',
                    'sub_id': query.replace(' ', '_')
                })

            cheapest = min(unique_results, key=lambda x: x['total'])
            result = {
                'title': cheapest['title'],
                'price': cheapest['price'],
                'delivery_fee': cheapest['delivery_fee'],
                'total': cheapest['total'],
                'currency': 'GBP',
                'retailer': cheapest['retailer'],
                'url': cheapest['url'],
                'fvs': cheapest['fvs'],
                'pressure': cheapest['pressure'],
                'category': cheapest['category'],
                'pulse': cheapest['pulse'],
                'stock': cheapest['stock'],
                'sub_id': cheapest['sub_id'],
                'alternatives': [x for x in unique_results if x['url'] != cheapest['url']]
            }
            set(cache_key, result)
            return result, 200
    except Exception as e:
        print(f'Price error: {e}')
        return {'error': 'Failed to retrieve data'}, 500