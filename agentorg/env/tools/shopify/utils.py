import requests
from agentorg.env.tools.shopify.auth_utils import get_access_token

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