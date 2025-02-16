import json
from typing import Any, Dict
import shopify

# general GraphQL navigation utilities
from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.shopify.utils_nav import *

from arklex.env.tools.tools import register_tool

description = "Get the details of collection with a preview of the inventory from a list of collections."
slots = [
    ShopifySlots.COLLECTION_IDS,
    *PAGEINFO_SLOTS
]
outputs = [
    ShopifyOutputs.COLLECTIONS_DETAILS,
    *PAGEINFO_OUTPUTS
]
COLLECTION_NOT_FOUND = "error: collection not found"
errors = [COLLECTION_NOT_FOUND]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def preview_collections(collection_ids: list, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]:
        return nav[0]
    
    try:
        ids = ' OR '.join(f'id:{cid.split("/")[-1]}' for cid in collection_ids)
        response = shopify.GraphQL().execute(f"""
            {{
                collections ({nav[0]}, query:"{ids}") {{
                    nodes {{
                        title
                        description
                        productsCount {{
                            count
                        }}
                        products (first: 5) {{
                            nodes {{
                                title
                                description
                                id
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
        results = json.loads(response)['data']
        response = results['collections']["nodes"]
        pageInfo = results['collections']['pageInfo']
        return response, pageInfo
    except Exception as e:
        return COLLECTION_NOT_FOUND