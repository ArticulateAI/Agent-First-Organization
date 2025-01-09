import json
from typing import Any, Dict
import logging

import shopify

from agentorg.tools.shopify.utils import *
from agentorg.tools.tools import register_tool

logger = logging.getLogger(__name__)

description = "Get the status and details of an order."
slots = [
    {
        "name": "order_ids",
        "type": "array",
        "items": {"type": "string"},
        "description": "The order id, such as gid://shopify/Order/1289503851427. If there is only 1 order, return in list with single item. If there are multiple order ids, please return all of them in a list.",
        "prompt": "Please provide the order id to get the details of the order.",
        "required": True,
    },
    *PAGEINFO_SLOTS
]
outputs = [
    {
        "name": "order_details",
        "type": "dict",
        "description": "The order details of the order. such as '{\"id\": \"gid://shopify/Order/1289503851427\", \"name\": \"#1001\", \"totalPriceSet\": {\"presentmentMoney\": {\"amount\": \"10.00\"}}, \"lineItems\": {\"nodes\": [{\"id\": \"gid://shopify/LineItem/1289503851427\", \"title\": \"Product 1\", \"quantity\": 1, \"variant\": {\"id\": \"gid://shopify/ProductVariant/1289503851427\", \"product\": {\"id\": \"gid:////shopify/Product/1289503851427\"}}}]}}'.",
    },
    *PAGEINFO_OUTPUTS
]
EMPTY_ORDER = "error: order appears empty"
ORDER_NOT_FOUND = "error: order not found"


errors = [
    EMPTY_ORDER,
    NAVIGATE_WITH_NO_CURSOR,
    NO_NEXT_PAGE,
    NO_PREV_PAGE
]

@register_tool(description, slots, outputs)
def get_order(order_id: str, limit=10, navigate='stay', pageInfo=None) -> str:
    limit = limit or 10
    navigate = navigate or 'stay'
    logger.info(f"PARAMS: {limit, navigate, pageInfo}")
    
    nav = f'first: {limit}'
    if navigate and navigate != 'stay':
        if not pageInfo:
            return NAVIGATE_WITH_NO_CURSOR, ''
        
        if navigate == 'next':
            if not pageInfo['hasNextPage']:
                return NO_NEXT_PAGE, ''
            nav = f"first: {limit}, after: \"{pageInfo['endCursor']}\""
            
        elif navigate == 'prev': 
            if not pageInfo['hasPreviousPage']:
                return NO_PREV_PAGE, ''
            nav = f"last: {limit}, before: \"{pageInfo['startCursor']}\""
    
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
                lineItems ({nav}) {{
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
        data = json.load(response)['data']['order']
        nodes = data['lineItems']['nodes']
        pageInfo = data['pageInfo']
        if len(nodes):
            return nodes, pageInfo
        else:
            return EMPTY_ORDER, ''
    except Exception as e:
        return ORDER_NOT_FOUND, ''
