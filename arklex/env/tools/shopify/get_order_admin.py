import json
from typing import Any, Dict
import logging


from arklex.env.tools.tools import register_tool

# general GraphQL navigation utilities
from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.shopify.utils_nav import *

# Admin API
import shopify

logger = logging.getLogger(__name__)


description = "Get the status and details of an order."
slots = [
    ShopifySlots.ORDER_ID,
    *PAGEINFO_SLOTS
]
outputs = [
    ShopifyOutputs.ORDERS_DETAILS,
    *PAGEINFO_OUTPUTS
]

ORDERS_NOT_FOUND = "error: order not found"
errors = [ORDERS_NOT_FOUND]

errors = [
    ORDERS_NOT_FOUND,
    NAVIGATE_WITH_NO_CURSOR,
    NO_NEXT_PAGE,
    NO_PREV_PAGE
]

@register_tool(description, slots, outputs)
def get_order_admin(order_id: str, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]: 
        return nav[0]
    
    try:
        response = shopify.GraphQL().execute(f"""
        {{
            order (id: "{order_id}") {{
                id
                name
                totalPriceSet {{
                    presentmentMoney {{
                        amount
                    }}
                }}
                lineItems ({nav[0]}) {{
                    nodes {{
                        id
                        title
                        quantity
                        variant {{
                            id
                            product {{
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
        }}
        """)
        results = json.loads(response)['data']['order']
        response = results['lineItems']["nodes"]
        pageInfo = results['lineItems']['pageInfo']
        return results, pageInfo
    except Exception as e:
        return ORDERS_NOT_FOUND
