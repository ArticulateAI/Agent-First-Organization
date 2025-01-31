from typing import Any, Dict
import json

from agentorg.env.tools.tools import register_tool

from agentorg.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from agentorg.env.tools.shopify.utils_nav import *

# Admin API
import shopify

description = "Get the details of a user with Admin API."
slots = [
    ShopifySlots.USER_ID,
    *PAGEINFO_SLOTS
]
outputs = [
    ShopifyOutputs.USER_DETAILS,
    *PAGEINFO_OUTPUTS
]

USER_NOT_FOUND_ERROR = "error: user not found"
errors = [USER_NOT_FOUND_ERROR]


@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_user_details_admin(user_id: str, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]:
        return nav[0]
    
    try:
        response = shopify.GraphQL().execute(f"""
            {{
                customer(id: "{user_id}")  {{ 
                    firstName
                    lastName
                    email
                    phone
                    numberOfOrders
                    amountSpent {{
                        amount
                        currencyCode
                    }}
                    createdAt
                    updatedAt
                    note
                    verifiedEmail
                    validEmailAddress
                    tags
                    lifetimeDuration
                    defaultAddress {{
                        formattedArea
                        address1
                    }}
                    addresses {{
                        address1
                    }}
                    orders ({nav[0]}) {{
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
            }}
        """)
        data = json.loads(response)['data']['customer']
        pageInfo = data['orders']['pageInfo']
        return data, pageInfo

    except Exception:
        return USER_NOT_FOUND_ERROR