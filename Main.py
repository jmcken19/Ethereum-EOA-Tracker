from moralis import evm_api
from moralis import sol_api
import requests
import pygsheets
import json


api_key = ""
wallet_address = ''
url = "https://deep-index.moralis.io/api/v2/erc20/prices?chain=arbitrum"

service_file = ''
gc = pygsheets.authorize(service_file=service_file)
sheetname = 'CryptoSheetQuote'
sh = gc.open(sheetname)
wks = sh.worksheet_by_title('Sheet1')
wks.clear(start='A1', end='Z') 


params = {"chain": "arbitrum", "address": wallet_address}
result = evm_api.token.get_wallet_token_balances(api_key=api_key, params=params) 
response = requests.get("https://api.exchangerate-api.com/v4/latest/USD") 
exchange_rates = response.json()["rates"]
token_Data = evm_api.token.get_wallet_token_balances(api_key=api_key, params=params)
token_Data_Length = len(token_Data)

#retrieves the token addresses for all tokens in the wallet
y=2
for i in token_Data:
    token_contract_address = i['token_address']
    y += 1


payload = {
  "tokens": [
    {
      "token_address": token_contract_address
    }
  ]
}
headers = {
  "Accept": "application/json",
  "Content-Type": "application/json",
  "X-API-Key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6ImJhM2E0MzgzLTc3NDYtNDRiMC1iMzM3LWI2ZDFiYzFjMGU4NyIsIm9yZ0lkIjoiMzQ1NjUzIiwidXNlcklkIjoiMzU1MzE2IiwidHlwZSI6IlBST0pFQ1QiLCJ0eXBlSWQiOiJiNmUzNjQ2Ny1iMTVhLTQyZjAtYWU1Ny0xYzY4ZDNkMDdlYmEiLCJpYXQiOjE2ODgwOTk1NjUsImV4cCI6NDg0Mzg1OTU2NX0.fhpSrYTpSXyvTWIYG--Mqs5ac-mjr6TZGpVB9suYBJs"
} 
response = requests.request("POST", url, json=payload, headers=headers)
response_data = json.loads(response.text)

# convert_balance_to_readable takes the quantity of each coin and turns it into a readable number
decimal_Numbers = 0
def convert_balance_to_readable(i, decimal_Numbers):
    for i in token_Data:
        decimal_Numbers = i['decimals']
    if decimal_Numbers is None:
        return None  
    return float(i['balance']) / (10 ** decimal_Numbers)

# updates the google sheet
def update_sheet():
    wks.update_value('A1', 'Wallet Address')
    wks.update_value('C1', 'Tokens')
    wks.update_value('D1', 'Symbol')
    wks.update_value('E1', 'Quantity')
    wks.update_value('F1', 'Token Address')
    wks.update_value('A2',  wallet_address)      
update_sheet()

# iterates through the array and pulls out all the tokens, if it finds a token it will print it in the google sheet, else it will skip
y = 2  
for token in token_Data:
    wallet_tokens = token['name']
    token_spam = token.get('possible_spam')  
    wks.update_value(f"C{y}", wallet_tokens)
    y += 1
    
    
# iterates through the array and pulls out all the tokens, If it finds a token it will print it in the Google sheet, else it will skip
y = 2  
for symbols in token_Data:
    wallet_symbols = symbols['symbol']
    wks.update_value(f"D{y}",  wallet_symbols)
    y += 1

# fetches the quantity from the array token data
y = 2  
for token in token_Data:
    token_Decimals = token.get('decimals')  
    if token_Decimals is not None:
        token_Price = float(token['balance']) / (10 ** token_Decimals)
        wks.update_value(f"E{y}", token_Price)
        y += 1
    else:
        print(f"Skipping token at row {y}")

# Retrieves token addresses again and prints them in the google sheet
y=2
for i in token_Data:
    token_contract_address = i['token_address']
    wks.update_value(f"F{y}",  token_contract_address)
    y += 1
print("Google sheet sucessufully updated")