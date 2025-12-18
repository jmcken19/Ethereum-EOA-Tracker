from moralis import evm_api
import requests
import pygsheets
from decimal import Decimal, ROUND_HALF_UP
import os
import re


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

gc = pygsheets.authorize(service_file=service_file)
sh = gc.open(sheetname)
wks = sh.worksheet_by_title(worksheet_title)
wks.clear(start="A1", end="Z")

# =========================
# CONSTANTS
# =========================
ETHERSCAN_V2_URL = "https://api.etherscan.io/v2/api"
ARBITRUM_CHAIN_ID = "42161"
ARBISCAN_ADDRESS_URL = "https://arbiscan.io/address/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


# =========================
# SMALL UTILS
# =========================
def money_2dp(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def parse_decimal_number(s: str) -> Decimal:
    s = s.strip().replace(",", "")
    if s == "":
        return Decimal("0")
    return Decimal(s)

def set_status(wks, status_text: str):
    """
    Writes status info onto the sheet in a consistent place.
    """
    try:
        wks.update_value("A11", "Status")
        wks.update_value("A12", status_text)
    except Exception:
        pass


# =========================
# ETHERSCAN V2 (MATCH ARBISCAN ETH BALANCE + ETH PRICE)
# =========================
def etherscan_v2_get_native_balance_wei(address: str) -> int:
    key = os.getenv("ETHERSCAN_API_KEY")
    if not key:
        raise RuntimeError('Missing ETHERSCAN_API_KEY env var. In PowerShell:  $env:ETHERSCAN_API_KEY="YOUR_KEY"')

    r = requests.get(
        ETHERSCAN_V2_URL,
        headers=HEADERS,
        params={
            "chainid": ARBITRUM_CHAIN_ID,
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": key,
        },
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return int(data["result"])

def etherscan_v2_get_eth_usd_price() -> Decimal:
    key = os.getenv("ETHERSCAN_API_KEY")
    if not key:
        raise RuntimeError('Missing ETHERSCAN_API_KEY env var. In PowerShell:  $env:ETHERSCAN_API_KEY="YOUR_KEY"')

    r = requests.get(
        ETHERSCAN_V2_URL,
        headers=HEADERS,
        params={
            "chainid": ARBITRUM_CHAIN_ID,
            "module": "stats",
            "action": "ethprice",
            "apikey": key,
        },
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    return Decimal(str(data["result"]["ethusd"]))


# =========================
# ARBISCAN ERC-20 HOLDINGS (to match Arbiscan $ totals and @ prices)
# =========================
def arbiscan_get_erc20_holdings(address: str) -> list[dict]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("Missing dependency: bs4. Install it with:  pip install beautifulsoup4")

    url = f"{ARBISCAN_ADDRESS_URL}{address}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    html = r.text

    lo = html.lower()
    start = lo.find("erc-20 tokens")
    if start == -1:
        raise RuntimeError("Could not find 'ERC-20 Tokens' section on Arbiscan page (layout changed or blocked).")

    end = lo.find("nft tokens", start)
    block = html[start:end if end != -1 else None]

    soup = BeautifulSoup(block, "html.parser")
    anchors = soup.find_all("a", href=re.compile(r"^/token/0x[a-fA-F0-9]{40}"))

    holdings: list[dict] = []

    line_re = re.compile(
        r"^(?P<name>.+?)\s+\((?P<sym_paren>.+?)\)\s+(?P<qty>[\d,\.Ee+\-]+)\s+(?P<sym2>\S+)\s+\$(?P<usd>[\d,]+\.\d{2})(?:\s+@(?P<price>[\d,]+\.\d+))?$"
    )

    for a in anchors:
        href = a.get("href", "")
        m_addr = re.search(r"/token/(0x[a-fA-F0-9]{40})", href)
        if not m_addr:
            continue
        token_addr = m_addr.group(1).lower()

        text = " ".join(a.get_text(" ", strip=True).split())
        m = line_re.match(text)
        if not m:
            continue

        usd_total = parse_decimal_number(m.group("usd"))

        holdings.append(
            {
                "name": m.group("name").strip(),
                "symbol": (m.group("sym2").strip() if m.group("sym2") else m.group("sym_paren").strip()),
                "qty_str": m.group("qty").strip(),
                "token_address": token_addr,
                "usd_price": (parse_decimal_number(m.group("price")) if m.group("price") else None),
                "usd_total": usd_total,
            }
        )

    return holdings


# =========================
# GOOGLE SHEET SETUP
# =========================
gc = pygsheets.authorize(service_file=service_file)
sh = gc.open(sheetname)
wks = sh.worksheet_by_title(worksheet_title)
wks.clear(start="A1", end="Z")


# =========================
# ETH (MATCH ARBISCAN)
# =========================
native_balance_wei = etherscan_v2_get_native_balance_wei(wallet_address)
native_balance_eth = Decimal(native_balance_wei) / (Decimal(10) ** Decimal(18))

eth_price_usd = etherscan_v2_get_eth_usd_price()
eth_value_usd_precise = native_balance_eth * eth_price_usd
eth_value_usd = money_2dp(eth_value_usd_precise)


# =========================
# WRITE SHEET HEADER
# =========================
def update_sheet_header():
    wks.update_value("A1", "Wallet Address")
    wks.update_value("A2", wallet_address)

    wks.update_value("A4", "ETH Balance")
    wks.update_value("A5", str(native_balance_eth))

    wks.update_value("A6", "ETH Value to USD")
    if eth_value_usd == Decimal("0.00") and eth_value_usd_precise > Decimal("0"):
        wks.update_value("A7", "Less Than $0.01")
    else:
        wks.update_value("A7", f"${eth_value_usd:,}")

    wks.update_value("A8", "ETH Price Used (USD)")
    wks.update_value("A9", str(eth_price_usd))

    wks.update_value("C1", "Tokens")
    wks.update_value("D1", "Symbol")
    wks.update_value("E1", "Quantity")
    wks.update_value("F1", "Token Address")
    wks.update_value("G1", "USD Price")
    wks.update_value("H1", "USD Total")

update_sheet_header()


# =========================
# TOKENS (MATCH ARBISCAN) + STATUS ON SHEET
# =========================
try:
    erc20_holdings = arbiscan_get_erc20_holdings(wallet_address)
    set_status(wks, "No Errors")
except Exception as e:
    err_msg = f"{type(e).__name__}: {e}"
    print("Token scrape failed:", err_msg)
    set_status(wks, err_msg)
    raise  # keep console traceback too


# =========================
# FILL TOKEN TABLE (Arbiscan-matched)
# RULE: If USD total is $0.00, do NOT show that token at all.
# =========================
row = 2
for t in erc20_holdings:
    if money_2dp(t["usd_total"]) == Decimal("0.00"):
        continue

    wks.update_value(f"C{row}", t["name"])
    wks.update_value(f"D{row}", t["symbol"])
    wks.update_value(f"E{row}", t["qty_str"])
    wks.update_value(f"F{row}", t["token_address"])

    if t["usd_price"] is not None:
        wks.update_value(f"G{row}", str(t["usd_price"]))
    else:
        wks.update_value(f"G{row}", "N/A")

    wks.update_value(f"H{row}", str(money_2dp(t["usd_total"])))
    row += 1

print("Google sheet successfully updated.")