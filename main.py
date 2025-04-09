import os
import json
import time
import random
from datetime import datetime
from script import scrape_amazon, save_data as save_amazon_data
from iherb_scraper import scrape_iherb, save_data as save_iherb_data
from sephora_scraper import scrape_sephora, save_data as save_sephora_data
from vitacost_scraper import scrape_vitacost, save_data as save_vitacost_data

# Update the run_all_scrapers function to handle errors from individual scrapers
def run_all_scrapers(search_queries, pages_per_site=2):
    """
    Run all scrapers for the given search queries
    
    Args:
        search_queries: List of search terms to look for
        pages_per_site: Number of pages to scrape per site
    
    Returns:
        Dictionary with all scraped data by source
    """
    all_data = {
        "amazon": [],
        "iherb": [],
        "sephora": [],
        "vitacost": [],
        "combined": []
    }
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    for query in search_queries:
        print(f"\n{'='*50}")
        print(f"Scraping products for: {query}")
        print(f"{'='*50}")
        
        # Amazon
        print("\nScraping Amazon...")
        try:
            amazon_products = scrape_amazon(search_query=query, num_pages=pages_per_site)
            all_data["amazon"].extend(amazon_products)
            all_data["combined"].extend(amazon_products)
            save_amazon_data(amazon_products)
        except Exception as e:
            print(f"Error scraping Amazon: {e}")
        
        # Random delay between sites
        delay = random.uniform(5, 10)
        print(f"Waiting {delay:.1f} seconds before next site...")
        time.sleep(delay)
        
        # iHerb
        print("\nScraping iHerb...")
        try:
            iherb_products = scrape_iherb(search_query=query, num_pages=pages_per_site)
            all_data["iherb"].extend(iherb_products)
            all_data["combined"].extend(iherb_products)
            save_iherb_data(iherb_products)
        except Exception as e:
            print(f"Error scraping iHerb: {e}")
        
        # Random delay between sites
        delay = random.uniform(5, 10)
        print(f"Waiting {delay:.1f} seconds before next site...")
        time.sleep(delay)
        
        # Sephora
        print("\nScraping Sephora...")
        try:
            sephora_products = scrape_sephora(search_query=query, num_pages=pages_per_site)
            all_data["sephora"].extend(sephora_products)
            all_data["combined"].extend(sephora_products)
            save_sephora_data(sephora_products)
        except Exception as e:
            print(f"Error scraping Sephora: {e}")
        
        # Random delay between sites
        delay = random.uniform(5, 10)
        print(f"Waiting {delay:.1f} seconds before next site...")
        time.sleep(delay)
        
        # Vitacost
        print("\nScraping Vitacost...")
        try:
            vitacost_products = scrape_vitacost(search_query=query, num_pages=pages_per_site)
            all_data["vitacost"].extend(vitacost_products)
            all_data["combined"].extend(vitacost_products)
            save_vitacost_data(vitacost_products)
        except Exception as e:
            print(f"Error scraping Vitacost: {e}")
        
        # Random delay between queries
        if query != search_queries[-1]:
            delay = random.uniform(10, 15)
            print(f"\nWaiting {delay:.1f} seconds before next query...")
            time.sleep(delay)
    
    # Save all data to combined files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save by source
    for source, data in all_data.items():
        if source != "combined" and data:
            filename = f"data/{source}_all_products_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"Saved {len(data)} {source} products to {filename}")
    
    # Save combined data
    combined_filename = f"data/all_products_combined_{timestamp}.json"
    with open(combined_filename, "w", encoding="utf-8") as f:
        json.dump(all_data["combined"], f, indent=4, ensure_ascii=False)
    print(f"Saved {len(all_data['combined'])} total products to {combined_filename}")
    
    return all_data

def add_affiliate_links(data, affiliate_ids):
    """
    Add affiliate IDs to product links
    
    Args:
        data: Dictionary with scraped data by source
        affiliate_ids: Dictionary with affiliate IDs by source
    
    Returns:
        Updated data with affiliate links
    """
    for source, products in data.items():
        if source == "combined":
            continue
            
        affiliate_id = affiliate_ids.get(source, "")
        if not affiliate_id:
            continue
            
        for product in products:
            original_link = product.get("link", "")
            if original_link:
                if source == "amazon":
                    # Amazon affiliate format
                    if "?" in original_link:
                        product["affiliate_link"] = f"{original_link}&tag={affiliate_id}"
                    else:
                        product["affiliate_link"] = f"{original_link}?tag={affiliate_id}"
                elif source == "iherb":
                    # iHerb affiliate format
                    product["affiliate_link"] = f"{original_link}?rcode={affiliate_id}"
                elif source == "sephora":
                    # Sephora affiliate format (example)
                    product["affiliate_link"] = f"{original_link}?affiliate_id={affiliate_id}"
                elif source == "vitacost":
                    # Vitacost affiliate format (example)
                    product["affiliate_link"] = f"{original_link}?affiliate={affiliate_id}"
    
    # Update combined data with affiliate links
    for product in data["combined"]:
        source = product.get("source", "")
        if source and "link" in product:
            affiliate_id = affiliate_ids.get(source, "")
            if affiliate_id:
                original_link = product.get("link", "")
                if source == "amazon":
                    if "?" in original_link:
                        product["affiliate_link"] = f"{original_link}&tag={affiliate_id}"
                    else:
                        product["affiliate_link"] = f"{original_link}?tag={affiliate_id}"
                elif source == "iherb":
                    product["affiliate_link"] = f"{original_link}?rcode={affiliate_id}"
                elif source == "sephora":
                    product["affiliate_link"] = f"{original_link}?affiliate_id={affiliate_id}"
                elif source == "vitacost":
                    product["affiliate_link"] = f"{original_link}?affiliate={affiliate_id}"
    
    return data

if __name__ == "__main__":
    # Example search queries relevant to the project
    search_queries = [
        "weight loss supplements",
        "collagen powder",
        "vitamin d3 supplements",
        "retinol cream",
        "anti aging serum"
    ]
    
    # Example affiliate IDs (replace with actual IDs)
    affiliate_ids = {
        "amazon": "youramazonid-20",
        "iherb": "ABC123",
        "sephora": "SEPH456",
        "vitacost": "VITA789"
    }
    
    # Run all scrapers
    print("Starting product scraping across all sites...")
    all_data = run_all_scrapers(search_queries, pages_per_site=2)
    
    # Add affiliate links
    print("\nAdding affiliate links to product data...")
    all_data_with_affiliates = add_affiliate_links(all_data, affiliate_ids)
    
    # Save final data with affiliate links
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_filename = f"data/final_products_with_affiliates_{timestamp}.json"
    
    with open(final_filename, "w", encoding="utf-8") as f:
        json.dump(all_data_with_affiliates["combined"], f, indent=4, ensure_ascii=False)
    
    print(f"\nScraping complete! Final data saved to {final_filename}")
    print(f"Total products scraped: {len(all_data_with_affiliates['combined'])}")
    
    # Print summary by source
    print("\nProducts by source:")
    for source, products in all_data_with_affiliates.items():
        if source != "combined":
            print(f"- {source.capitalize()}: {len(products)} products")