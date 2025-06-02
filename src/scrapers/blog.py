import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import random
import os
from tqdm import tqdm
from weasyprint import HTML, CSS

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3', 
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/56.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
]

headers = {
    'User-Agent': random.choice(user_agents)
}

BASE_URL = 'https://aws.amazon.com/blogs/architecture/'
PDF_DOWNLOAD_DIR = 'pdf_blog'
HTML_DOWNLOAD_DIR = 'html_blogs'
os.makedirs(PDF_DOWNLOAD_DIR, exist_ok=True)  # Create directory to save PDFs
os.makedirs(HTML_DOWNLOAD_DIR, exist_ok=True)  # Create directory to save HTML files

# CSS to limit image width and keep it responsive
custom_css = """
    img {
        max-width: 100%;
        height: auto;
    }
    body {
        margin: 0 auto;
        padding: 20px;
    }
    article {
        font-family: Arial, sans-serif;
    }
"""

def get_all_blog_posts(base_url, total_pages=68):
    """ Loop through all pages and gather blog post URLs """
    blog_posts = []
    
    for page_number in tqdm(range(2, total_pages + 1), desc="Fetching blog posts"):
        # Construct the correct pagination URL
        url = f"{base_url}page/{page_number}/"
        print(f"Fetching blog posts from: {url}")
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching page {page_number}, status code {response.status_code}")
            continue

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract all blog post links on the current page
        articles = soup.find_all('article', class_='blog-post')
        if not articles:
            print(f"No blog posts found on page {page_number}.")
            continue

        for article in articles:
            # Extract the URL from the anchor inside the h2 tag
            a_tag = article.find('h2', class_='blog-post-title').find('a', href=True)
            if a_tag:
                full_link = urljoin(base_url, a_tag['href'])
                blog_posts.append(full_link)

        # Polite scraping: sleep between requests
        time.sleep(random.uniform(1, 3))

    return blog_posts

def process_blog_posts(blog_posts):
    """ Process each blog post URL to save as PDF and HTML """
    for idx, post_url in enumerate(tqdm(blog_posts, desc="Processing blog posts")):
        print(f"Processing [{idx + 1}/{len(blog_posts)}]: {post_url}")
        download_post_as_pdf(post_url)

def download_post_as_pdf(post_url):
    print(f"Fetching blog post HTML: {post_url}")
    try:
        response = requests.get(post_url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch {post_url}, status code {response.status_code}")
            return

        # Parse the response HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract the <article> content
        article_content = soup.find('article', class_='blog-post')
        if article_content:
            # Preprocess the HTML to fix large images
            preprocess_html(article_content)
            article_html = str(article_content)
        else:
            print(f"No <article> found in {post_url}")
            return

        # Parse URL to create file names
        parsed_url = urlparse(post_url)
        filename = os.path.basename(parsed_url.path.rstrip('/'))

        # Save the extracted HTML content
        html_path = os.path.join(HTML_DOWNLOAD_DIR, filename + '.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(article_html)
        print(f"Saved extracted HTML to {html_path}")

        # Convert the extracted HTML content to PDF with custom CSS
        pdf_path = os.path.join(PDF_DOWNLOAD_DIR, filename + '.pdf')
        if os.path.exists(pdf_path):
            print(f"{pdf_path} already exists, skipping PDF conversion.")
        else:
            # Apply custom CSS to scale images properly
            HTML(string=article_html).write_pdf(pdf_path, stylesheets=[CSS(string=custom_css)])
            print(f"Saved PDF to {pdf_path}")

        # Polite scraping: sleep between requests
        time.sleep(random.uniform(1, 3))

    except Exception as e:
        print(f"Failed to download {post_url} as PDF. Error: {e}")

def preprocess_html(article_content):
    """ Preprocess the HTML content to remove large image dimensions """
    images = article_content.find_all('img')
    for img in images:
        # Remove inline width and height attributes if they exist
        if img.has_attr('width'):
            del img['width']
        if img.has_attr('height'):
            del img['height']

        # Optional: If the image has a parent container that also sets width (e.g., a div with a fixed size), reset that too.
        parent_div = img.find_parent('div')
        if parent_div and 'style' in parent_div.attrs:
            del parent_div['style']  # Remove any inline styles that might force fixed sizes

def main():
    print("Starting to fetch blog posts...")
    blog_posts = get_all_blog_posts(BASE_URL)
    print(f"Found {len(blog_posts)} blog posts.")

    # Process each blog post (download HTML and convert to PDF)
    process_blog_posts(blog_posts)

if __name__ == "__main__":
    main()