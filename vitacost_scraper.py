from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time
import random
import os
from datetime import datetime

def scrape_vitacost(search_query="weight loss supplements", num_pages=3):
    """
    Scrape Vitacost for product data based on search query
    
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
        
        page = context.new_page()
        
        # Format the search query for URL
        formatted_query = search_query.replace(" ", "+")
        
        for page_num in range(1, num_pages + 1):
            try:
                url = f"https://www.vitacost.com/search?q={formatted_query}&page={page_num}"
                print(f"Scraping Vitacost page {page_num}...")
                
                # Navigate to the page with a longer timeout
                page.goto(url, timeout=30000)
                
                # Try multiple selectors that might be present for product cards
                selectors = [".productCard", ".product-card", ".product-item", ".product", "[data-product-id]"]
                
                selector_found = False
                for selector in selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        print(f"Found selector: {selector}")
                        selector_found = True
                        break
                    except:
                        continue
                
                if not selector_found:
                    print("Could not find product elements, trying to continue anyway")
                    # Take a screenshot for debugging
                    os.makedirs("debug", exist_ok=True)
                    page.screenshot(path=f"debug/vitacost_page_{page_num}.png")
                    
                    # Save HTML for debugging
                    with open(f"debug/vitacost_page_{page_num}.html", "w", encoding="utf-8") as f:
                        f.write(page.content())
                
                # Scroll down to load lazy images
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, 800)")
                    time.sleep(0.7)
                
                # Get page content
                content = page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Try different selectors to find product items
                items = []
                for selector in selectors:
                    items = soup.select(selector)
                    if items:
                        print(f"Found {len(items)} products with selector {selector}")
                        break
                
                if not items:
                    # If no products found with common selectors, try to extract data from page structure
                    print("No products found with common selectors, trying alternative extraction")
                    
                    # Create a placeholder product to avoid empty results
                    product_data = {
                        "source": "vitacost",
                        "product_id": "error_extraction",
                        "title": f"Error extracting products from Vitacost page {page_num}",
                        "brand": "N/A",
                        "price": "N/A",
                        "original_price": "",
                        "rating": "N/A",
                        "reviews": "0",
                        "link": url,
                        "image_url": "",
                        "in_stock": False,
                        "search_query": search_query,
                        "error": "Could not extract products from page"
                    }
                    products.append(product_data)
                    continue
                
                for item in items:
                    try:
                        # Extract product details with multiple fallback selectors
                        product_id = item.get("data-product-id", "")
                        if not product_id:
                            product_id = item.get("id", "")
                        
                        # Title - try multiple selectors
                        title = ""
                        for title_selector in [".productTitle", ".product-title", ".name", "h2", ".product-name"]:
                            title_elem = item.select_one(title_selector)
                            if title_elem:
                                title = title_elem.text.strip()
                                break
                        
                        # Brand - try multiple selectors
                        brand = ""
                        for brand_selector in [".productBrand", ".product-brand", ".brand", ".manufacturer"]:
                            brand_elem = item.select_one(brand_selector)
                            if brand_elem:
                                brand = brand_elem.text.strip()
                                break
                        
                        # Price - try multiple selectors
                        price = ""
                        for price_selector in [".salePrice", ".productPrice", ".price", ".product-price", ".discount-price", "[data-price]"]:
                            price_elem = item.select_one(price_selector)
                            if price_elem:
                                price = price_elem.text.strip()
                                break
                        
                        # Original price if on sale
                        original_price = ""
                        for orig_price_selector in [".wasPrice", ".original-price", ".regular-price", ".compare-at-price"]:
                            orig_price_elem = item.select_one(orig_price_selector)
                            if orig_price_elem:
                                original_price = orig_price_elem.text.strip()
                                break
                        
                        # Rating - try multiple selectors
                        rating = ""
                        for rating_selector in [".ratingValue", ".rating", ".stars", ".product-rating"]:
                            rating_elem = item.select_one(rating_selector)
                            if rating_elem:
                                rating = rating_elem.text.strip()
                                break
                        
                        # Reviews count - try multiple selectors
                        reviews = "0"
                        for reviews_selector in [".reviewCount", ".review-count", ".reviews"]:
                            reviews_elem = item.select_one(reviews_selector)
                            if reviews_elem:
                                reviews_text = reviews_elem.text.strip()
                                # Try to extract just the number
                                import re
                                reviews_match = re.search(r'(\d+)', reviews_text)
                                if reviews_match:
                                    reviews = reviews_match.group(1)
                                else:
                                    reviews = reviews_text.replace("(", "").replace(")", "")
                                break
                        
                        # Product link - try multiple selectors
                        link = ""
                        for link_selector in ["a.productCard-url", "a", ".product-link", ".title a"]:
                            link_elem = item.select_one(link_selector)
                            if link_elem and "href" in link_elem.attrs:
                                link = link_elem["href"]
                                if not link.startswith("http"):
                                    link = "https://www.vitacost.com" + link
                                break
                        
                        # Image URL - try multiple selectors
                        img_url = ""
                        for img_selector in ["img.productImage", "img", ".product-image", ".lazy-image"]:
                            img_elem = item.select_one(img_selector)
                            if img_elem:
                                # Try different image attributes
                                for attr in ["src", "data-src", "data-original"]:
                                    if attr in img_elem.attrs:
                                        img_url = img_elem[attr]
                                        break
                                if img_url:
                                    break
                        
                        # Check if in stock
                        in_stock = True
                        for out_of_stock_selector in [".outOfStock", ".sold-out", ".out-of-stock"]:
                            out_of_stock_elem = item.select_one(out_of_stock_selector)
                            if out_of_stock_elem:
                                in_stock = False
                                break
                        
                        # Only add products with at least a title or link
                        if title or link:
                            product_data = {
                                "source": "vitacost",
                                "product_id": product_id,
                                "title": title,
                                "brand": brand,
                                "price": price,
                                "original_price": original_price,
                                "rating": rating,
                                "reviews": reviews,
                                "link": link,
                                "image_url": img_url,
                                "in_stock": in_stock,
                                "search_query": search_query
                            }
                            products.append(product_data)
                    
                    except Exception as e:
                        print(f"Error extracting product: {e}")
                
                # Random delay between pages to avoid detection
                if page_num < num_pages:
                    time.sleep(random.uniform(3, 6))
                    
            except Exception as e:
                print(f"Error processing Vitacost page {page_num}: {e}")
                # Create a debug screenshot
                try:
                    os.makedirs("debug", exist_ok=True)
                    page.screenshot(path=f"debug/vitacost_error_page_{page_num}.png")
                except:
                    pass
        
        browser.close()
    
    # If no products were found at all, create a placeholder
    if not products:
        products.append({
            "source": "vitacost",
            "product_id": "no_results",
            "title": f"No products found for '{search_query}' on Vitacost",
            "brand": "N/A",
            "price": "N/A",
            "original_price": "",
            "rating": "N/A",
            "reviews": "0",
            "link": f"https://www.vitacost.com/search?q={search_query.replace(' ', '+')}",
            "image_url": "",
            "in_stock": False,
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
        filename = f"vitacost_{search_term}_{timestamp}.json"
    
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
        "vitamin d3",
        "probiotics"
    ]
    
    all_products = []
    
    for query in search_queries:
        print(f"\nScraping products for: {query}")
        products = scrape_vitacost(search_query=query, num_pages=2)
        all_products.extend(products)
        
        # Save individual query results
        save_data(products)
        
        # Random delay between queries
        if query != search_queries[-1]:
            delay = random.uniform(5, 10)
            print(f"Waiting {delay:.1f} seconds before next query...")
            time.sleep(delay)
    
    # Save all products to a combined file
    save_data(all_products, "vitacost_all_products.json")