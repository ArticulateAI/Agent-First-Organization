import json
from typing import Any, Dict

import shopify

# general GraphQL navigation utilities
from arklex.env.tools.shopify.utils_nav import *

# ADMIN
from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.tools import register_tool

description = "Get the inventory information and description details of a product."
slots = [
    ShopifySlots.PRODUCT_IDS,
    *PAGEINFO_SLOTS
]
outputs = [
    ShopifyOutputs.PRODUCTS_DETAILS,
    *PAGEINFO_OUTPUTS
]
PRODUCTS_NOT_FOUND = "error: product not found"
errors = [PRODUCTS_NOT_FOUND]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_products(product_ids: list, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]:
        return nav[0]

    try:
        ids = ' OR '.join(f'id:{pid.split("/")[-1]}' for pid in product_ids)
        response = shopify.GraphQL().execute(f"""
            {{
                products ({nav[0]}, query:"{ids}") {{
                    nodes {{
                        id
                        title
                        description
                        totalInventory
                        onlineStoreUrl
                        category {{
                            name
                        }}
                        variants (first: 2) {{
                            nodes {{
                                displayName
                                id
                                price
                                inventoryQuantity
                            }}
                        }}
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
        result = json.loads(response)['data']['products']
        response = result["nodes"]
        pageInfo = result["pageInfo"]
        return response, pageInfo
    except Exception as e:
        return PRODUCTS_NOT_FOUND
    
