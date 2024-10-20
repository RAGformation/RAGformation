import requests

def call_rag_endpoint(user_query):
    url = 'https://chubby-jeanie-ragformation-8a33f1cc.koyeb.app/api/chat/request'
    headers = {'Content-Type': 'application/json'}
    payload = {
        "messages": [
            {
                "role": "user",
                "content": user_query
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to reach RAG endpoint. Status code: {response.status_code}"}