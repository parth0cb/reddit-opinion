import datetime
import requests
import torch
import time

from ddgs import DDGS
from bs4 import BeautifulSoup

from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer


tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L12-v2")
model = SentenceTransformer("all-MiniLM-L12-v2")

def gather_contextual_info():
    utc_now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    try:
        response = requests.get("https://ipinfo.io/json")
        response.raise_for_status()
        data = response.json()
        
        city = data.get("city", "Unknown city")
        region = data.get("region", "Unknown region")
        country = data.get("country", "Unknown country")
    except requests.RequestException:
        city = region = country = loc = "Unavailable"
    
    info_str = (
        "Contextual Information:"
        f"Date & Time (UTC): {utc_now}\n"
        f"Approximate Location: {city}, {region}, {country}\n---\n\n"
    )
    
    return info_str

def ensure_scheme(url):
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


def get_top_reddit_urls(query, num_results=15):
    query += " site:reddit.com"
    with DDGS() as ddgs:
        try:
            results = ddgs.text(query, max_results=num_results)
            urls = [r["href"] for r in results]
            return urls
        except Exception:
            return []


def get_text_chunks(text, max_tokens=256, url=""):
    tokens = tokens = tokenizer.tokenize(text)
    chunks = []
    url = url.replace("old.reddit.com", "www.reddit.com")
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk_text = tokenizer.convert_tokens_to_string(chunk_tokens)
        if len(chunk_text.strip()) < 200:
            continue
        chunk_text = chunk_text.strip() + f"\nSource: {url}"
        chunks.append(chunk_text)
    return chunks

def is_mod_comment(entry):
    tagline = entry.find('p', class_='tagline')
    if not tagline:
        return False
    author_link = tagline.find('a', class_='author')
    if author_link and 'moderator' in author_link.get('class', []):
        return True
    userattrs = tagline.find('span', class_='userattrs')
    if userattrs and userattrs.find('a', class_='moderator'):
        return True
    return False

def extract_post_and_comments(url):
    if 'old.reddit.com' not in url:
        url = url.replace("www.reddit.com", "old.reddit.com")
    if 'old.reddit.com' not in url:
        url = url.replace("reddit.com", "old.reddit.com")

    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    chunks = []

    main_post_thing = soup.find('div', class_='thing', attrs={'data-type': 'link'})
    if main_post_thing:
        post_entry = main_post_thing.find('div', class_='entry')
        if post_entry:
            md_div = post_entry.find('div', class_='md')
            if md_div:
                post_text = md_div.get_text(separator='\n', strip=True)
                if post_text:
                    chunks.extend(get_text_chunks(post_text, url=url))

    comment_things = soup.find_all('div', class_='thing', attrs={'data-type': 'comment'})
    for comment_thing in comment_things:
        entry = comment_thing.find('div', class_='entry')
        if not entry or is_mod_comment(entry):
            continue

        md_div = entry.find('div', class_='md')
        if md_div:
            comment_text = md_div.get_text(separator='\n', strip=True)
            if comment_text.lower() not in ['[deleted]', '[removed]'] and comment_text.strip():
                chunks.extend(get_text_chunks(comment_text, url=url))

    return [chunk for chunk in chunks if chunk.strip()]


def get_top_chunks_by_token_limit(query, chunks, max_token_limit=4000):
    query_embedding = model.encode(query, convert_to_tensor=True)
    chunk_embeddings = model.encode(chunks, convert_to_tensor=True)
    similarities = util.cos_sim(query_embedding, chunk_embeddings)[0]

    ranked_indices = torch.argsort(similarities, descending=True)
    selected_chunks = []
    total_tokens = 0

    for idx in ranked_indices:
        chunk = chunks[idx]
        chunk_tokens = len(tokenizer.encode(chunk, add_special_tokens=False))
        if total_tokens + chunk_tokens <= max_token_limit:
            selected_chunks.append(chunk)
            total_tokens += chunk_tokens
        else:
            break

    return selected_chunks