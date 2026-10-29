# Solana Meme Paper Bot (iPhone-friendly dashboard)

This starter project is PAPER TRADING ONLY. It has no wallet integration, no private-key handling, and cannot submit blockchain transactions.

## What it does
- Reads the latest token profiles from DexScreener.
- Fetches Solana token pairs in small batches.
- Filters by pool age, liquidity, 5-minute volume, recent buys/sells, and recent price change.
- Lets you manually record simulated buys and sells.
- Displays a basic simulated portfolio.

## Important limitations
- Market-data filters are not a contract audit and do not guarantee a token is safe.
- Mint/freeze authority, holder concentration, locked liquidity, honeypot behavior, and sellability are NOT verified by this starter.
- Prices/volume may be stale; API calls may be rate-limited.
- The IDR/USD conversion is an illustrative fixed value (16,000) in `app.py`; change it if you want a different simulation assumption. It is not a live FX quote.
- Free app hosts may sleep and may not persist in-memory state. This app is for learning only.
- Do not add wallet keys or seed phrases to this project.

## Run locally
1. Install Python 3.10+.
2. In a terminal:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```
3. Open the local URL shown by Streamlit.

## Deploy from an iPhone using Streamlit Community Cloud
1. Create a GitHub account if needed.
2. Create a **private** repository named `solana-meme-paper-bot`.
3. Upload `app.py` and `requirements.txt` from this ZIP to that repository using GitHub's website.
4. Open https://share.streamlit.io/ and sign in with GitHub.
5. Create an app from your repository; set the main file path to `app.py`.
6. Wait for the app to build, then open the generated app URL in Safari on your iPhone.
7. Keep it in paper mode. Do not add a wallet or secret key.

Provider plans and behavior can change. A free deployment may sleep or have resource limits. Never put a wallet private key or seed phrase in the repository, even if it is private.

## Suggested test plan
- Leave the app running and record the results at least daily for 2–4 weeks.
- Track API errors, number of candidates, number passing filters, simulated P/L, and stale/missing prices.
- Do not switch to live trading based on a small number of trades.
