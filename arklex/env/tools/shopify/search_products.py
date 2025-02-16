import json
from typing import Any, Dict
import shopify

# general GraphQL navigation utilities
from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.shopify.utils_nav import *
from arklex.env.tools.shopify.utils import authorify

# Admin API
from arklex.env.tools.tools import register_tool

description = "Search products by string query. If no products are found, the function will return an error message."
slots = [
    {
        "name": "query",
        "type": "string",
        "description": "The string query to search products, such as 'Hats'. If query is empty string, it returns all products.",
        "prompt": "In order to proceed, please provide a query for the products search.",
        "required": False,
    },
    *PAGEINFO_SLOTS
] 
outputs = [
    ShopifyOutputs.PRODUCTS_LIST,
    *PAGEINFO_OUTPUTS
]
PRODUCT_SEARCH_ERROR = "error: product search failed"
NO_PRODUCTS_FOUND_ERROR = "no products found"

errors = [
    PRODUCT_SEARCH_ERROR,
    NO_PRODUCTS_FOUND_ERROR,
    NAVIGATE_WITH_NO_CURSOR,
    NO_NEXT_PAGE,
    NO_PREV_PAGE
]

@register_tool(description, slots, outputs, lambda x: x[0] not in errors)
def search_products(query: str, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]:
        return nav[0]
    auth = authorify(kwargs)
    if auth["error"]:
        return auth["error"]
    
    try:
        with shopify.Session.temp(**auth["value"]):
            response = shopify.GraphQL().execute(f"""
                {{
                    products ({nav[0]}, query: "{query}") {{
                        nodes {{
                            id
                        }}
                        pageInfo {{
                            endCursor
                            hasNextPage
                            hasPreviousPage
                            startCursor
                        }}
                    }}
                }}
            """)
        
            data = json.loads(response)['data']['products']
            nodes = data['nodes']
            pageInfo = data['pageInfo']
            if len(nodes):
                return nodes, pageInfo
            else:
                return NO_PRODUCTS_FOUND_ERROR, ''
    
    except Exception as e:
        return PRODUCT_SEARCH_ERROR, ''