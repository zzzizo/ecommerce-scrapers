from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time
import random
import os
from datetime import datetime

def scrape_amazon(search_query="weight loss supplements", num_pages=3):
    """
    Scrape Amazon for product data based on search query
    
    Args:
        search_query: The search term to look for
        num_pages: Number of pages to scrape
    
    Returns:
        List of product dictionaries with details
    """
    products = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Format the search query for URL
        formatted_query = search_query.replace(" ", "+")
        
        for page_num in range(1, num_pages + 1):
            url = f"https://www.amazon.com/s?k={formatted_query}&page={page_num}"
            print(f"Scraping Amazon page {page_num}...")
            
            page.goto(url)
            # Wait for product grid to load
            page.wait_for_selector(".s-result-item", timeout=10000)
            
            # Scroll down to load lazy images
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 800)")
                time.sleep(0.5)
            
            soup = BeautifulSoup(page.content(), "html.parser")
            
            # Find all product items
            items = soup.select(".s-result-item[data-asin]:not([data-asin=''])") 
            
            for item in items:
                try:
                    # Extract product details
                    asin = item.get("data-asin", "")
                    title_elem = item.select_one("h2 a span")
                    title = title_elem.text.strip() if title_elem else ""
                    
                    # Price - handle different price formats
                    price = ""
                    price_whole = item.select_one(".a-price-whole")
                    price_fraction = item.select_one(".a-price-fraction")
                    
                    if price_whole and price_fraction:
                        price = f"{price_whole.text}{price_fraction.text}"
                    
                    # Handle sponsored price
                    if not price:
                        price_elem = item.select_one(".a-offscreen")
                        if price_elem:
                            price = price_elem.text.strip()
                    
                    # Rating and reviews
                    rating_elem = item.select_one(".a-icon-star-small")
                    rating = ""
                    if rating_elem:
                        rating_text = rating_elem.get_text().strip()
                        rating = rating_text.split(" ")[0] if rating_text else ""
                    
                    reviews_elem = item.select_one("span.a-size-base.s-underline-text")
                    reviews = reviews_elem.text.strip() if reviews_elem else "0"
                    
                    # Product link
                    link_elem = item.select_one("h2 a")
                    link = "https://www.amazon.com" + link_elem["href"] if link_elem and "href" in link_elem.attrs else ""
                    
                    # Image URL
                    img_elem = item.select_one("img.s-image")
                    img_url = img_elem["src"] if img_elem and "src" in img_elem.attrs else ""
                    
                    # Check if prime eligible
                    prime_elem = item.select_one(".a-icon-prime")
                    prime_eligible = True if prime_elem else False
                    
                    # Only add products with title and some pricing info
                    if title and (price or asin):
                        product_data = {
                            "source": "amazon",
                            "asin": asin,
                            "title": title,
                            "price": price,
                            "rating": rating,
                            "reviews": reviews,
                            "link": link,
                            "image_url": img_url,
                            "prime_eligible": prime_eligible,
                            "search_query": search_query
                        }
                        products.append(product_data)
                
                except Exception as e:
                    print(f"Error extracting product: {e}")
            
            # Random delay between pages to avoid detection
            if page_num < num_pages:
                time.sleep(random.uniform(2, 5))
        
        browser.close()
    
    return products

def save_data(data, filename=None):
    """Save scraped data to JSON file"""
    if not filename:
        # Create filename with timestamp and search query
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_term = data[0]["search_query"].replace(" ", "_") if data else "products"
        filename = f"amazon_{search_term}_{timestamp}.json"
    
    # Ensure directory exists
    os.makedirs("data", exist_ok=True)
    filepath = os.path.join("data", filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"Saved {len(data)} products to {filepath}")
    return filepath

if __name__ == "__main__":
    # Example search queries
    search_queries = [
        "weight loss supplements",
        "collagen powder",
        "vitamin d3 supplements",
        "retinol cream"
    ]
    
    all_products = []
    
    for query in search_queries:
        print(f"\nScraping products for: {query}")
        products = scrape_amazon(search_query=query, num_pages=2)
        all_products.extend(products)
        
        # Save individual query results
        save_data(products)
        
        # Random delay between queries
        if query != search_queries[-1]:
            delay = random.uniform(5, 10)
            print(f"Waiting {delay:.1f} seconds before next query...")
            time.sleep(delay)
    
    # Save all products to a combined file
    save_data(all_products, "amazon_all_products.json")