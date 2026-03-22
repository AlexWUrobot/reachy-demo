import ollama
import json
import re
import requests

class GroceryAssistant:
    def __init__(self, laptop_ip="192.168.31.5"):
        self.base_url = f"http://{laptop_ip}:8000/api" # Double check your port!
        self.search_url = f"{self.base_url}/products"
        self.add_url = f"{self.base_url}/cart/add"
        self.client_id = "global"

    def find_best_product(self, item_name):
        try:
            params = {'q': item_name, 'per_page': 1}
            response = requests.get(self.search_url, params=params, timeout=2)
            return response.json()['products'][0]['id'] if response.json().get('products') else None
        except:
            return None

    # MAKE SURE THIS NAME MATCHES EXACTLY
    def add_ingredients_to_cart(self, dish_name):
        prompt = f"List specific grocery ingredients for: {dish_name}. Return ONLY JSON: {{\"ingredients\": [\"item1\", \"item2\"]}}"
        try:
            res = ollama.chat(model='alibayram/smollm3', messages=[{'role': 'user', 'content': prompt}])
            content = res['message']['content']
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if not match: return "Could not parse ingredients."

            items = json.loads(match.group(0)).get('ingredients', [])
            added_count = 0
            for item in items:
                p_id = self.find_best_product(item)
                if p_id:
                    requests.post(self.add_url, json={"product_id": p_id, "qty": 1}, headers={"X-Client-Id": self.client_id})
                    added_count += 1
            return f"Success! Added {added_count} items for {dish_name} to your cart."
        except Exception as e:
            return f"Error: {str(e)}"