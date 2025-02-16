from arklex.env.tools.tools import register_tool
from arklex.env.tools.shopify.auth import *

description = "Get refresh token of customer through the Auth process."
slots = []
outputs = [
    {
        "name": "refresh_token",
        "type": "str",
        "description": "customer's shopify refresh_token retrieved from authenticating",
    },
]

REFRESH_TOKEN_ERROR = "error: refresh token error"
errors = [REFRESH_TOKEN_ERROR]

@register_tool(description, slots, outputs, lambda x: x not in errors)
def get_order() -> str:
    try:
        return authenticate()
    except Exception as e:
        return REFRESH_TOKEN_ERROR