# from agentorg.tools.shopify_new.auth_utils import get_auth_link, get_refresh_token, get_access_token
# from agentorg.tools.shopify_new.auth_server import authenticate_server
from auth_utils import get_auth_link, get_refresh_token, get_access_token
from auth_server import authenticate_server

import os

def authenticate():
    auth_link = get_auth_link()
    print("Authenticate Link here: ", auth_link)
    code = authenticate_server()
    refresh_token = get_refresh_token(code)
    # access_token = get_access_token(refresh_token)
    return refresh_token

if __name__ == "__main__":
    refresh_token = authenticate()
    
    os.environ["SHOPIFY_CUSTOMER_API_REFRESH_TOKEN"] = refresh_token
    print(f"Refresh token: {refresh_token}")