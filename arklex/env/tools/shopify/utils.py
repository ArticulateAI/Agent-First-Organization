import requests
from arklex.env.tools.shopify.auth_utils import get_access_token

SHOPIFY_AUTH_ERROR = "error: missing some or all required shopify authentication parameters: shop_url, api_version, token. Please set up 'fixed_args' in the config file. For example, {'name': <unique name of the tool>, 'fixed_args': {'token': <shopify_access_token>, 'shop_url': <shopify_shop_url>, 'api_version': <Shopify API version>}}"

def authorify(kwargs):
    auth = {
        "value": {
            "domain": None,
            "version": None,
            "token": None
        },
        "error": None
    }
    auth["value"]["domain"] = kwargs.get("shop_url")
    auth["value"]["version"] = kwargs.get("api_version")
    auth["value"]["token"] = kwargs.get("token")


    
    if not auth["value"]["domain"] or not auth["value"]["version"] or not auth["value"]["token"]:
        auth["error"] = SHOPIFY_AUTH_ERROR
        return auth
    
    return auth


shop_id = 60183707761
customer_url = f'https://shopify.com/{shop_id}/account/customer/api/2025-01/graphql'

customer_headers = {
    'Content-Type': 'application/json',
    # 'Authorization': '<<token>>',
}

def make_query(url, query, variables, headers):
    """
    Make query response
    """
    request = requests.post(url, json={'query': query, 'variables': variables}, headers=headers)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))
    
def get_id(refresh_token):
    try:
        body = '''query { customer { id } } '''
        
        auth = {'Authorization': get_access_token(refresh_token)}
        response = make_query(customer_url, body, {}, customer_headers | auth)['data']['customer']['id']
        
        return response
    
    except Exception:
        raise PermissionError