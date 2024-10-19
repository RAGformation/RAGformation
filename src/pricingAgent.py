import boto3
import json


def get_price_for_service(service_code):
    client = boto3.client('pricing', region_name='us-east-1')
    response = client.get_products(
        ServiceCode=service_code,
        Filters=[
            {
                'Type': 'TERM_MATCH',
                'Field': 'ServiceCode',
                'Value': service_code,
            },
        ],
        MaxResults=1
    )

    price_items = response.get('PriceList', [])
    if not price_items:
        return None

    price_item = price_items[0]
    price_json = json.loads(price_item)
    terms = price_json.get('terms', {})
    on_demand_terms = terms.get('OnDemand', {})
    for term_key, term_value in on_demand_terms.items():
        price_dimensions = term_value.get('priceDimensions', {})
        for pd_key, pd_value in price_dimensions.items():
            price_per_unit = pd_value.get('pricePerUnit', {})
            unit = pd_value.get('unit', 'Unknown unit')
            price_usd = price_per_unit.get('USD', '0')
            # Return price info
            {'service': service_code, 'price_usd': price_usd, 'unit': unit}
    return None

def main():
    services = ['AmazonRDS', 'AmazonCloudFront', 'AmazonRoute53', 'AmazonECS','AmazonSimpleDB']
    for service in services:
        price_info = get_price_for_service(service)
        if price_info:
            print(f"Price for {service}: {price_info['price_usd']} USD per {price_info['unit']}")
        else:
            print(f"No price found for {service}")