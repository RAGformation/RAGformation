import boto3
import json

"""
pip install awscli
aws configure
create user
create policy

{
    "Buckets": [
        {
            "Name": "example-bucket",
            "CreationDate": "2023-10-18T12:00:00.000Z"
        }
    ]
}

add user to the policy
"""


def get_price_for_service(service_code: str, filters=None):
    client = boto3.client("pricing", region_name="us-east-1")

    api_filters = [
        {
            "Type": "TERM_MATCH",
            "Field": "ServiceCode",
            "Value": service_code,
        }
    ]
    if filters:
        api_filters.extend(filters)

    try:
        response = client.get_products(
            ServiceCode=service_code, Filters=api_filters, MaxResults=1
        )

        price_items = response.get("PriceList", [])
        if not price_items:
            return None

        price_item = price_items[0]
        price_json = json.loads(price_item)
        terms = price_json.get("terms", {})
        on_demand_terms = terms.get("OnDemand", {})

        detailed_pricing = []
        for term_key, term_value in on_demand_terms.items():
            price_dimensions = term_value.get("priceDimensions", {})
            for pd_key, pd_value in price_dimensions.items():
                price_per_unit = pd_value.get("pricePerUnit", {})
                unit = pd_value.get("unit", "Unknown unit")
                price_usd = price_per_unit.get("USD", "0")

                detailed_pricing.append(
                    {
                        "description": pd_value.get("description", "No description"),
                        "price_usd": price_usd,
                        "unit": unit,
                    }
                )
        return detailed_pricing

    except Exception as e:
        error_msg = f"An error occurred: {e}"
        return error_msg


def main():
    services = [
        "AmazonS3",
        "AmazonRDS",
        "AmazonCloudFront",
        "AmazonRoute53",
        "AmazonECS",
        "AmazonSimpleDB",
    ]
    glacier_filters = [
        {
            "Type": "TERM_MATCH",
            "Field": "StorageClass",
            "Value": "GLACIER",
        },
        {
            "Type": "TERM_MATCH",
            "Field": "Location",
            "Value": "US East (N. Virginia)",
        },
    ]

    for service in services:
        if service == "AmazonS3":
            price_info = get_price_for_service(service, glacier_filters)
        else:
            price_info = get_price_for_service(service)

        if price_info:
            if isinstance(
                price_info, list
            ):  # For services with multiple pricing dimensions
                for info in price_info:
                    print(
                        f"Price for {service}: {info['description']} - {info['price_usd']} USD per {info['unit']}"
                    )
            else:  # For other services with single pricing
                print(
                    f"Price for {service}: {price_info['price_usd']} USD per {price_info['unit']}"
                )
        else:
            print(f"No price found for {service}")


# Call the main function
main()
