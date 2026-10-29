import time
from datetime import datetime, timezone
import requests
import pandas as pd
import streamlit as st

# PAPER-TRADING ONLY. No wallet, private key, or transaction execution exists here.
DEX_LATEST = "https://api.dexscreener.com/token-profiles/latest/v1"
DEX_PAIRS = "https://api.dexscreener.com/token-pairs/v1/solana/{}"

st.set_page_config(page_title="Solana Meme Paper Bot", page_icon="🧪", layout="wide")
st.title("🧪 Solana Meme Coin — Paper Trading")
st.caption("Simulation only. This app cannot connect to a wallet or submit transactions.")

with st.sidebar:
    st.header("Pengaturan simulasi")
    starting_cash = st.number_input("Modal simulasi (IDR)", min_value=50000, max_value=10000000,
                                    value=250000, step=25000)
    position_pct = st.slider("Alokasi maksimum per token (%)", 1, 20, 10)
    min_liquidity = st.number_input("Likuiditas minimum (USD)", min_value=1000, max_value=1000000,
                                    value=10000, step=1000)
    min_age_minutes = st.number_input("Umur pool minimum (menit)", min_value=1, max_value=1440,
                                      value=5, step=1)
    min_volume_5m = st.number_input("Volume 5 menit minimum (USD)", min_value=0, max_value=1000000,
                                    value=1000, step=100)
    max_price_impact_pct = st.slider("Batas perubahan harga 5m (%)", 1, 80, 25)
    poll_seconds = st.selectbox("Interval refresh", [30, 60, 120, 300], index=2)
    run_once = st.button("🔄 Perbarui data sekarang", use_container_width=True)

if "cash" not in st.session_state:
    st.session_state.cash = float(starting_cash)
    st.session_state.initial_cash = float(starting_cash)
    st.session_state.positions = {}
    st.session_state.trades = []
    st.session_state.seen = set()
    st.session_state.last_refresh = None

# If the user changes starting cash before opening any position, sync simulation.
if not st.session_state.positions and not st.session_state.trades:
    st.session_state.cash = float(starting_cash)
    st.session_state.initial_cash = float(starting_cash)

def get_json(url, timeout=12):
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "SolanaMemePaperBot/0.1"})
        if r.status_code == 429:
            st.warning("API membatasi permintaan (HTTP 429). Tunggu sebelum refresh lagi.")
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Gagal mengambil data dari sumber publik: {e}")
        return None

