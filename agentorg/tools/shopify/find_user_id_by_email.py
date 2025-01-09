from typing import Any, Dict
import json

import shopify

from agentorg.tools.tools import register_tool

description = "Find user id by email. If the user is not found, the function will return an error message."
slots = [
    {
        "name": "email",
        "type": "string",
        "description": "The email of the user, such as 'something@example.com'.",
        "prompt": "In order to proceed, please provide the email for identity verification.",
        "required": True,
    }
]
outputs = [
    {
        "name": "user_id",
        "type": "string",
        "description": "The user id of the user. such as 'gid://shopify/Customer/13573257450893'.",
    }
]

USER_NOT_FOUND_ERROR = "error: user not found"
MULTIPLE_USERS_SAME_EMAIL_ERROR = "error: there are multiple users with the same email"

@register_tool(description, slots, outputs, lambda x: x not in [USER_NOT_FOUND_ERROR, MULTIPLE_USERS_SAME_EMAIL_ERROR])
def find_user_id_by_email(email: str) -> str:
    user_id = ""
    try:
        response = shopify.GraphQL().execute(f"""
            {{
                customers (first: 10, query: "email:{email}") {{
                    edges {{
                        node {{
                            id
                        }}
                    }}
                }}
            }}
            """)
        nodes = json.loads(response)["data"]["customers"]["edges"]
        if len(nodes) == 1:
            user_id = nodes[0]["node"]["id"]
            return user_id
        else:
            return MULTIPLE_USERS_SAME_EMAIL_ERROR
    except Exception as e:
        return USER_NOT_FOUND_ERROR