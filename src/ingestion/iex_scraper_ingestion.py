from playwright.sync_api import sync_playwright
import pandas as pd
import time
import os
import io

def fetch_iex_dam_data():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to IEX Market Snapshot...")
        page.goto("https://www.iexindia.com/market-data/day-ahead-market/market-snapshot")
        
        # Wait for the table to load
        page.wait_for_selector("table", timeout=30000)
        time.sleep(3)
        
        print("Selecting 'LAST 31 DAYS' Delivery Period...")
        # Target the dropdowns
        dropdowns = page.locator("div[role='combobox']")
        # The Delivery Period is usually the second one
        dropdowns.nth(1).click()
        time.sleep(1)
        
        # Click the "LAST 31 DAYS" option
        page.locator("li[role='option']", has_text="LAST 31 DAYS").click()
        time.sleep(1)
        
        # Click Update Report
        print("Clicking Update Report...")
        page.locator("button", has_text="Update Report").click()
        
        # Wait for network and table update
        time.sleep(5)
        
        print("Extracting Data Table...")
        html = page.content()
        browser.close()
        
        dfs = pd.read_html(io.StringIO(html))
        df = None
        for temp_df in dfs:
            if any("MCP" in str(col) for col in temp_df.columns):
                df = temp_df
                break
                
        if df is None:
            print("Could not find the target data table.")
            return None
            
        print(f"Extracted {len(df)} rows of data.")
        
        os.makedirs("data/raw", exist_ok=True)
        file_path = "data/raw/iex_dam_actuals.csv"
        
        if os.path.exists(file_path):
            try:
                old_df = pd.read_csv(file_path)
                # Ensure the columns match exactly or handle gracefully
                # Append and drop duplicates
                combined = pd.concat([old_df, df], ignore_index=True)
                combined.drop_duplicates(subset=["Date", "Time Block"], keep="last", inplace=True)
                # Re-sort to maintain chronological order
                combined['SortDate'] = pd.to_datetime(combined['Date'], format="%d-%m-%Y")
                combined.sort_values(by=['SortDate', 'Time Block'], inplace=True)
                combined.drop(columns=['SortDate'], inplace=True)
                df = combined
                print(f"Appended and deduplicated. Total rows: {len(df)}")
            except Exception as e:
                print(f"Error merging with existing data: {e}")
        
        df.to_csv(file_path, index=False)
        print(f"Saved to {file_path}")
        return df

if __name__ == "__main__":
    fetch_iex_dam_data()