def num(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default

def get_metrics(pair):
    liq = num((pair.get("liquidity") or {}).get("usd"))
    vol5 = num((pair.get("volume") or {}).get("m5"))
    tx5 = (pair.get("txns") or {}).get("m5") or {}
    buys = int(num(tx5.get("buys")))
    sells = int(num(tx5.get("sells")))
    created = num(pair.get("pairCreatedAt"))
    age_min = max(0.0, (time.time() * 1000 - created) / 60000) if created else 0.0
    change5 = num((pair.get("priceChange") or {}).get("m5"))
    price = num(pair.get("priceUsd"))
    base = pair.get("baseToken") or {}
    return {
        "name": base.get("name") or "Unknown",
        "symbol": base.get("symbol") or "?",
        "address": base.get("address") or "",
        "pair": pair.get("pairAddress") or "",
        "url": pair.get("url") or "",
        "price": price,
        "liquidity_usd": liq,
        "volume_5m_usd": vol5,
        "buys_5m": buys,
        "sells_5m": sells,
        "age_min": age_min,
        "change_5m_pct": change5,
        "fdv_usd": num(pair.get("fdv")),
    }

def scan():
    profiles = get_json(DEX_LATEST)
    if not isinstance(profiles, list):
        return []
    addresses = []
    for p in profiles:
        if p.get("chainId") == "solana" and p.get("tokenAddress"):
            addresses.append(p["tokenAddress"])
    # Avoid huge bursts. DexScreener token endpoint accepts batches up to 30 addresses.
    rows, seen_addresses = [], set()
    for start in range(0, min(len(addresses), 90), 30):
        batch = addresses[start:start+30]
        if not batch:
            continue
        url = "https://api.dexscreener.com/tokens/v1/solana/" + ",".join(batch)
        data = get_json(url)
        if not isinstance(data, list):
            continue
        for pair in data:
            m = get_metrics(pair)
            if not m["address"] or m["address"] in seen_addresses:
                continue
            seen_addresses.add(m["address"])
            rows.append(m)
        time.sleep(0.25)
    rows.sort(key=lambda x: x["volume_5m_usd"], reverse=True)
    return rows

def passes(m):
    # Market-data screening only; NOT a contract audit or rug-pull guarantee.
    return (
        m["liquidity_usd"] >= float(min_liquidity)
        and m["age_min"] >= float(min_age_minutes)
        and m["volume_5m_usd"] >= float(min_volume_5m)
        and m["buys_5m"] > 0 and m["sells_5m"] > 0
        and abs(m["change_5m_pct"]) <= float(max_price_impact_pct)
        and m["price"] > 0
    )

def estimate_value(position, current_price):
    if position["entry_price"] <= 0 or current_price <= 0:
        return position["cost_idr"]
    return position["token_qty"] * current_price * position["idr_per_usd"]

refresh = run_once or st.session_state.last_refresh is None
if refresh:
    with st.spinner("Mengambil data token/pool terbaru…"):
        st.session_state.market_rows = scan()
        st.session_state.last_refresh = datetime.now(timezone.utc).isoformat()

rows = st.session_state.get("market_rows", [])
df = pd.DataFrame(rows)

st.info("Mode PAPER: tombol Beli/Jual hanya mencatat simulasi. Harga dan likuiditas dapat berubah cepat; data API bisa terlambat.")
if st.session_state.last_refresh:
    st.caption(f"Terakhir diperbarui (UTC): {st.session_state.last_refresh}")

if df.empty:
    st.warning("Belum ada data yang dapat ditampilkan. Coba Perbarui data; API publik bisa membatasi permintaan.")
else:
    df["lolos_filter"] = df.apply(lambda r: passes(r.to_dict()), axis=1)
    display_cols = ["name", "symbol", "age_min", "liquidity_usd", "volume_5m_usd",
                    "buys_5m", "sells_5m", "change_5m_pct", "price", "lolos_filter"]
    view = df[display_cols].copy()
    view.columns = ["Nama", "Simbol", "Umur pool (m)", "Likuiditas USD", "Volume 5m USD",
                    "Beli 5m", "Jual 5m", "Perubahan 5m %", "Harga USD", "Lolos filter"]
    st.subheader("Token/pool yang ditemukan")
    st.dataframe(view, use_container_width=True, hide_index=True)

    st.subheader("Simulasi beli")
    candidates = [r for r in rows if passes(r)]
    if candidates:
        labels = {f'{m["symbol"]} — {m["name"]} — {m["address"][:8]}…': m for m in candidates}
        chosen_label = st.selectbox("Pilih token yang lolos filter", list(labels.keys()))
        chosen = labels[chosen_label]
        st.write(f"Pair: {chosen['pair'] or 'tidak tersedia'}")
        if chosen["url"]:
            st.markdown(f"[Buka chart DexScreener]({chosen['url']})")
        buy_amount = st.number_input("Nilai simulasi beli (IDR)", min_value=10000,
                                     max_value=max(10000, int(st.session_state.cash)),
                                     value=min(int(st.session_state.cash), int(starting_cash * position_pct / 100)),
                                     step=5000)
        if st.button("🟢 Beli (SIMULASI)"):
            addr = chosen["address"]
            if addr in st.session_state.positions:
                st.error("Token ini sudah ada di posisi simulasi.")
            elif buy_amount > st.session_state.cash:
                st.error("Saldo simulasi tidak cukup.")
            else:
                # Price is USD; use a fixed illustrative FX rate only for paper bookkeeping.
                # User can change this in code. This does not represent a live FX quote.
                idr_per_usd = 16000.0
                token_qty = (buy_amount / idr_per_usd) / chosen["price"]
                st.session_state.positions[addr] = {
                    **chosen, "entry_price": chosen["price"], "token_qty": token_qty,
                    "cost_idr": float(buy_amount), "idr_per_usd": idr_per_usd,
                    "entry_time": datetime.now(timezone.utc).isoformat()
                }
                st.session_state.cash -= float(buy_amount)
                st.session_state.trades.append({
                    "time": datetime.now(timezone.utc).isoformat(),
                    "action": "PAPER_BUY", "symbol": chosen["symbol"],
                    "address": addr, "price_usd": chosen["price"], "amount_idr": buy_amount
                })
                st.success("Pembelian simulasi dicatat. Tidak ada transaksi blockchain yang dikirim.")
    else:
        st.write("Belum ada token yang memenuhi filter. Jangan melonggarkan filter hanya untuk memaksa entry.")

st.subheader("Posisi simulasi")
positions = st.session_state.positions
if positions:
    for addr, pos in list(positions.items()):
        current = next((m for m in rows if m["address"] == addr), None)
        current_price = current["price"] if current and current["price"] > 0 else pos["entry_price"]
        current_value = estimate_value(pos, current_price)
        pnl = current_value - pos["cost_idr"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f'{pos["symbol"]} harga masuk', f'${pos["entry_price"]:.10f}')
        c2.metric("Harga terpantau", f'${current_price:.10f}')
        c3.metric("Nilai simulasi", f'Rp{current_value:,.0f}')
        c4.metric("P/L simulasi", f'Rp{pnl:,.0f}', delta=f'{pnl:,.0f} IDR')
        if st.button(f'🔴 Jual {pos["symbol"]} (SIMULASI)', key=f"sell_{addr}"):
            st.session_state.cash += current_value
            st.session_state.trades.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "action": "PAPER_SELL", "symbol": pos["symbol"],
                "address": addr, "price_usd": current_price, "amount_idr": current_value,
                "pnl_idr": pnl
            })
            del st.session_state.positions[addr]
            st.rerun()
else:
    st.write("Belum ada posisi simulasi.")

st.subheader("Ringkasan")
total_value = st.session_state.cash
for addr, pos in positions.items():
    current = next((m for m in rows if m["address"] == addr), None)
    px = current["price"] if current and current["price"] > 0 else pos["entry_price"]
    total_value += estimate_value(pos, px)
initial = st.session_state.initial_cash
a, b, c = st.columns(3)
a.metric("Saldo simulasi", f'Rp{st.session_state.cash:,.0f}')
b.metric("Nilai total", f'Rp{total_value:,.0f}')
c.metric("P/L total", f'Rp{total_value-initial:,.0f}', delta=f'{total_value-initial:,.0f} IDR')

if st.session_state.trades:
    st.subheader("Riwayat simulasi")
    st.dataframe(pd.DataFrame(st.session_state.trades), use_container_width=True, hide_index=True)

st.warning("Batasan penting: versi ini tidak memeriksa mint/freeze authority, holder concentration, honeypot, atau likuiditas terkunci secara on-chain. Karena itu ia hanya untuk latihan paper trading, bukan untuk mengaktifkan pembelian otomatis.")
st.caption("Data API dan state simulasi bisa hilang ketika aplikasi gratis tidur/restart. Jangan gunakan angka simulasi sebagai hasil investasi nyata.")
