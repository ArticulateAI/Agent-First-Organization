from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.shopify.utils_cart import *
from arklex.env.tools.shopify.utils_nav import *
from arklex.env.tools.shopify.utils import make_query

from arklex.env.tools.tools import register_tool

description = "Removes a items from cart based on line ids"
slots = [
    ShopifySlots.CART_ID,
    ShopifySlots.UPDATE_LINE_ITEM,
]
outputs = []

CART_UPDATE_ITEM_ERROR = "error: products could not be updated to cart"
errors = [CART_UPDATE_ITEM_ERROR]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def cart_update_items(cart_id, items):
    try:
        query = '''
        mutation cartLinesUpdate($cartId: ID!, $lines: [CartLineUpdateInput!]!) {
            cartLinesUpdate(cartId: $cartId, lines: $lines) {
                cart {
                    checkoutUrl
                }
            }
        }
        '''
        
        lines = []
        for i in items:
            lineItem = {'id': i[0]}
            if i[1]:
                lineItem['merchandiseId'] = i[1]
            if i[2]:
                lineItem['quantity'] = i[2]
            lines.append(lineItem)
        
        variable = {
            "cartId": cart_id,
            "lines": lines
        }
        make_query(cart_url, query, variable, cart_headers)
        return 
    except:
        return CART_UPDATE_ITEM_ERROR