from agentorg.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from agentorg.env.tools.shopify.utils_cart import *
from agentorg.env.tools.shopify.utils_nav import *

from agentorg.env.tools.tools import register_tool

description = "Get cart information"
slots = [
    ShopifySlots.CART_ID,
    *PAGEINFO_SLOTS
]
outputs = [
    *PAGEINFO_OUTPUTS
]
CART_NOT_FOUND_ERROR = "error: cart not found"
errors = [CART_NOT_FOUND_ERROR]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_cart(cart_id, **kwargs):
    nav = cursorify(kwargs)
    if not nav[1]:
        return nav[0]
    
    # try:
    query = f'''
        query ($id: ID!) {{ 
            cart(id: $id) {{
                id
                checkoutUrl
                lines ({nav[0]}) {{
                    nodes {{
                        id
                        quantity
                        merchandise {{
                            ... on ProductVariant {{
                                id
                                title
                                product {{
                                    title
                                    id
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
    variable = {
        "id": cart_id,
    }
    response = make_query(cart_url, query, variable, cart_headers)['data']['cart']
    pageInfo = response['lines']['pageInfo']
    return response, pageInfo
    
    # except Exception as e:
    #     return CART_NOT_FOUND_ERROR