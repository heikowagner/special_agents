"""
Newsletter Opt-Out Module
Automates the process of unsubscribing from newsletters
"""
import logging
import re
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import requests
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsletterOptOut:
    def __init__(self, headless: bool = True, timeout: int = 10, openai_api_key: Optional[str] = None):
        """Initialize newsletter opt-out handler"""
        self.headless = headless
        self.timeout = timeout
        self.client = OpenAI(api_key=openai_api_key) if openai_api_key else None
    
    def find_unsubscribe_link(self, email_body: str, email_headers: dict, use_llm: bool = True) -> Optional[str]:
        """
        Find unsubscribe link in email body or headers
        Returns the unsubscribe URL if found
        First tries LLM if available, then falls back to regex patterns
        """
        # First, try LLM-based extraction if available
        if use_llm and self.client:
            llm_result = self._find_unsubscribe_link_with_llm(email_body, email_headers)
            if llm_result:
                logger.info(f"LLM found unsubscribe link: {llm_result}")
                return llm_result
        
        # Fall back to header-based detection
        list_unsubscribe = email_headers.get('List-Unsubscribe', '')
        if list_unsubscribe:
            url_match = re.search(r'<(https?://[^>]+)>', list_unsubscribe)
            if url_match:
                logger.info("Found unsubscribe link in List-Unsubscribe header")
                return url_match.group(1)
        
        # Fall back to regex patterns in email body
        logger.info("LLM not available or unsuccessful, using regex fallback")
        return self._find_unsubscribe_link_with_regex(email_body)
    
    def _find_unsubscribe_link_with_llm(self, email_body: str, email_headers: dict) -> Optional[str]:
        """
        Use OpenAI API to intelligently find unsubscribe links
        This is smarter than regex and handles various formats
        """
        try:
            prompt = f"""You are an email analysis expert. Extract the unsubscribe/opt-out URL from this email content.

Email Headers (relevant):
List-Unsubscribe: {email_headers.get('List-Unsubscribe', 'N/A')}

Email Body (first 2000 chars):
{email_body[:2000]}

Find and return ONLY the unsubscribe/opt-out URL. Look for:
- Links labeled "unsubscribe", "opt-out", "manage preferences", "manage subscriptions"
- URLs in List-Unsubscribe header
- Any footer links related to email preferences
- Alternative text like "click here to unsubscribe" or similar

Return ONLY the URL in this format:
URL: https://example.com/unsubscribe?token=123

If no unsubscribe link is found, respond with:
URL: NOT_FOUND

Do not include any other text in your response."""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an email analysis assistant. Extract unsubscribe URLs from email content. Return only the URL, nothing else."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            result = response.choices[0].message.content.strip()
            
            # Extract URL from response
            if "URL:" in result:
                url = result.split("URL:")[-1].strip()
                if url and url.startswith("http"):
                    # Validate it's a proper URL
                    if re.match(r'https?://[^\s]+', url):
                        logger.info(f"LLM extracted unsubscribe URL: {url}")
                        return url
                elif url != "NOT_FOUND":
                    logger.warning(f"LLM returned invalid URL format: {url}")
            
            logger.info("LLM could not find unsubscribe link")
            return None
            
        except Exception as e:
            logger.error(f"LLM unsubscribe link extraction failed: {e}")
            return None
    
    def _find_unsubscribe_link_with_regex(self, email_body: str) -> Optional[str]:
        """Search for unsubscribe link in email body using regex patterns"""
        patterns = [
            r'<a[^>]*href=["\']([^"\']*unsubscribe[^"\']*)["\']',
            r'<a[^>]*href=["\']([^"\']*opt-out[^"\']*)["\']',
            r'<a[^>]*href=["\']([^"\']*manage[^"\']*preference[^"\']*)["\']',
            r'https?://[^\s<>"{}|\\^`\[\]]*unsubscribe[^\s<>"{}|\\^`\[\]]*',
            r'https?://[^\s<>"{}|\\^`\[\]]*opt-out[^\s<>"{}|\\^`\[\]]*',
            r'https?://[^\s<>"{}|\\^`\[\]]*manage.*preference[^\s<>"{}|\\^`\[\]]*',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, email_body, re.IGNORECASE)
            if matches:
                url = matches[0]
                if url.startswith('http'):
                    logger.info(f"Regex found unsubscribe link: {url}")
                    return url
                elif not url.startswith('mailto:'):
                    logger.info(f"Regex found potential unsubscribe link: {url}")
                    return url
        
        return None
    
    def opt_out_from_newsletter(self, unsubscribe_url: str, email_subject: str) -> Tuple[bool, str]:
        """
        Attempt to opt-out from a newsletter by visiting the unsubscribe link
        Returns (success, message)
        """
        try:
            logger.info(f"Attempting to opt-out from: {unsubscribe_url}")
            
            # Try simple HTTP request first
            try:
                response = requests.get(unsubscribe_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    logger.info(f"Successfully accessed unsubscribe page: {unsubscribe_url}")
                    
                    # Try to find and click unsubscribe button
                    return self._process_unsubscribe_page(response.text, unsubscribe_url)
            except requests.RequestException as e:
                logger.warning(f"Simple request failed, trying with Selenium: {e}")
            
            # If simple request fails, use Selenium
            return self._opt_out_with_selenium(unsubscribe_url, email_subject)
            
        except Exception as e:
            logger.error(f"Failed to opt-out: {e}")
            return False, f"Error during opt-out: {str(e)}"
    
    def _process_unsubscribe_page(self, html_content: str, url: str) -> Tuple[bool, str]:
        """Process unsubscribe page HTML and attempt to find confirmation"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for success messages
            success_patterns = ['unsubscribed', 'opt.out', 'removed', 'no longer receive', 'successfully']
            page_text = soup.get_text().lower()
            
            for pattern in success_patterns:
                if pattern in page_text:
                    logger.info(f"Found success indicator: {pattern}")
                    return True, f"Successfully unsubscribed from newsletter (found: {pattern})"
            
            # Try to find unsubscribe button
            buttons = soup.find_all(['button', 'a'], class_=re.compile(r'unsubscribe|opt-out|confirm', re.I))
            if buttons:
                logger.info(f"Found unsubscribe button: {buttons[0].text}")
                return True, "Found unsubscribe button - manual confirmation may be needed"
            
            return True, "Accessed unsubscribe page successfully"
            
        except Exception as e:
            logger.error(f"Error processing unsubscribe page: {e}")
            return False, f"Could not process page: {str(e)}"
    
    def _opt_out_with_selenium(self, unsubscribe_url: str, email_subject: str) -> Tuple[bool, str]:
        """Use Selenium to automate unsubscribe process"""
        driver = None
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_page_load_timeout(self.timeout)
            
            logger.info(f"Opening unsubscribe URL: {unsubscribe_url}")
            driver.get(unsubscribe_url)
            
            # Wait a bit for page to load
            import time
            time.sleep(2)
            
            # Try to find and click unsubscribe/opt-out button
            button_selectors = [
                "button[class*='unsubscribe']",
                "button[class*='opt-out']",
                "a[class*='unsubscribe']",
                "a[class*='opt-out']",
                "input[type='submit'][value*='unsubscribe']",
                "button:contains('Unsubscribe')",
            ]
            
            clicked = False
            for selector in button_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found button with selector: {selector}")
                        elements[0].click()
                        clicked = True
                        time.sleep(2)
                        break
                except:
                    continue
            
            # Check for success message
            final_text = driver.page_source.lower()
            if any(word in final_text for word in ['unsubscribed', 'opt.out', 'removed', 'no longer receive']):
                logger.info("Found success confirmation")
                return True, "Successfully unsubscribed from newsletter"
            
            if clicked:
                return True, "Clicked unsubscribe button - unsubscription may be processing"
            
            return False, "Could not find unsubscribe button on page"
            
        except Exception as e:
            logger.error(f"Selenium error: {e}")
            return False, f"Selenium error: {str(e)}"
        finally:
            if driver:
                driver.quit()
