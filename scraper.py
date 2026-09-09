import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from database import insert_job, job_exists
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SITEMAP_URL = "https://spse.inaproc.id/sitemap.xml"
CATEGORIES = [
    "Jasa Konsultansi Badan Usaha Non Konstruksi",
    "Jasa Lainnya"
]
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_sitemap_urls():
    urls = []
    try:
        response = requests.get(SITEMAP_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        
        # Namespace might be present
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        for url_tag in root.findall('.//ns:loc', namespaces):
            urls.append(url_tag.text)
    except Exception as e:
        logging.error(f"Error fetching sitemap: {e}")
    
    return urls

session = requests.Session()
session.headers.update(HEADERS)

def fetch_job_details(job_url, source_url):
    value = "Tidak diketahui"
    kbli = "Tidak diketahui"
    try:
        # Add referer to bypass 403 blocks
        custom_headers = {'Referer': source_url}
        response = session.get(job_url, headers=custom_headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for "Nilai Pagu Paket" or "Nilai HPS Paket" and "KBLI" in tables
        rows = soup.find_all('tr')
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            if td:
                text = td.text.strip()
                if "KBLI" in text:
                    kbli = text
                    
            if th and td:
                header_text = th.text.strip()
                if "Nilai Pagu Paket" in header_text or "Nilai HPS Paket" in header_text:
                    if value == "Tidak diketahui": # Don't overwrite Pagu with HPS if both exist
                        value = td.text.strip()
    except Exception as e:
        # Ignore errors (403, etc.) and return defaults
        logging.debug(f"Could not fetch details for {job_url}: {e}")
        pass
    return value, kbli

def scrape_spse_site(url):
    logging.info(f"Scraping {url} ...")
    try:
        # Hit home page first (might help with cookies if hitting same domain)
        response = session.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find category headers/links
        for cat in CATEGORIES:
            cat_elements = soup.find_all(lambda tag: tag.name in ['a', 'h4', 'h5', 'h6', 'div'] and cat in tag.text)
            
            for cat_el in cat_elements:
                parent_container = cat_el.find_parent('div')
                if parent_container:
                    links = parent_container.find_all('a')
                    for link in links:
                        job_title = link.text.strip()
                        job_url = link.get('href')
                        
                        if job_url and ('/lelang/' in job_url or '/nontender/' in job_url):
                            if job_title and job_title != cat:
                                from urllib.parse import urlparse
                                if job_url.startswith('http'):
                                    full_url = job_url
                                else:
                                    if not job_url.startswith('/'):
                                        job_url = '/' + job_url
                                    
                                    parsed = urlparse(url)
                                    slug = parsed.path # e.g., /sumbarprov
                                    if slug and slug != '/':
                                        if not job_url.startswith(slug):
                                            job_url = slug.rstrip('/') + job_url
                                            
                                    full_url = f"{parsed.scheme}://{parsed.netloc}{job_url}"
                                
                                # Skip if already exists in DB
                                if job_exists(full_url):
                                    logging.info(f"Skipping existing job: {job_title}")
                                    continue
                                
                                # Fetch value and kbli
                                job_value, job_kbli = fetch_job_details(full_url, url)
                                
                                # Filter KBLI
                                allowed_kblis = ['70209', '74909', '73202', '73201', '72202', '72209']
                                if not any(k in job_kbli for k in allowed_kblis):
                                    logging.info(f"Skipping due to KBLI {job_kbli[:15]}... : {job_title}")
                                    continue
                                
                                insert_job(
                                    title=job_title,
                                    category=cat,
                                    source_url=url,
                                    job_url=full_url,
                                    value=job_value,
                                    kbli=job_kbli
                                )
                                logging.info(f"Found job: {job_title} ({cat}) - Value: {job_value} - KBLI: {job_kbli[:20]}...")
                                
    except Exception as e:
        logging.error(f"Error scraping {url}: {e}")

def run_scraper(limit=None, progress_callback=None):
    urls = fetch_sitemap_urls()
    msg = f"Found {len(urls)} URLs in sitemap."
    logging.info(msg)
    if progress_callback: progress_callback(msg)
    
    if limit:
        urls = urls[:limit]
        
    for i, url in enumerate(urls):
        msg = f"Scraping {i+1}/{len(urls)}: {url} ..."
        logging.info(msg)
        if progress_callback: progress_callback(msg)
        scrape_spse_site(url)
        time.sleep(1) # Be nice to the server
        
    msg = "Scraping completed."
    logging.info(msg)
    if progress_callback: progress_callback(msg)

if __name__ == '__main__':
    run_scraper(limit=5) # Run a small batch for testing
