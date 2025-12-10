from moralis import evm_api
import requests
import pygsheets

#API KEY from API Provider
api_key = ""  
# Desired wallet address to track 
wallet_address = ""
#Path to google serve account json key file
service_file = r""

#Google Sheet Information
sheetname = "CryptoSheetQuote"
worksheet_title = "Sheet1"
gc = pygsheets.authorize(service_file=service_file)
sh = gc.open(sheetname)
wks = sh.worksheet_by_title(worksheet_title)
wks.clear(start="A1", end="Z")

# ------------- Moralis API Setup ---------------------
params_base = {"chain": "arbitrum", "address": wallet_address}
WETH_ADDRESS = "0x82af49447d8a07e3bd95bd0d56f35241523fbab1".lower()
NATIVE_ETH_ADDRESS = "0x0000000000000000000000000000000000000000"

#ETH balance on Arbitrum
native = evm_api.balance.get_native_balance(
    api_key=api_key,
    params=params_base,
)
native_balance_wei = int(native["balance"])
native_balance_eth = native_balance_wei / (10 ** 18)


#All coins (Not filtered)
token_Data = evm_api.token.get_wallet_token_balances(
    api_key=api_key,
    params=params_base,
)

# 3) fetch WETH balance by address
weth_list = evm_api.token.get_wallet_token_balances(
    api_key=api_key,
    params={
        "address": wallet_address,
        "chain": "arbitrum",
        "token_addresses": [WETH_ADDRESS],
    },
)
weth_token = weth_list[0] if weth_list else None

# "Total ETH Balance" -> This fetches the price of eth on arbitrum 
price_result = evm_api.token.get_token_price(
    api_key=api_key,
    params={
        "address": WETH_ADDRESS,
        "chain": "arbitrum",
    },
)
eth_price_usd = price_result["usdPrice"]
eth_value_usd = native_balance_eth * eth_price_usd

# Refresh google sheet
def update_sheet_header():
    wks.update_value("A1", "Wallet Address")
    wks.update_value("A4", "ETH Balance")
    wks.update_value("A5", round(native_balance_eth, 6))
    wks.update_value("A6", "ETH Value to USD")
    wks.update_value("A7", f"${round(eth_value_usd, 2)}")
    wks.update_value("C1", "Tokens")
    wks.update_value("D1", "Symbol")
    wks.update_value("E1", "Quantity")
    wks.update_value("F1", "Token Address")
    wks.update_value("A2", wallet_address)
    
update_sheet_header()

#retrieves the token addresses for all tokens in the wallet
y=2
for i in token_Data:
    token_contract_address = i['token_address']
    y += 1

# convert_balance_to_readable takes the quantity of each coin and turns it into a readable number
decimal_Numbers = 0
def convert_balance_to_readable(i, decimal_Numbers):
    for i in token_Data:
        decimal_Numbers = i['decimals']
    if decimal_Numbers is None:
        return None  
    return float(i['balance']) / (10 ** decimal_Numbers)

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