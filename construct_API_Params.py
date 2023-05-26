import os
import json

class BigboxParams:
    def __init__(self):
        # Ensure the BIGBOX_API_KEY is set
        self.api_key = os.getenv('BIGBOX_API_KEY')
        if not self.api_key:
            raise ValueError("Please set the BIGBOX_API_KEY environment variable.")

        self.params = {
            'api_key': self.api_key,
            'output': 'json',
            'type': 'search',
            'include_html': 'false',
            'customer_zipcode': '98109',
            'url': ''
        }

    def construct_params(self, input_string):
        print(input_string)
        input_data = json.loads(input_string)
        
        # Required parameter
        self.params['search_term'] = input_data.get('search_term')

        # Optional parameters
        self.params['max_price'] = input_data.get('max_price')
        self.params['min_price'] = input_data.get('min_price')
        self.params['sort_by'] = input_data.get('sort_by')

        return self.params


if __name__ == "__main__":
    bot = BigboxParams()
    input_string = """
    {
        "search_term": "one-piece toilet",
        "max_price": 650,
        "min_price": 0,
        "sort_by": "price_high_to_low"
    }
    """
    params = bot.construct_params(input_string)
    print(params)
