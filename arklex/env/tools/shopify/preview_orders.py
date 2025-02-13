from typing import Any, Dict

from arklex.env.tools.tools import register_tool

# general GraphQL navigation utilities
from arklex.env.tools.shopify.utils_nav import *

# Customer API
from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.shopify.utils import *
from arklex.env.tools.shopify.auth_utils import *

description = "Give a preview of customer's recent orders."
slots = [
    ShopifySlots.REFRESH_TOKEN,
    *PAGEINFO_SLOTS
]
outputs = [
    ShopifyOutputs.ORDERS_DETAILS,
    *PAGEINFO_OUTPUTS
]

USER_NOT_FOUND_ERROR = "error: user not found"
errors = [USER_NOT_FOUND_ERROR]


@register_tool(description, slots, outputs, lambda x: x not in errors)
def preview_orders(refresh_token: str, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]: 
        return nav[0]
    
    try:
        body = f'''
            query {{ 
                customer {{ 
                    orders ({nav[0]}) {{
                        nodes {{
                            id
                            name
                            updatedAt
                            statusPageUrl
                            totalPrice {{
                                amount
                            }}
                            lineItems (first: 5) {{
                                nodes {{
                                    name
                                    quantity
                                    totalPrice {{
                                        amount
                                    }}
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
        '''
        try:
            auth = {'Authorization': get_access_token(refresh_token)}
        except:
            return AUTH_ERROR, None
        
        try:
            response = make_query(customer_url, body, {}, customer_headers | auth)['data']['customer']['orders']
        except Exception as e:
            return f"error: {e}"
        
        pageInfo = response['pageInfo']
        return response['nodes'], pageInfo
        
    except Exception:
        raise PermissionError 
