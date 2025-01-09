PAGEINFO_SLOTS = [
    {
        "name": "limit",
        "type": "int",\
        "value": 10,
        "description": "Maximum number of catalogs to show per query.",
        "prompt": "",
        "required": False
    },
    {
        "name": "navigate",
        "type": "string",
        "description": "navigate relative to previous view. 'next' to search after previous view, 'prev' to search before the previous view. 'stay' or None to remain.'",
        "prompt": "",
        "required": False
    },
    {
        "name": "pageInfo",
        "type": "string",
        "description": "The previous pageInfo object, such as \"{'endCursor': 'eyJsYXN0X2lkIjo3Mjk2NTgxODk0MjU3LCJsYXN0X3ZhbHVlIjoiNzI5NjU4MTg5NDI1NyJ9', 'hasNextPage': True, 'hasPreviousPage': False, 'startCursor': 'eyJsYXN0X2lkIjo3Mjk2NTgwODQ1NjgxLCJsYXN0X3ZhbHVlIjoiNzI5NjU4MDg0NTY4MSJ9'}\"",
        "prompt": "",
        "required": False
    },
]
    
PAGEINFO_OUTPUTS = [
    {
        "name": "pageInfo",
        "type": "string",
        "description": "Current pageInfo object, such as  \"{'endCursor': 'eyJsYXN0X2lkIjo3Mjk2NTgxODk0MjU3LCJsYXN0X3ZhbHVlIjoiNzI5NjU4MTg5NDI1NyJ9', 'hasNextPage': True, 'hasPreviousPage': False, 'startCursor': 'eyJsYXN0X2lkIjo3Mjk2NTgwODQ1NjgxLCJsYXN0X3ZhbHVlIjoiNzI5NjU4MDg0NTY4MSJ9'}\""
    }
]

NAVIGATE_WITH_NO_CURSOR = "error: cannot navigate without reference cursor"
NO_NEXT_PAGE = "error: no more pages after"
NO_PREV_PAGE = "error: no more pages before"
    