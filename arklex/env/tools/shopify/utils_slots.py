class ShopifySlots:
    def to_list(baseSlot: dict):
        slot = baseSlot.copy()
        slot["name"] += 's'
        slot["items"] = {"type": baseSlot["type"]}
        slot["type"] = "array"
        slot["description"] = f"List of {slot['name']}. {slot['description']}"
        return slot
    
    USER_ID = {
        "name": "user_id",
        "type": "string",
        "description": "The user id, such as 'gid://shopify/Customer/13573257450893'.",
        "prompt": "In order to proceed, Could you please provide the user id?",
        "required": True,
    }
    
    REFRESH_TOKEN = {
        "name": "refresh_token",
        "type": "str",
        "description": "customer's shopify refresh_token retrieved from authenticating",
        "prompt": "",
        "required": True
    }
    
    PRODUCT_ID = {
        "name": "product_id",
        "type": "string",
        "description": "The product id, such as 'gid://shopify/Product/2938501948327'.", # If there is only 1 product, return in list with single item. If there are multiple product ids, please return all of them in a list.",
        "prompt": "In order to proceed, please provide the product id.",
        "required": True,
    }
    PRODUCT_IDS = to_list(PRODUCT_ID)
    
    ORDER_ID = {
        "name": "order_id",
        "type": "array",
        "description": "The order id, such as gid://shopify/Order/1289503851427.",
        "prompt": "Please provide the order id to get the details of the order.",
        "required": True,
    }
    ORDERS_ID = to_list(ORDER_ID)
    
    COLLECTION_ID = {
        "name": "collection_id",
        "type": "str",
        "description": "The collection id, such as 'gid://shopify/Collection/2938501948327'.",
        "prompt": "",
        "required": True,
    }
    COLLECTION_IDS = to_list(COLLECTION_ID)
    
    CART_ID = {
        "name": "cart_id",
        "type": "str",
        "description": "The cart id, such as 'gid://shopify/Cart/2938501948327'.",
        "prompt": "",
        "required": True,
    }
    
    LINE_ID = {
        "name": "line_id",
        "type": "str",
        "description": "The line id for a line entry in the cart such as 'gid://shopify/CartLine/b3dbff2e-4e9a-4ce0-9f15-5fa8f61882e1?cart=Z2NwLXVzLWVhc3QxOjAxSkpDTjBQSDVLR1JaRkZHMkE3UlZSVjhX'",
        "prompt": "",
        "required": True,
    }
    LINE_IDS = to_list(LINE_ID)
    
    ADD_LINE_ITEM = {
        "name": "items",
        "type": "list",
        "items": "tuple",
        "description": "list of (item_id, quantity) tuples of lineItem to add to the cart such as [('gid://shopify/ProductVariant/41552094527601', 5), ('gid://shopify/ProductVariant/41552094494833', 10)].",
        "prompt": "",
        "required": True,
    }
    
    UPDATE_LINE_ITEM = {
        "name": "line_ids",
        "type": "list",
        "items": "str",
        "description": "list of (line_id, item_id, quantity) tuples of lineItem to add to the cart such as [('gid://shopify/CartLine/db5cb3dd-c830-482e-88cd-99afe8eafa3f?cart=Z2NwLXVzLWVhc3QxOjAxSkpEM0JLNU1KMUI2UFRYRTNFS0NNTllW', None, 69)]",
        "prompt": "",
        "required": True,
    }
    
        
    

class ShopifyOutputs:
    USER_ID = {
        "name": "user_id",
        "type": "string",
        "description": "The user id of the user. such as 'gid://shopify/Customer/13573257450893'.",
    }
    
    USER_DETAILS = {
        "name": "user_details",
        "type": "dict",
        "description": "The user details of the user. such as '{\"firstName\": \"John\", \"lastName\": \"Doe\", \"email\": \"example@gmail.com\"}'."
    }
    
    PRODUCTS_LIST = {
        "name": "products_list",
        "type": "dict",
        "description": "A list of up to limit number of products that satisfies the query. Such as \"[{'id': 'gid://shopify/Product/7296580845681'}, {'id': 'gid://shopify/Product/7296580878449'}, {'id': 'gid://shopify/Product/7296581042289'}]\"",
    }
    
    PRODUCTS_DETAILS = {
        "name": "product_details",
        "type": "dict",
        "description": "The product details of each products. such as \"[{'id': 'gid://shopify/Product/7296581894257', 'title': 'Nordic Bedding Set', 'description': 'size: 48 cm', 'totalInventory': 3, 'category': 'bedding', 'variants': {'nodes': [{'price': '50.99'}]}}, {'id': 'gid://shopify/Product/7296582123633', 'title': 'Ocean Theme Bedding ', 'description': 'Grade A', 'totalInventory': 0, 'category': 'bedding', 'variants': {'nodes': [{'price': '76.99'}]}}]\".",
    }
    
    ORDERS_DETAILS = {
        "name": "order_details",
        "type": "dict",
        "description": "The order details of the order. such as '{\"id\": \"gid://shopify/Order/1289503851427\", \"name\": \"#1001\", \"totalPriceSet\": {\"presentmentMoney\": {\"amount\": \"10.00\"}}, \"lineItems\": {\"nodes\": [{\"id\": \"gid://shopify/LineItem/1289503851427\", \"title\": \"Product 1\", \"quantity\": 1, \"variant\": {\"id\": \"gid://shopify/ProductVariant/1289503851427\", \"product\": {\"id\": \"gid:////shopify/Product/1289503851427\"}}}]}}'.",
    }
    
    COLLECTIONS_DETAILS = {
        "name": "cart",
        "type": "dict",
        "description": "The collection details of the collection. such as \"['{'title': 'Beddings and Pillows', 'description': '', 'productsCount': {'count': 6}, 'products': {'nodes': [{'id': 'gid://shopify/Product/7296582090865'}, {'id': 'gid://shopify/Product/7296582025329'}, {'id': 'gid://shopify/Product/7296581894257'}, {'id': 'gid://shopify/Product/7296581763185'}, {'id': 'gid://shopify/Product/7296581337201'}], 'pageInfo': {'hasNextPage': true}}}', '{'title': 'Bedding', 'description': '', 'productsCount': {'count': 4}, 'products': {'nodes': [{'id': 'gid://shopify/Product/7296582123633'}, {'id': 'gid://shopify/Product/7296582090865'}, {'id': 'gid://shopify/Product/7296581894257'}, {'id': 'gid://shopify/Product/7296581763185'}], 'pageInfo': {'hasNextPage': false}}}']\""
    }