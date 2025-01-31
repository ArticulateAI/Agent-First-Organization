import json
from typing import Any, Dict
import shopify

# general GraphQL navigation utilities
from agentorg.env.tools.shopify.utils_nav import *

from agentorg.env.tools.tools import register_tool

description = "Search collections by string query. If no collections are found, the function will return an error message."
slots = [
    {
        "name": "query",
        "type": "string",
        "description": "The string query to search collections, such as 'Hats'. If query is empty string, it returns all collections.",
        "prompt": "In order to proceed, please provide a query for the collections search.",
        "required": False,
    },
    *PAGEINFO_SLOTS
]
outputs = [
    {
        "name": "collections_list",
        "type": "dict",
        "description": "A list of up to limit number of collections that satisfies the query. Such as \"[{'id': 'gid://shopify/Collection/7296580845681'}, {'id': 'gid://shopify/Collection/7296580878449'}, {'id': 'gid://shopify/Collection/7296581042289'}]\"",
    },
    *PAGEINFO_OUTPUTS
]
COLLECTION_SEARCH_ERROR = "error: collection search failed"
NO_COLLECTIONS_FOUND_ERROR = "no collections found"

errors = [
    COLLECTION_SEARCH_ERROR,
    NO_COLLECTIONS_FOUND_ERROR,
    NAVIGATE_WITH_NO_CURSOR,
    NO_NEXT_PAGE,
    NO_PREV_PAGE
]

@register_tool(description, slots, outputs, lambda x: x[0] not in errors)
def search_collections(query: str, **kwargs) -> str:
    nav = cursorify(kwargs)
    if not nav[1]:
        return nav[0]
    
    try:
        response = shopify.GraphQL().execute(f"""
            {{
                collections ({nav[0]}, query: "{query}") {{
                    nodes {{
                        title
                        description
                        productsCount {{
                            count
                        }}
                        products (first: 5) {{
                            nodes {{
                                title
                                description
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
        """)
        data = json.loads(response)  ['data']['collections']
        nodes = data['nodes']
        pageInfo = data['pageInfo']
        if len(nodes):
            return nodes, pageInfo
        else:
            return NO_COLLECTIONS_FOUND_ERROR, ''
    
    except Exception as e:
        return COLLECTION_SEARCH_ERROR, ''