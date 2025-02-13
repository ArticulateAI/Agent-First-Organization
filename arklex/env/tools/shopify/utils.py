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