# utils/content_summarizer.py
import logging
import httpx
from bs4 import BeautifulSoup
import re
import google.generativeai as genai
from config.config import Config

class ContentSummarizer:
    """Fetches and summarizes content from web pages using Google's Gemini API."""
    
    # Maximum timeout for HTTP requests (in seconds)
    REQUEST_TIMEOUT = 30
    
    # Maximum content length to send to Gemini (characters)
    MAX_CONTENT_LENGTH = 30000
    
    def __init__(self, api_key=None):
        """Initialize the summarizer with configuration."""
        self.logger = logging.getLogger(__name__)
        
        # Allow passing API key directly or get it from config
        if api_key:
            self.gemini_api_key = api_key
        else:
            config = Config.get_instance()
            self.gemini_api_key = config.GEMINI_API_KEY
        
        if not self.gemini_api_key:
            self.logger.error("Gemini API key not found in configuration")
            raise ValueError("Gemini API key is required for content summarization")
        
        # Configure the Gemini API
        genai.configure(api_key=self.gemini_api_key)
        
        # Set up the Gemini model
        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    async def fetch_webpage(self, url):
        """
        Fetch webpage content from the provided URL.
        
        Args:
            url (str): The URL to fetch
            
        Returns:
            tuple: (success, content or error message)
        """
        self.logger.info(f"Fetching content from URL: {url}")
        
        try:
            # Set headers to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            # Fetch the webpage
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url, 
                    headers=headers, 
                    timeout=self.REQUEST_TIMEOUT,
                    follow_redirects=True
                )
                
                # Check response status
                if response.status_code != 200:
                    return False, f"Error fetching page: HTTP {response.status_code}"
                
                return True, response.text
                
        except httpx.TimeoutException:
            error_msg = f"Timeout while fetching URL: {url}"
            self.logger.warning(error_msg)
            return False, "Request timed out. The website might be slow or unavailable."
            
        except Exception as e:
            error_msg = f"Error fetching URL {url}: {str(e)}"
            self.logger.error(error_msg)
            return False, f"Error fetching webpage: {str(e)}"
    
    def extract_main_content(self, html_content):
        """
        Extract the main text content from HTML.
        
        Args:
            html_content (str): Raw HTML content
            
        Returns:
            tuple: (title, main_content)
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for tag in ['script', 'style', 'nav', 'footer', 'header', 'aside']:
                for element in soup.find_all(tag):
                    element.decompose()
            
            # Extract title
            title = ""
            title_tag = soup.find('title')
            if title_tag and title_tag.text:
                title = title_tag.text.strip()
            
            # Try to find main content container
            main_content = None
            
            # First check for article or main tags
            for tag in ['article', 'main']:
                content = soup.find(tag)
                if content:
                    main_content = content
                    break
            
            # If not found, look for common content containers
            if not main_content:
                for selector in ['div.content', 'div.post', 'div.article', '#content', '#main-content']:
                    try:
                        content = soup.select_one(selector)
                        if content:
                            main_content = content
                            break
                    except Exception:
                        continue
            
            # If still not found, use the body
            if not main_content:
                main_content = soup.body
            
            if not main_content:
                return title, "Could not extract content from this page."
            
            # Extract paragraphs from main content
            paragraphs = []
            for p in main_content.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 20:  # Skip very short paragraphs
                    paragraphs.append(text)
            
            # Combine paragraphs and clean up text
            content = '\n\n'.join(paragraphs)
            content = re.sub(r'\s+', ' ', content).strip()
            
            # If content is too large, truncate it
            if len(content) > self.MAX_CONTENT_LENGTH:
                content = content[:self.MAX_CONTENT_LENGTH] + "..."
            
            if not content:
                return title, "Could not extract meaningful content from this page."
            
            return title, content
            
        except Exception as e:
            error_msg = f"Error extracting content: {str(e)}"
            self.logger.error(error_msg)
            return "", f"Error parsing page content: {str(e)}"
    
    async def generate_summary(self, title, content):
        """
        Generate a summary using the Gemini API.
        
        Args:
            title (str): The title of the webpage
            content (str): The content to summarize
            
        Returns:
            tuple: (success, summary or error message)
        """
        try:
            # Create a prompt for Gemini
            prompt = f"""
            Summarize the following web article. Create a concise, informative summary capturing the main points.
            
            Title: {title}
            
            Content:
            {content}
            
            Format your response as:
            1. A brief overview in 1-2 sentences
            2. 3-5 key points from the article
            3. A conclusion sentence
            
            Keep the summary concise and focused on the most important information.
            """
            
            # Generate summary using Gemini
            response = await self.model.generate_content_async(prompt)
            
            # Extract and format the summary
            if hasattr(response, 'text'):
                return True, response.text
            else:
                # For older versions of the API
                return True, response.parts[0].text
                
        except Exception as e:
            error_msg = f"Error generating summary with Gemini API: {str(e)}"
            self.logger.error(error_msg)
            return False, f"Error generating summary: {str(e)}"
    
    async def summarize_url(self, url):
        """
        Main method to fetch a URL and generate a summary.
        
        Args:
            url (str): The URL to summarize
            
        Returns:
            tuple: (success, title, summary or error message)
        """
        self.logger.info(f"Starting summarization process for URL: {url}")
        
        # Step 1: Fetch the webpage
        success, content = await self.fetch_webpage(url)
        if not success:
            return False, "", content
        
        # Step 2: Extract the main content
        title, main_content = self.extract_main_content(content)
        if not main_content or main_content.startswith("Error"):
            return False, title, main_content
        
        # Step 3: Generate a summary with Gemini
        success, summary = await self.generate_summary(title, main_content)
        if not success:
            return False, title, summary
        
        return True, title, summary