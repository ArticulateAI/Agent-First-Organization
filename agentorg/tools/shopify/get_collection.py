import json
from typing import Any, Dict

import shopify

from agentorg.tools.tools import register_tool

description = "Get the details of collection with a preview of the inventory from a list of collections."
slots = [
    {
        "name": "collection_ids",
        "type": "array",
        "items": {"type": "string"},
        "description": "The collection id, such as 'gid://shopify/Collection/2938501948327'. If there is only 1 collection, return in list with single item. If there are multiple collection ids, please return all of them in a list.",
        "prompt": "In order to proceed, please provide the collection id.",
        "required": True,
    },
    {
        "name": "limit",
        "type": "int",
        "description": "Maximum number of products to show.",
        "prompt": "",
        "required": False
    }
]
outputs = [
    {
        "name": "collection_details",
        "type": "dict",
        "description": "The collection details of the collection. such as \"['{'title': 'Beddings and Pillows', 'description': '', 'productsCount': {'count': 6}, 'products': {'nodes': [{'id': 'gid://shopify/Product/7296582090865'}, {'id': 'gid://shopify/Product/7296582025329'}, {'id': 'gid://shopify/Product/7296581894257'}, {'id': 'gid://shopify/Product/7296581763185'}, {'id': 'gid://shopify/Product/7296581337201'}], 'pageInfo': {'hasNextPage': true}}}', '{'title': 'Bedding', 'description': '', 'productsCount': {'count': 4}, 'products': {'nodes': [{'id': 'gid://shopify/Product/7296582123633'}, {'id': 'gid://shopify/Product/7296582090865'}, {'id': 'gid://shopify/Product/7296581894257'}, {'id': 'gid://shopify/Product/7296581763185'}], 'pageInfo': {'hasNextPage': false}}}']\""
    }
]
COLLECTION_NOT_FOUND = "error: collection not found"
errors = [COLLECTION_NOT_FOUND]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_collection(collection_ids: list, limit=3) -> str:
    limit = limit or 3
    try:
        results = []
        for collection_id in collection_ids:
            response = shopify.GraphQL().execute(f"""
            {{
                collection (id: "{collection_id}") {{
                    title
                    description
                    productsCount {{
                        count
                    }}
                    products (first: {limit}) {{
                        nodes {{
                            id
                        }}
                        pageInfo {{
                            hasNextPage
                        }}
                    }}
                }}
            }}
            """)
            parsed_response = json.loads(response)["data"]["collection"]
            results.append(json.dumps(parsed_response))
        return results
    except Exception as e:
        return COLLECTION_NOT_FOUND