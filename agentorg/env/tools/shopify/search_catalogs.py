import json
from typing import Any, Dict
import shopify

from agentorg.env.tools.shopify.utils import *
from agentorg.env.tools.tools import register_tool

description = "Search catalogs by string query. If no catalogs are found, the function will return an error message."
slots = [
    {
        "name": "query",
        "type": "string",
        "description": "The string query to search catalogs, such as 'Hats'. If query is empty string, it returns all catalogs.",
        "prompt": "In order to proceed, please provide a query for the catalogs search.",
        "required": False,
    },
    *PAGEINFO_SLOTS
]
outputs = [
    {
        "name": "catalogs_list",
        "type": "dict",
        "description": "A list of up to limit number of catalogs that satisfies the query. Such as \"[{'id': 'gid://shopify/Catalog/7296580845681'}, {'id': 'gid://shopify/Catalog/7296580878449'}, {'id': 'gid://shopify/Catalog/7296581042289'}]\"",
    }
] + PAGEINFO_OUTPUTS
CATALOG_SEARCH_ERROR = "error: product search failed"
NO_CATALOGS_FOUND_ERROR = "no catalogs found"

errors = [
    SHOPIFY_AUTH_ERROR,
    CATALOG_SEARCH_ERROR,
    NO_CATALOGS_FOUND_ERROR,
    NAVIGATE_WITH_NO_CURSOR,
    NO_NEXT_PAGE,
    NO_PREV_PAGE
]

@register_tool(description, slots, outputs, lambda x: x[0] not in errors)
def search_catalogs(query: str, limit=10, navigate='stay', pageInfo=None, **kwargs) -> str:
    limit = limit or 10
    
    shop_url = kwargs.get("shop_url")
    api_version = kwargs.get("api_version")
    token = kwargs.get("token")

    if not shop_url or not api_version or not token:
        return SHOPIFY_AUTH_ERROR, ''
    
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
        with shopify.Session.temp(shop_url, api_version, token):
            response = shopify.GraphQL().execute(f"""
                {{
                    catalogs ({nav}, query: "{query}") {{
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
            """)
        
        data = json.loads(response)['data']['catalogs']
        nodes = data['nodes']
        pageInfo = data['pageInfo']
        if len(nodes):
            return nodes, pageInfo
        else:
            return NO_CATALOGS_FOUND_ERROR, ''
    
    except Exception as e:
        return CATALOG_SEARCH_ERROR, ''