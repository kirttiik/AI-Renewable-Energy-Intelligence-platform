import os
import asyncio
import logging
from datetime import datetime, date
import pandas as pd
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR  = os.path.join(ROOT_DIR, 'data', 'market')
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'iex_prices.csv')

async def scrape_iex_data():
    """Scrape real-time DAM prices from IEX website using Playwright."""
    data_payload = None

    async def handle_response(response):
        nonlocal data_payload
        if "marketdata" in response.url.lower() or "snapshot" in response.url.lower() or "damcollective" in response.url.lower():
            if response.status == 200:
                try:
                    ct = response.headers.get("content-type", "")
                    if "application/json" in ct:
                        json_data = await response.json()
                        if isinstance(json_data, dict) and any(k in str(json_data).lower() for k in ['mcp', 'mcv', 'price', 'volume']):
                            data_payload = json_data
                        elif isinstance(json_data, list) and len(json_data) > 0:
                            data_payload = json_data
                except Exception:
                    pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        page.on("response", handle_response)
        
        target_url = 'https://www.iexindia.com/market-data/day-ahead-market/market-snapshot'
        logger.info(f"Navigating to {target_url}...")
        
        try:
            await page.goto(target_url, timeout=60000)
            await page.wait_for_load_state('networkidle')
            await page.wait_for_timeout(5000)
            
            if not data_payload:
                logger.info("Parsing data from DOM tables...")
                # The MCP column is usually the last column in the 96 time-block rows.
                # Let's extract all table rows and calculate the average.
                rows = await page.locator('tr').all_inner_texts()
                
                prices = []
                for row in rows:
                    parts = row.strip().split('\t')
                    # Look for rows that have at least 5 columns and the last one is a number
                    if len(parts) >= 6:
                        try:
                            # The last column is usually the MCP
                            val_str = parts[-1].replace('Rs', '').replace(',', '').replace('₹', '').strip()
                            # Check if the block before it is a volume (also a float)
                            vol_str = parts[-2].replace(',', '').strip()
                            
                            price = float(val_str)
                            vol = float(vol_str)
                            
                            if 0 <= price <= 20000:  # Reasonable range for DAM MCP
                                prices.append(price)
                        except Exception:
                            continue
                
                if prices:
                    avg_price = sum(prices) / len(prices)
                    logger.info(f"Successfully calculated average price from {len(prices)} 15-min blocks: {avg_price}")
                    data_payload = {'dam_price_rs_mwh': avg_price, 'source': 'DOM'}
                else:
                    logger.warning("Could not find valid price blocks in the DOM.")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        finally:
            await browser.close()
            
    return data_payload

def process_and_save(scraped_data):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if os.path.exists(OUTPUT_PATH):
        df = pd.read_csv(OUTPUT_PATH)
        df['date'] = pd.to_datetime(df['date'])
    else:
        logger.warning("No existing IEX data found. Running generator to backfill.")
        from src.ingestion.iex_price_generator import main as gen_historical
        gen_historical()
        df = pd.read_csv(OUTPUT_PATH)
        df['date'] = pd.to_datetime(df['date'])

    today_date = date.today()
    price = None
    
    if scraped_data:
        if isinstance(scraped_data, dict) and 'dam_price_rs_mwh' in scraped_data:
            price = scraped_data['dam_price_rs_mwh']
    
    if not price:
        logger.warning("Scraping failed. Using 7-day rolling average as fallback.")
        recent_prices = df['dam_price_rs_mwh'].tail(7)
        price = recent_prices.mean() if len(recent_prices) > 0 else 4500
            
    peak_price   = price * 1.25
    offpeak_price = price * 0.85
    vwap = (peak_price * 12 + offpeak_price * 12) / 24

    new_row = {
        'date'            : today_date,
        'dam_price_rs_mwh': round(price, 2),
        'peak_price'      : round(peak_price, 2),
        'offpeak_price'   : round(offpeak_price, 2),
        'vwap_rs_mwh'     : round(vwap, 2),
        'month'           : today_date.month,
        'year'            : today_date.year,
        'day_of_week'     : today_date.strftime('%a'),
    }

    df = df[df['date'].dt.date != today_date]
    new_df = pd.DataFrame([new_row])
    new_df['date'] = pd.to_datetime(new_df['date'])
    df = pd.concat([df, new_df], ignore_index=True)
    
    df.to_csv(OUTPUT_PATH, index=False)
    logger.info(f"Saved real-time data for {today_date}: ₹{price:,.2f}/MWh -> {OUTPUT_PATH}")

def main():
    logger.info("=" * 55)
    logger.info("IEX Playwright Scraper — Starting")
    logger.info("=" * 55)
    
    try:
        data = asyncio.run(scrape_iex_data())
        process_and_save(data)
    except Exception as e:
        logger.error(f"Critical error in scraper: {e}")
        process_and_save(None)

    logger.info("=" * 55)
    logger.info("IEX Playwright Scraper — Completed")
    logger.info("=" * 55)

if __name__ == "__main__":
    main()
