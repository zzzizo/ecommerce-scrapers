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
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        # Add cookie consent to avoid popup
        context.add_cookies([{
            "name": "i18n-prefs",
            "value": "USD",
            "domain": ".amazon.com",
            "path": "/"
        }])
        
        page = context.new_page()
        
        # Format the search query for URL
        formatted_query = search_query.replace(" ", "+")
        
        for page_num in range(1, num_pages + 1):
            try:
                url = f"https://www.amazon.com/s?k={formatted_query}&page={page_num}"
                print(f"Scraping Amazon page {page_num}...")
                
                # Navigate to the page with a longer timeout
                page.goto(url, timeout=30000)
                
                # Wait for product grid to load
                page.wait_for_selector("div.s-result-list", timeout=10000)
                
                # Scroll down to load lazy images and content
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, 800)")
                    time.sleep(0.7)
                
                # Get page content
                content = page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Find all product items
                items = soup.select("div.s-result-item[data-asin]:not([data-asin=''])") 
                
                if not items:
                    print("No products found on this page, trying alternative selectors")
                    items = soup.select("[data-asin]:not([data-asin=''])")
                
                if not items:
                    print(f"No products found on Amazon page {page_num}")
                    # Take a screenshot for debugging
                    os.makedirs("debug", exist_ok=True)
                    page.screenshot(path=f"debug/amazon_page_{page_num}.png")
                    
                    # Save HTML for debugging
                    with open(f"debug/amazon_page_{page_num}.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    continue
                
                print(f"Found {len(items)} products on page {page_num}")
                
                for item in items:
                    try:
                        # Get ASIN (Amazon Standard Identification Number)
                        asin = item.get("data-asin", "")
                        if not asin:
                            continue
                        
                        # Get product title
                        title_elem = item.select_one("h2 a span") or item.select_one(".a-text-normal")
                        title = title_elem.text.strip() if title_elem else ""
                        
                        # Get product link
                        link_elem = item.select_one("h2 a") or item.select_one("a.a-link-normal.s-no-outline")
                        link = "https://www.amazon.com" + link_elem["href"] if link_elem and "href" in link_elem.attrs else ""
                        
                        # Get product image
                        img_elem = item.select_one("img.s-image")
                        img_url = img_elem["src"] if img_elem and "src" in img_elem.attrs else ""
                        
                        # Get product price - try multiple selectors
                        price = ""
                        price_selectors = [
                            ".a-price .a-offscreen", 
                            ".a-price-whole", 
                            ".a-price", 
                            ".a-color-price"
                        ]
                        
                        for selector in price_selectors:
                            price_elem = item.select_one(selector)
                            if price_elem:
                                price = price_elem.text.strip()
                                break
                        
                        # Get product rating - try multiple approaches
                        rating = ""
                        rating_elem = item.select_one("i.a-icon-star-small") or item.select_one("i.a-icon-star")
                        if rating_elem:
                            rating_text = rating_elem.text.strip()
                            if rating_text:
                                # Extract just the number
                                import re
                                rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                                if rating_match:
                                    rating = rating_match.group(1)
                        
                        # If still no rating, try to get it from aria-label
                        if not rating:
                            rating_elem = item.select_one("[aria-label*='out of 5 stars']")
                            if rating_elem:
                                import re
                                rating_match = re.search(r'(\d+(\.\d+)?)', rating_elem.get("aria-label", ""))
                                if rating_match:
                                    rating = rating_match.group(1)
                        
                        # Get number of reviews
                        reviews = "0"
                        reviews_elem = item.select_one("span.a-size-base.s-underline-text") or item.select_one("span.a-size-base")
                        if reviews_elem:
                            reviews_text = reviews_elem.text.strip()
                            # Check if this is likely a review count (contains digits)
                            if any(c.isdigit() for c in reviews_text):
                                # Extract just the number
                                import re
                                reviews_match = re.search(r'(\d+[,\d]*)', reviews_text)
                                if reviews_match:
                                    reviews = reviews_match.group(1).replace(",", "")
                        
                        # Check if Prime eligible
                        prime_elem = item.select_one("i.a-icon-prime") or item.select_one("[aria-label='Amazon Prime']")
                        prime_eligible = bool(prime_elem)
                        
                        # Only add products with at least an ASIN and title
                        if asin and title:
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
                    time.sleep(random.uniform(3, 6))
                    
            except Exception as e:
                print(f"Error processing Amazon page {page_num}: {e}")
                # Create a debug screenshot
                try:
                    os.makedirs("debug", exist_ok=True)
                    page.screenshot(path=f"debug/amazon_error_page_{page_num}.png")
                except:
                    pass
        
        browser.close()
    
    # If no products were found at all, create a placeholder
    if not products:
        products.append({
            "source": "amazon",
            "asin": "no_results",
            "title": f"No products found for '{search_query}' on Amazon",
            "price": "",
            "rating": "",
            "reviews": "0",
            "link": f"https://www.amazon.com/s?k={search_query.replace(' ', '+')}",
            "image_url": "",
            "prime_eligible": False,
            "search_query": search_query,
            "error": "No products found"
        })
    
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
        "protein powder",
        "vitamin d3",
        "probiotics"
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