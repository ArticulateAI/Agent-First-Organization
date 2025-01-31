from typing import Any, Dict

from agentorg.env.tools.tools import register_tool

# general GraphQL navigation utilities
from agentorg.env.tools.shopify.utils_nav import *

# Customer API
from agentorg.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from agentorg.env.tools.shopify.utils import *
from agentorg.env.tools.shopify.auth_utils import *

description = "Get the status and details of an order."
slots = [
    ShopifySlots.REFRESH_TOKEN,
    ShopifySlots.ORDER_ID,
    *PAGEINFO_SLOTS
]
outputs = [
    ShopifyOutputs.ORDERS_DETAILS,
    *PAGEINFO_OUTPUTS
]

ORDERS_NOT_FOUND = "error: order not found"
errors = [ORDERS_NOT_FOUND]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_order(refresh_token, order_id: str, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]: 
        return nav[0]
    
    try:
        body = f'''
            query {{ 
                order (id: "{order_id}") {{ 
                    id
                    name
                    totalPrice {{
                        amount
                    }}
                    lineItems({nav[0]}) {{
                        nodes {{
                            id
                            name
                            quantity
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
        '''
        try:
            auth = {'Authorization': get_access_token(refresh_token)}
        except:
            return AUTH_ERROR
        
        try:
            response = make_query(customer_url, body, {}, customer_headers | auth)['data']['order']
        except Exception as e:
            return f"error: {e}"
        
        pageInfo = response['lineItems']['pageInfo']
        return response, pageInfo
    except Exception as e:
        return ORDERS_NOT_FOUND