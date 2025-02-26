"""
This module is currently inactive.

It is reserved for future use and may contain experimental or planned features (dependence on shopping cart id).

Status:
    - Not in use (as of 2025-02-18)
    - Intended for future feature expansion

Module Name: cart_add_items

This file contains the code for adding items to a shopping cart.
"""
from arklex.env.exceptions import FunctionFailureError
from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.shopify.utils_cart import *
from arklex.env.tools.shopify.utils_nav import *

from arklex.env.tools.tools import register_tool

description = "Get the inventory information and description details of a product."
slots = [
    ShopifySlots.CART_ID,
    ShopifySlots.ADD_LINE_ITEM
]
outputs = []
CART_ADD_ITEM_ERROR = "error: products could not be added to cart"
errors = [CART_ADD_ITEM_ERROR]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def cart_add_items(cart_id, items: list[tuple]):
    try:
        query = '''
        mutation cartLinesAdd($cartId: ID!, $lines: [CartLineInput!]!) {
            cartLinesAdd(cartId: $cartId, lines: $lines) {
                cart {
                    checkoutUrl
                }
            }
        }
        '''
        
        variable = {
            "cartId": cart_id,
            "lines": [
                {"merchandiseId": item[0],
                    "quantity": item[1] if len(item) >= 1 else 1
                } for item in items
            ]
        }
        make_query(cart_url, query, variable, cart_headers)
        return
    except:
        raise FunctionFailureError(CART_ADD_ITEM_ERROR)