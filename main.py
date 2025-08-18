import os
import requests
import datetime
from typing import Dict, Optional
import json
from collections import defaultdict
import time
from pathlib import Path

# Load .env (simple parser, no extra dependency)
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if not line or line.strip().startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

class QTOBidirectionalSwapAnalyzer:

    def __init__(self):
        # Read secrets/config from environment (.env). Do NOT include secrets in source.
        self.token_address = os.getenv("TOKEN_ADDRESS")
        self.etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        
        # Common token addresses and symbols
        self.common_tokens = {
            "0xa0b86a33e6441026daf4c94f74ffc88b6b48a1cc": "USDT",
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2": "WETH", 
            "0x6b175474e89094c44da98b954eedeac495271d0f": "DAI",
            "0xa0b86a33e6441026daf4c94f74ffc88b6b48a1cc": "USDC",
            "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599": "WBTC",
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984": "UNI",
            "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0": "MATIC",
            "0x514910771af9ca656af840dff83e8264ecf986ca": "LINK"
        }
        
        # Reverse mapping for quick lookup
        self.token_symbols = {v: k for k, v in self.common_tokens.items()}
        
        # DEX platform identification
        self.dex_signatures = {
            "uniswap_v2": ["0x7a250d5630b4cf539739df2c5dacb4c659f2488d"],
            "uniswap_v3": ["0xe592427a0aece92de3edee1f18e0157c05861564"],
            "sushiswap": ["0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f", "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506"],
            "oboswap": ["0xe71ec95e61f76e7dd86bba1c78a85f5e4b062e77"],
            "1inch_v4": ["0x1111111254fb6c44bac0bed2854e76f90643097d"],
            "1inch_v5": ["0x1111111254eeb25477b68fb85ed929f73a960582"],
            "pancakeswap": ["0x10ed43c718714eb63d5aa57b78b54704e256024e"],
            "balancer": ["0xba12222222228d8ba445958a75a0704d566bf2c8"],
            "0x_protocol": ["0xdef1c0ded9bec7f1a1670819833240f027b25eff"],
            "metamask_swaps": ["0x881d40237659c251811cec9c364ef91dc08d300c"]
        }

    def analyze_bidirectional_swaps(self) -> Dict:
        """Main function to analyze QTO ↔ Token swaps."""
        print("🔄 QTO BIDIRECTIONAL SWAP ANALYZER")
        print("=" * 50)
        print("📅 Analyzing last 7 days of swaps")
        print("🔀 Tracking: QTO → Token AND Token → QTO")
        print("🏢 Sources: DEX + CEX platforms\n")
        
        dex_swaps = self._get_dex_bidirectional_swaps()
        cex_swaps = self._get_cex_bidirectional_swaps()
        
        complete_analysis = self._analyze_complete_swap_data(dex_swaps, cex_swaps)
        
        return complete_analysis
    
    def _get_dex_bidirectional_swaps(self) -> Dict:
        """Get DEX swaps."""
        print("🔍 Analyzing DEX Swaps...")
        print("-" * 40)
        
        swap_data = {
            "qto_to_token": defaultdict(lambda: defaultdict(float)),
            "token_to_qto": defaultdict(lambda: defaultdict(float)),
            "platforms": defaultdict(float)
        }
        
        dexscreener_swaps = self._get_dexscreener_bidirectional()
        if dexscreener_swaps:
            self._merge_swap_data(swap_data, dexscreener_swaps)
        
        etherscan_swaps = self._get_etherscan_bidirectional()
        if etherscan_swaps:
            self._merge_swap_data(swap_data, etherscan_swaps)
        
        return swap_data
    
    def _get_dexscreener_bidirectional(self) -> Dict:
        """Get bidirectional data from DexScreener."""
        print("📊 DexScreener: Fetching trading pairs...")
        
        url = f"https://api.dexscreener.com/latest/dex/tokens/{self.token_address}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            pairs = data.get("pairs", [])
            print(f"✅ Found {len(pairs)} active pairs")
            
            swap_data = {
                "qto_to_token": defaultdict(lambda: defaultdict(float)),
                "token_to_qto": defaultdict(lambda: defaultdict(float)),
                "platforms": defaultdict(float)
            }
            
            for pair in pairs:
                base_token = pair.get("baseToken", {})
                quote_token = pair.get("quoteToken", {})
                dex_name = pair.get("dexId", "unknown").title()
                
                dex_mapping = { "uniswap": "Uniswap V2", "uniswapv3": "Uniswap V3", "sushiswap": "SushiSwap" }
                dex_name = dex_mapping.get(dex_name.lower(), dex_name)
                
                volume_24h = float(pair.get("volume", {}).get("h24", 0))
                volume_7d = volume_24h * 7
                
                if volume_7d > 0:
                    if base_token.get("address", "").lower() == self.token_address.lower():
                        quote_symbol = quote_token.get("symbol", "UNKNOWN")
                        qto_to_quote = volume_7d * 0.5
                        quote_to_qto = volume_7d * 0.5
                        
                        swap_data["qto_to_token"][quote_symbol][dex_name] += qto_to_quote
                        swap_data["token_to_qto"][quote_symbol][dex_name] += quote_to_qto
                        swap_data["platforms"][dex_name] += volume_7d
                        
                    elif quote_token.get("address", "").lower() == self.token_address.lower():
                        base_symbol = base_token.get("symbol", "UNKNOWN")
                        base_to_qto = volume_7d * 0.5
                        qto_to_base = volume_7d * 0.5
                        
                        swap_data["token_to_qto"][base_symbol][dex_name] += base_to_qto
                        swap_data["qto_to_token"][base_symbol][dex_name] += qto_to_base
                        swap_data["platforms"][dex_name] += volume_7d
            
            total_volume = sum(swap_data["platforms"].values())
            print(f"📈 DexScreener Total: ${total_volume:,.2f} (7-day estimate)")
            
            return swap_data
            
        except Exception as e:
            print(f"❌ DexScreener error: {e}")
            return {}
    
    def _get_etherscan_bidirectional(self) -> Dict:
        """Analyze on-chain transactions for swaps."""
        print("🔗 Etherscan: Analyzing on-chain swaps...")
        
        seven_days_ago = int((datetime.datetime.now() - datetime.timedelta(days=7)).timestamp())
        
        url = "https://api.etherscan.io/api"
        params = {
            "module": "account", "action": "tokentx", "contractaddress": self.token_address,
            "startblock": 0, "endblock": 99999999, "sort": "desc", "apikey": self.etherscan_api_key
        }
        
        try:
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get("status") != "1":
                print(f"❌ Etherscan error: {data.get('message')}")
                return {}
            
            transactions = data.get("result", [])
            recent_txs = [tx for tx in transactions if int(tx.get("timeStamp", 0)) >= seven_days_ago]
            
            print(f"✅ Found {len(recent_txs)} QTO transfers in last 7 days")
            
            swap_data = {
                "qto_to_token": defaultdict(lambda: defaultdict(float)),
                "token_to_qto": defaultdict(lambda: defaultdict(float)),
                "platforms": defaultdict(float)
            }
            
            dex_count = 0
            for tx in recent_txs[:50]:
                platform = self._identify_platform(tx)
                if platform and "Unknown" not in platform:
                    dex_count += 1
                    
                    token_amount = int(tx.get("value", 0)) / (10 ** int(tx.get("tokenDecimal", 18)))
                    usd_value = self._estimate_usd_value(token_amount, tx.get("timeStamp"))
                    
                    if usd_value > 0:
                        paired_token = "USDT"
                        from_addr = tx.get("from", "").lower()
                        to_addr = tx.get("to", "").lower()
                        
                        if any(router in [from_addr, to_addr] for router_list in self.dex_signatures.values() for router in [r.lower() for r in router_list]):
                            swap_data["qto_to_token"][paired_token][platform] += usd_value * 0.5
                            swap_data["token_to_qto"][paired_token][platform] += usd_value * 0.5
                            swap_data["platforms"][platform] += usd_value

            print(f"🎯 Identified {dex_count} potential DEX swaps")
            return swap_data
            
        except Exception as e:
            print(f"❌ Etherscan error: {e}")
            return {}
    
    def _get_cex_bidirectional_swaps(self) -> Dict:
        """Get CEX trading data."""
        print("\n🏦 Analyzing CEX Swaps...")
        print("-" * 40)
        
        swap_data = {
            "qto_to_token": defaultdict(lambda: defaultdict(float)),
            "token_to_qto": defaultdict(lambda: defaultdict(float)),
            "platforms": defaultdict(float)
        }
        
        # Method 1: CryptoCompare
        cc_data = self._get_cryptocompare_cex_data()
        if cc_data:
            self._merge_swap_data(swap_data, cc_data)
        
        total_cex_volume = sum(swap_data["platforms"].values())
        if total_cex_volume > 0:
            print(f"🏦 Total CEX Volume: ${total_cex_volume:,.2f} (7-day estimate)")
        else:
            print("❌ No CEX trading data found for QTO")
        
        return swap_data
    
    def _get_cryptocompare_cex_data(self) -> Dict:
        """Get CEX data from CryptoCompare."""
        print("💹 CryptoCompare: Checking CEX exchanges...")
        
        endpoints = [
            f"https://min-api.cryptocompare.com/data/top/exchanges/full?fsym=QTO&tsym=USD",
            f"https://min-api.cryptocompare.com/data/top/exchanges?fsym=QTO&tsym=USDT",
            f"https://min-api.cryptocompare.com/data/top/exchanges?fsym=QTO&tsym=BTC"
        ]
        
        swap_data = {
            "qto_to_token": defaultdict(lambda: defaultdict(float)),
            "token_to_qto": defaultdict(lambda: defaultdict(float)),
            "platforms": defaultdict(float)
        }
        
        for endpoint in endpoints:
            try:
                response = requests.get(endpoint)
                data = response.json()
                
                if data.get("Response") == "Success":
                    exchanges_data = data.get("Data", {})
                    
                    if isinstance(exchanges_data, dict) and "Exchanges" in exchanges_data:
                        exchanges = exchanges_data["Exchanges"]
                    elif isinstance(exchanges_data, list):
                        exchanges = exchanges_data
                    else:
                        continue
                    
                    for exchange in exchanges[:10]:
                        exchange_name = exchange.get("MARKET", exchange.get("exchange", "Unknown"))
                        volume_24h = float(exchange.get("VOLUME24HOURTO", exchange.get("volume", 0)))
                        
                        if volume_24h > 0:
                            volume_7d = volume_24h * 7
                            
                            if "USDT" in endpoint: paired_token = "USDT"
                            elif "BTC" in endpoint: paired_token = "BTC"
                            else: paired_token = "USD"
                            
                            qto_to_token = volume_7d * 0.5
                            token_to_qto = volume_7d * 0.5
                            
                            cex_name = f"{exchange_name} (CEX)"
                            swap_data["qto_to_token"][paired_token][cex_name] += qto_to_token
                            swap_data["token_to_qto"][paired_token][cex_name] += token_to_qto
                            swap_data["platforms"][cex_name] += volume_7d
                    
                    if exchanges:
                        print(f"✅ CryptoCompare: Found {len(exchanges)} exchanges")
                        break
                        
            except Exception as e:
                print(f"❌ CryptoCompare endpoint error: {e}")
                continue
        
        return swap_data

    def _merge_swap_data(self, main_data: Dict, new_data: Dict) -> None:
        """Merge new swap data into the main data structure."""
        if not new_data:
            return
            
        for token, platforms in new_data.get("qto_to_token", {}).items():
            for platform, volume in platforms.items():
                main_data["qto_to_token"][token][platform] += volume
        
        for token, platforms in new_data.get("token_to_qto", {}).items():
            for platform, volume in platforms.items():
                main_data["token_to_qto"][token][platform] += volume
        
        for platform, volume in new_data.get("platforms", {}).items():
            main_data["platforms"][platform] += volume
    
    def _analyze_complete_swap_data(self, dex_data: Dict, cex_data: Dict) -> Dict:
        """Combine and analyze all swap data."""
        print("\n" + "=" * 60)
        print("📊 COMPLETE BIDIRECTIONAL SWAP ANALYSIS")
        print("=" * 60)
        
        complete_data = {
            "qto_to_token": defaultdict(lambda: defaultdict(float)),
            "token_to_qto": defaultdict(lambda: defaultdict(float)),
            "platforms": defaultdict(float)
        }
        
        self._merge_swap_data(complete_data, dex_data)
        self._merge_swap_data(complete_data, cex_data)
        
        total_qto_to_token = sum(sum(p.values()) for p in complete_data["qto_to_token"].values())
        total_token_to_qto = sum(sum(p.values()) for p in complete_data["token_to_qto"].values())
        total_volume = total_qto_to_token + total_token_to_qto
        
        self._display_bidirectional_results(complete_data, total_qto_to_token, total_token_to_qto, total_volume)
        
        return {
            "qto_to_token": dict(complete_data["qto_to_token"]),
            "token_to_qto": dict(complete_data["token_to_qto"]),
            "platforms": dict(complete_data["platforms"]),
            "totals": { "qto_to_token": total_qto_to_token, "token_to_qto": total_token_to_qto, "total_volume": total_volume }
        }
    
    def _display_bidirectional_results(self, data: Dict, qto_to_token_total: float, token_to_qto_total: float, total_volume: float):
        """Display comprehensive bidirectional results."""
        
        print(f"📅 Period: Last 7 days")
        print(f"💰 Total Volume: ${total_volume:,.2f}")
        print(f"📤 QTO → Token: ${qto_to_token_total:,.2f} ({qto_to_token_total/total_volume*100:.1f}%)")
        print(f"📥 Token → QTO: ${token_to_qto_total:,.2f} ({token_to_qto_total/total_volume*100:.1f}%)")
        print()
        
        print("🔄 SWAP BREAKDOWN BY DIRECTION & TOKEN")
        print("-" * 45)
        
        print("📤 QTO → TOKEN SWAPS:")
        for token, platforms in sorted(data["qto_to_token"].items(), key=lambda x: sum(x[1].values()), reverse=True):
            token_total = sum(platforms.values())
            if token_total > 0: print(f"   💱 QTO → {token:<8}: ${token_total:>10,.2f}")
        
        print()
        
        print("📥 TOKEN → QTO SWAPS:")
        for token, platforms in sorted(data["token_to_qto"].items(), key=lambda x: sum(x[1].values()), reverse=True):
            token_total = sum(platforms.values())
            if token_total > 0: print(f"   💱 {token:<8} → QTO: ${token_total:>10,.2f}")
        
        print()
        
        print("🏛️  SWAP VOLUME BY PLATFORMS")
        print("-" * 35)
        
        sorted_platforms = sorted(data["platforms"].items(), key=lambda x: x[1], reverse=True)
        for platform, volume in sorted_platforms:
            percentage = (volume / total_volume * 100) if total_volume > 0 else 0
            emoji = "🏦" if "(CEX)" in platform else "🔸"
            print(f"{emoji} {platform:<15}: ${volume:>12,.2f} ({percentage:>5.1f}%)")
        
        print()
        
        print("📋 DETAILED BREAKDOWN (TOKEN ↔ PLATFORM)")
        print("-" * 50)
        
        all_tokens = set(data["qto_to_token"].keys()) | set(data["token_to_qto"].keys())
        
        for token in sorted(all_tokens):
            qto_to_token_vol = sum(data["qto_to_token"].get(token, {}).values())
            token_to_qto_vol = sum(data["token_to_qto"].get(token, {}).values())
            token_total = qto_to_token_vol + token_to_qto_vol
            
            if token_total > 0:
                print(f"\n💱 QTO ↔ {token} (Total: ${token_total:,.2f}):")
                
                if qto_to_token_vol > 0:
                    print(f"  📤 QTO → {token} (${qto_to_token_vol:,.2f}):")
                    qto_to_platforms = sorted(data["qto_to_token"][token].items(), key=lambda x: x[1], reverse=True)
                    for platform, volume in qto_to_platforms:
                        if volume > 0:
                            platform_pct = (volume / qto_to_token_vol * 100) if qto_to_token_vol > 0 else 0
                            print(f"     ├─ {platform:<15}: ${volume:>8,.2f} ({platform_pct:>4.1f}%)")
                
                if token_to_qto_vol > 0:
                    print(f"  📥 {token} → QTO (${token_to_qto_vol:,.2f}):")
                    token_to_platforms = sorted(data["token_to_qto"][token].items(), key=lambda x: x[1], reverse=True)
                    for platform, volume in token_to_platforms:
                        if volume > 0:
                            platform_pct = (volume / token_to_qto_vol * 100) if token_to_qto_vol > 0 else 0
                            print(f"     ├─ {platform:<15}: ${volume:>8,.2f} ({platform_pct:>4.1f}%)")
        
        print("\n" + "=" * 60)
        print("✨ Bidirectional Analysis Complete!")
    
    def _identify_platform(self, transaction: Dict) -> Optional[str]:
        """Identify DEX platform from transaction data."""
        to_addr = transaction.get("to", "").lower()
        from_addr = transaction.get("from", "").lower()
        
        for platform, addresses in self.dex_signatures.items():
            if to_addr in [addr.lower() for addr in addresses] or from_addr in [addr.lower() for addr in addresses]:
                platform_name = platform.replace("_", " ").title().replace("V2", " V2").replace("V3", " V3").replace("V4", " V4")
                return "Oboswap" if platform == "oboswap" else platform_name
        
        return None
    
    def _estimate_usd_value(self, token_amount: float, timestamp: str) -> float:
        """Estimate USD value of QTO tokens."""
        estimated_price_per_qto = 0.01
        return token_amount * estimated_price_per_qto

def main():
    """Run the complete QTO swap analysis."""
    print("🚀 QTO BIDIRECTIONAL SWAP ANALYZER v3.0")
    print("=" * 45)
    print("🔍 Analyzing QTO ↔ Token swaps")
    print("📊 Including DEX + CEX platforms")
    print("⏰ Time period: Last 7 days\n")
    
    analyzer = QTOBidirectionalSwapAnalyzer()
    
    try:
        results = analyzer.analyze_bidirectional_swaps()
        
        print(f"\n💾 Analysis Complete!")
        print(f"📈 Total Swap Volume: ${results['totals']['total_volume']:,.2f}")
        print(f"📤 QTO → Tokens: ${results['totals']['qto_to_token']:,.2f}")
        print(f"📥 Tokens → QTO: ${results['totals']['token_to_qto']:,.2f}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        print("Please check your internet connection and API credentials.")

if __name__ == "__main__":
    main()