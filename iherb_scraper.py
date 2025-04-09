from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time
import random
import os
from datetime import datetime

def scrape_iherb(search_query="weight loss supplements", num_pages=3):
    """
    Scrape iHerb for product data based on search query
    
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
            "name": "ih-preference",
            "value": "store=0&country=US&language=en-US&currency=USD",
            "domain": ".iherb.com",
            "path": "/"
        }])
        
        page = context.new_page()
        
        # Format the search query for URL
        formatted_query = search_query.replace(" ", "+")
        
        for page_num in range(1, num_pages + 1):
            try:
                url = f"https://www.iherb.com/search?kw={formatted_query}&p={page_num}"
                print(f"Scraping iHerb page {page_num}...")
                
                # Navigate to the page with a longer timeout
                page.goto(url, timeout=30000)
                
                # Wait for any selector that indicates products have loaded
                # Try multiple selectors that might be present
                selectors = [".product-cell", ".product-inner", ".product-item", ".product"]
                
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
                
                # Scroll down to load lazy images
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, 800)")
                    time.sleep(0.7)
                
                # Get page content
                content = page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # Try different selectors to find product items
                items = []
                for selector in [".product-cell", ".product-inner", ".product-item", ".product"]:
                    items = soup.select(selector)
                    if items:
                        print(f"Found {len(items)} products with selector {selector}")
                        break
                
                if not items:
                    # If no products found with common selectors, try to extract data from page structure
                    print("No products found with common selectors, trying alternative extraction")
                    
                    # Take a screenshot for debugging
                    os.makedirs("debug", exist_ok=True)
                    page.screenshot(path=f"debug/iherb_page_{page_num}.png")
                    
                    # Save HTML for debugging
                    with open(f"debug/iherb_page_{page_num}.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    # Create a placeholder product to avoid empty results
                    product_data = {
                        "source": "iherb",
                        "product_id": "error_extraction",
                        "title": f"Error extracting products from iHerb page {page_num}",
                        "brand": "N/A",
                        "price": "N/A",
                        "rating": "N/A",
                        "reviews": "0",
                        "link": url,
                        "image_url": "",
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
                        for title_selector in [".product-title", ".name", "h2", ".product-name"]:
                            title_elem = item.select_one(title_selector)
                            if title_elem:
                                title = title_elem.text.strip()
                                break
                        
                        # Brand - try multiple selectors
                        brand = ""
                        for brand_selector in [".product-brand", ".brand", ".manufacturer"]:
                            brand_elem = item.select_one(brand_selector)
                            if brand_elem:
                                brand = brand_elem.text.strip()
                                break
                        
                        # Price - try multiple selectors
                        price = ""
                        for price_selector in [".price", ".product-price", ".discount-price", "[data-price]"]:
                            price_elem = item.select_one(price_selector)
                            if price_elem:
                                price = price_elem.text.strip()
                                break
                        
                        # If still no price, try to get it from data attribute
                        if not price and item.get("data-price"):
                            price = item.get("data-price")
                        
                        # Rating - try multiple selectors
                        rating = ""
                        for rating_selector in [".rating", ".stars", ".product-rating"]:
                            rating_elem = item.select_one(rating_selector)
                            if rating_elem:
                                rating_text = rating_elem.get("title", "") or rating_elem.text.strip()
                                # Try to extract just the number
                                import re
                                rating_match = re.search(r'(\d+(\.\d+)?)', rating_text)
                                if rating_match:
                                    rating = rating_match.group(1)
                                else:
                                    rating = rating_text
                                break
                        
                        # Reviews count - try multiple selectors
                        reviews = "0"
                        for reviews_selector in [".rating-count", ".review-count", ".reviews"]:
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
                        for link_selector in ["a", ".product-link", ".title a"]:
                            link_elem = item.select_one(link_selector)
                            if link_elem and "href" in link_elem.attrs:
                                link = link_elem["href"]
                                if not link.startswith("http"):
                                    link = "https://www.iherb.com" + link
                                break
                        
                        # Image URL - try multiple selectors
                        img_url = ""
                        for img_selector in ["img", ".product-image", ".lazy-image"]:
                            img_elem = item.select_one(img_selector)
                            if img_elem:
                                # Try different image attributes
                                for attr in ["src", "data-src", "data-original"]:
                                    if attr in img_elem.attrs:
                                        img_url = img_elem[attr]
                                        break
                                if img_url:
                                    break
                        
                        # Only add products with at least a title or link
                        if title or link:
                            product_data = {
                                "source": "iherb",
                                "product_id": product_id,
                                "title": title,
                                "brand": brand,
                                "price": price,
                                "rating": rating,
                                "reviews": reviews,
                                "link": link,
                                "image_url": img_url,
                                "search_query": search_query
                            }
                            products.append(product_data)
                    
                    except Exception as e:
                        print(f"Error extracting product: {e}")
                
                # Random delay between pages to avoid detection
                if page_num < num_pages:
                    time.sleep(random.uniform(3, 6))
                    
            except Exception as e:
                print(f"Error processing iHerb page {page_num}: {e}")
                # Create a debug screenshot
                try:
                    os.makedirs("debug", exist_ok=True)
                    page.screenshot(path=f"debug/iherb_error_page_{page_num}.png")
                except:
                    pass
        
        browser.close()
    
    # If no products were found at all, create a placeholder
    if not products:
        products.append({
            "source": "iherb",
            "product_id": "no_results",
            "title": f"No products found for '{search_query}' on iHerb",
            "brand": "N/A",
            "price": "N/A",
            "rating": "N/A",
            "reviews": "0",
            "link": f"https://www.iherb.com/search?kw={search_query.replace(' ', '+')}",
            "image_url": "",
            "search_query": search_query,
            "error": "No products found"
        })
    
    # Post-process products to validate and clean data
    for product in products:
        # Ensure rating is within 0-5 range
        try:
            if product["rating"]:
                rating_float = float(product["rating"])
                if rating_float > 5:
                    # This is likely a review count, not a rating
                    if product["reviews"] == "0":
                        product["reviews"] = product["rating"]
                    product["rating"] = ""
        except (ValueError, TypeError):
            product["rating"] = ""
        
        # Ensure reviews is a number
        try:
            if product["reviews"]:
                int(product["reviews"].replace(",", ""))
        except (ValueError, TypeError):
            product["reviews"] = "0"
    
    return products

def save_data(data, filename=None):
    """Save scraped data to JSON file"""
    if not filename:
        # Create filename with timestamp and search query
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        search_term = data[0]["search_query"].replace(" ", "_") if data else "products"
        filename = f"iherb_{search_term}_{timestamp}.json"
    
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
        products = scrape_iherb(search_query=query, num_pages=2)
        all_products.extend(products)
        
        # Save individual query results
        save_data(products)
        
        # Random delay between queries
        if query != search_queries[-1]:
            delay = random.uniform(5, 10)
            print(f"Waiting {delay:.1f} seconds before next query...")
            time.sleep(delay)
    
    # Save all products to a combined file
    save_data(all_products, "iherb_all_products.json")