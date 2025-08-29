import os
import requests
import subprocess
import json
from datetime import datetime, timedelta, timezone
import time

# --- CONFIGURATION ---
# IMPORTANT: Replace this with your actual News API key.
# You can get one for free at https://newsapi.org/
NEWS_API_KEY = "3e7f417946b240c9b4fa7ec42df99bb6"
# The URL for the News API endpoint.
NEWS_API_URL = "https://newsapi.org/v2/everything"
# The path to your Git repository.
REPO_PATH = "."
# The name of the HTML file to update.
HTML_FILE = "index.html"
# The name of the JSON file to store articles.
ARTICLES_JSON_FILE = "articles.json"

def get_articles_from_newsapi(api_key):
    """
    Fetches the latest news articles from a news source.
    """
    try:
        # We'll use the 'everything' endpoint to get the latest articles from any source.
        params = {
            'q': 'technology', # You can change this query to get news on any topic.
            'sortBy': 'publishedAt',
            'apiKey': api_key,
            'pageSize': 1, # Get only one article to add per run.
            'language': 'en'
        }
        response = requests.get(NEWS_API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'ok' and data['articles']:
            return data['articles']
        else:
            print(f"No articles found or API error: {data.get('message', 'Unknown error')}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news from API: {e}")
        return []

def update_files_and_git():
    """
    Manages the entire process: fetching, updating files, and committing to Git.
    """
    # Change to the repository directory to ensure git commands work correctly.
    try:
        os.chdir(REPO_PATH)
        print(f"Changed directory to {REPO_PATH}")
    except FileNotFoundError:
        print(f"Error: Repository path not found at {REPO_PATH}")
        return

    # Check if the local time hour is odd.
    now = datetime.now()
    if not (now.hour % 2 != 0):
        print("Current hours is even. Exiting without updating.")
        return

    print("Current time is within the update window. Proceeding with update...")

    # --- 1. FETCH NEW ARTICLE ---
    new_articles = get_articles_from_newsapi(NEWS_API_KEY)
    if not new_articles:
        print("Could not retrieve new articles. Exiting.")
        return
    
    new_article = new_articles[0]

    # --- 2. UPDATE ARTICLE DATA JSON ---
    all_articles = []
    if os.path.exists(ARTICLES_JSON_FILE):
        try:
            with open(ARTICLES_JSON_FILE, 'r') as f:
                all_articles = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {ARTICLES_JSON_FILE} is empty or corrupt. Starting with a new file.")

    all_articles.append(new_article)

    # Filter articles to keep only the last 72 hours.
    time_limit = datetime.now(timezone.utc) - timedelta(hours=72)
    filtered_articles = []
    for article in all_articles:
        try:
            published_at = datetime.fromisoformat(article.get('publishedAt').replace('Z', '+00:00')).astimezone(timezone.utc)
            if published_at >= time_limit:
                filtered_articles.append(article)
        except (TypeError, ValueError) as e:
            print(f"Warning: Could not parse published date for an article. Skipping. Error: {e}")
            
    with open(ARTICLES_JSON_FILE, 'w') as f:
        json.dump(filtered_articles, f, indent=2)
    
    print(f"Updated {ARTICLES_JSON_FILE} with {len(filtered_articles)} articles.")

    # --- 3. GENERATE AND UPDATE THE HTML FILE ---
    articles_html = ""
    for article in filtered_articles:
        articles_html += f"""
        <div class="p-4 mb-4 bg-gray-100 rounded-lg shadow-md">
            <h2 class="text-xl font-bold mb-2"><a href="{article['url']}" class="text-blue-600 hover:underline">{article['title']}</a></h2>
            <p class="text-gray-700">{article.get('description', 'No description available.')}</p>
            <p class="text-sm text-gray-500 mt-2">Published: {article['publishedAt']}</p>
        </div>
        """
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily News Digest</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
            padding: 2rem;
        }}
        .container {{
            max-width: 800px;
            margin: auto;
            background-color: #fff;
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-4xl font-bold text-center mb-6">Daily News Digest</h1>
        <div id="news-container">
            {articles_html}
        </div>
    </div>
</body>
</html>
"""
    
    with open(HTML_FILE, 'w') as f:
        f.write(html_content)
    
    print(f"Successfully generated {HTML_FILE}.")

    # --- 4. COMMIT AND PUSH CHANGES ---
    try:
        subprocess.run(["git", "add", "."], check=True)
        commit_message = f"Automated update: Added new article on {now.strftime('%Y-%m-%d %H:%M')}."
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Successfully committed and pushed changes to the repository.")
    except subprocess.CalledProcessError as e:
        print(f"Error with Git command: {e}")
        print("Please ensure you have a Git remote configured and are authenticated to push.")

if __name__ == "__main__":
    update_files_and_git()
