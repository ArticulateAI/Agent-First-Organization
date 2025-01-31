from typing import Any, Dict

from agentorg.env.tools.tools import register_tool

# Customer API
from agentorg.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from agentorg.env.tools.shopify.utils import *
from agentorg.env.tools.shopify.auth_utils import *
from agentorg.env.tools.shopify.utils_nav import *

description = "Get the details of a user."
slots = [
    ShopifySlots.REFRESH_TOKEN,
    *PAGEINFO_SLOTS
]
outputs = [
    ShopifyOutputs.USER_DETAILS,
    *PAGEINFO_OUTPUTS
]

USER_NOT_FOUND_ERROR = "error: user not found"
errors = [USER_NOT_FOUND_ERROR]


@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_user_details(refresh_token: str, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]: 
        return nav[0]
    try:
        body = f'''
            query {{ 
                customer {{ 
                    id
                    firstName
                    lastName
                    emailAddress {{
                        emailAddress
                    }}
                    phoneNumber {{
                        phoneNumber
                    }}
                    creationDate
                    defaultAddress {{
                        formatted
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
        '''
        try:
            auth = {'Authorization': get_access_token(refresh_token)}
        except:
            return AUTH_ERROR
        
        try:
            response = make_query(customer_url, body, {}, customer_headers | auth)['data']['customer']
        except Exception as e:
            return f"error: {e}"
        
        pageInfo = response['orders']['pageInfo']
        return response, pageInfo
    
    except Exception:
        raise PermissionError