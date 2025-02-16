from typing import Any, Dict

from arklex.env.tools.tools import register_tool

# Customer API
from arklex.env.tools.shopify.utils_slots import ShopifySlots, ShopifyOutputs
from arklex.env.tools.shopify.utils import *
from arklex.env.tools.shopify.auth_utils import *

description = "Find user id by refresh token. If the user is not found, the function will return an error message."
slots = [
    ShopifySlots.REFRESH_TOKEN,
]
outputs = [
    ShopifyOutputs.USER_ID
]

USER_NOT_FOUND_ERROR = "error: user not found"
errors = [AUTH_ERROR, USER_NOT_FOUND_ERROR]

@register_tool(description, slots, outputs, lambda x: x not in errors or not x.startswith("error: "))
def get_user_id(refresh_token) -> str:
    try:
        return get_id(refresh_token)
    except Exception:
        return USER_NOT_FOUND_ERROR