import requests
import sys
import json


API_KEY = ""

#URL = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={API_KEY}"

def display(Tickers):
    
    for T in Tickers:
        URL = f"https://finnhub.io/api/v1/quote?symbol={T}&token={API_KEY}"
        response = requests.get(URL)
        data = response.json()
        print(f"{T} ${data['c']}")
    pass

if __name__ == "__main__":
    if(len(sys.argv) < 4):
        sys.exit(1)
    display(sys.argv[2:])
