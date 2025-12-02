import json
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

class ChatGPTExtractor:
    def __init__(self):
        self.playwright = None
        self.browser = None
        
    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def extract_chat(self, share_url):
        page = await self.browser.new_page()
        
        try:
            print(f"Loading page: {share_url}")
            await page.goto(share_url, wait_until="domcontentloaded", timeout=60000)
            
            # Wait a bit for JavaScript to render
            await asyncio.sleep(3)
            
            # Debug: Print page content to see what we're working with
            print("Checking page content...")
            
            # Try multiple possible selectors
            selectors_to_try = [
                'article',  # Common for chat messages
                '[data-message-author-role]',
                '[class*="message"]',
                '[class*="conversation"]',
                'main',
                'div[role="presentation"]'
            ]
            
            found_selector = None
            for selector in selectors_to_try:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    found_selector = selector
                    print(f"Found content using selector: {selector}")
                    break
                except:
                    continue
            
            if not found_selector:
                # Get page HTML for debugging
                html = await page.content()
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("Page HTML saved to debug_page.html for inspection")
                raise Exception("Could not find chat content on page")
            
            # Extract chat title
            title = await page.evaluate("""
                () => {
                    const titleElement = document.querySelector('h1, h2, [class*="title"]');
                    return titleElement ? titleElement.innerText.trim() : 'Untitled Chat';
                }
            """)
            
            # Extract all messages with multiple strategies
            messages = await page.evaluate("""
                () => {
                    let extractedMessages = [];
                    
                    // Strategy 1: Try data-message-author-role
                    const messageElements = document.querySelectorAll('[data-message-author-role]');
                    if (messageElements.length > 0) {
                        messageElements.forEach((el) => {
                            const role = el.getAttribute('data-message-author-role');
                            const contentEl = el.querySelector('[class*="markdown"], [class*="message"], div');
                            const content = contentEl ? contentEl.innerText : el.innerText;
                            
                            if (content.trim()) {
                                extractedMessages.push({
                                    role: role,
                                    content: content.trim()
                                });
                            }
                        });
                        return extractedMessages;
                    }
                    
                    // Strategy 2: Try article tags (common in ChatGPT)
                    const articles = document.querySelectorAll('article');
                    if (articles.length > 0) {
                        articles.forEach((article, index) => {
                            const content = article.innerText.trim();
                            if (content) {
                                // Alternate between user and assistant
                                const role = index % 2 === 0 ? 'user' : 'assistant';
                                extractedMessages.push({
                                    role: role,
                                    content: content
                                });
                            }
                        });
                        return extractedMessages;
                    }
                    
                    // Strategy 3: Try any div with substantial text content
                    const allDivs = document.querySelectorAll('div');
                    const contentDivs = Array.from(allDivs).filter(div => {
                        const text = div.innerText;
                        return text && text.trim().length > 50 && 
                               div.children.length < 5; // Avoid container divs
                    });
                    
                    contentDivs.forEach((div, index) => {
                        const role = index % 2 === 0 ? 'user' : 'assistant';
                        extractedMessages.push({
                            role: role,
                            content: div.innerText.trim()
                        });
                    });
                    
                    return extractedMessages;
                }
            """)
            
            chat_id = share_url.split('/')[-1]
            
            if not messages or len(messages) == 0:
                print("Warning: No messages extracted")
                print("This might mean:")
                print("  1. The page structure has changed")
                print("  2. The share link is invalid or expired")
                print("  3. JavaScript didn't render properly")
            
            # JSON structure I will change that to something else
            chat_data = {
                "metadata": {
                    "source": "chatgpt",
                    "chat_id": chat_id,
                    "title": title,
                    "extracted_at": datetime.utcnow().isoformat() + "Z",
                    "url": share_url,
                    "message_count": len(messages)
                },
                "messages": messages
            }
            
            print(f"Extracted {len(messages)} messages")
            return chat_data
            
        except Exception as e:
            print(f"Error extracting chat: {str(e)}")
            raise
        finally:
            await page.close()
    
    def save_to_file(self, data, filename="chat_export.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved to {filename}")


async def main():
    """Main execution function"""
    
    # Example usage
    share_url = "https://chatgpt.com/share/69288d0f-be68-8003-bd41-bb79df9f46db"
    
    extractor = ChatGPTExtractor()
    
    try:
        await extractor.start()
        print("Browser started...")
        
        # Extract chat data
        chat_data = await extractor.extract_chat(share_url)
        
        # Print extracted data
        print("\n" + "="*50)
        print("EXTRACTED CHAT DATA:")
        print("="*50)
        print(json.dumps(chat_data, indent=2))
        
        # Save to file
        extractor.save_to_file(chat_data, "chat_export.json")
        
    finally:
        await extractor.close()
        print("\nBrowser closed.")

if __name__ == "__main__":
    asyncio.run(main())


## run the following commands
#--------------------------------------#
## pip install playwright
## playwright install chromium
## pip install asyncio
