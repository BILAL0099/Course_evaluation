"""
Browser manager using Playwright for SCORM course navigation.
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


class BrowserManager:
    """Manages Playwright browser for SCORM course testing."""
    
    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        screenshot_dir: Optional[Path] = None
    ):
        self.headless = headless
        self.timeout = timeout
        self.screenshot_dir = screenshot_dir
        
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # Load SCORM stub script
        stub_path = Path(__file__).parent / "scorm_stub.js"
        with open(stub_path, 'r', encoding='utf-8') as f:
            self.scorm_stub_script = f.read()
    
    async def start(self):
        """Start the browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-web-security',
                '--allow-file-access-from-files',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        self._context = await self._browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True,
            permissions=['clipboard-read', 'clipboard-write']
        )
        
        # Inject SCORM stub before any page loads
        await self._context.add_init_script(self.scorm_stub_script)
        
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout)
        
        # Listen for console messages
        self._page.on('console', self._on_console)
        self._page.on('pageerror', self._on_error)
    
    async def stop(self):
        """Stop the browser."""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
    
    async def navigate(self, url: str) -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to (can be file:// URL)
            
        Returns:
            True if navigation successful
        """
        try:
            await self._page.goto(url, wait_until='networkidle')
            return True
        except Exception as e:
            print(f"Navigation error: {e}")
            return False
    
    async def navigate_to_file(self, file_path: Path) -> bool:
        """
        Navigate to a local file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if navigation successful
        """
        url = f"file:///{str(file_path).replace(chr(92), '/')}"
        return await self.navigate(url)
    
    async def take_screenshot(
        self, 
        name: str, 
        full_page: bool = False
    ) -> Optional[Path]:
        """
        Take a screenshot of the current page.
        
        Args:
            name: Screenshot filename (without extension)
            full_page: Whether to capture full page
            
        Returns:
            Path to the saved screenshot
        """
        if not self.screenshot_dir:
            return None
        
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = self.screenshot_dir / f"{name}.png"
        
        await self._page.screenshot(
            path=str(screenshot_path),
            full_page=full_page
        )
        
        return screenshot_path
    
    async def get_scorm_data(self) -> Dict[str, Any]:
        """Get the current SCORM tracking data."""
        try:
            return await self._page.evaluate('() => window.__SCORM__.getSummary()')
        except:
            return {}
    
    async def get_scorm_calls(self) -> list:
        """Get all SCORM API calls made."""
        try:
            return await self._page.evaluate('() => window.__SCORM__.calls')
        except:
            return []
    
    async def reset_scorm_tracking(self):
        """Reset SCORM tracking data."""
        try:
            await self._page.evaluate('() => window.__SCORM__.reset()')
        except:
            pass
    
    async def get_page_text(self) -> str:
        """Get all visible text from the page."""
        try:
            return await self._page.evaluate('''() => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: function(node) {
                            const parent = node.parentElement;
                            if (!parent) return NodeFilter.FILTER_REJECT;
                            
                            const style = window.getComputedStyle(parent);
                            if (style.display === 'none' || style.visibility === 'hidden') {
                                return NodeFilter.FILTER_REJECT;
                            }
                            
                            const tag = parent.tagName.toLowerCase();
                            if (['script', 'style', 'noscript'].includes(tag)) {
                                return NodeFilter.FILTER_REJECT;
                            }
                            
                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );
                
                let text = [];
                let node;
                while (node = walker.nextNode()) {
                    const trimmed = node.textContent.trim();
                    if (trimmed) text.push(trimmed);
                }
                return text.join(' ');
            }''')
        except:
            return ""
    
    async def get_page_title(self) -> Optional[str]:
        """Get the page title or main heading."""
        try:
            # Try document title first
            title = await self._page.title()
            if title and title.strip():
                return title.strip()
            
            # Try h1
            h1 = await self._page.query_selector('h1')
            if h1:
                text = await h1.text_content()
                if text and text.strip():
                    return text.strip()
            
            return None
        except:
            return None
    
    async def click_element(self, selector: str) -> bool:
        """
        Click an element.
        
        Args:
            selector: CSS selector
            
        Returns:
            True if click successful
        """
        try:
            element = await self._page.query_selector(selector)
            if element:
                await element.click()
                return True
            return False
        except:
            return False
    
    async def find_navigation_buttons(self) -> Dict[str, Optional[str]]:
        """
        Find common navigation buttons on the page.
        
        Returns:
            Dict with 'next', 'prev', 'submit' keys and their selectors
        """
        nav_buttons = {
            'next': None,
            'prev': None,
            'submit': None
        }
        
        # Common patterns for next buttons
        next_patterns = [
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'a:has-text("Next")',
            '[class*="next"]',
            '[id*="next"]',
            '[aria-label*="next" i]',
            'button:has-text(">")',
            '.nav-next',
            '.btn-next',
            '#nextBtn',
            '#next'
        ]
        
        # Common patterns for previous buttons
        prev_patterns = [
            'button:has-text("Previous")',
            'button:has-text("Back")',
            'a:has-text("Previous")',
            '[class*="prev"]',
            '[id*="prev"]',
            '[aria-label*="previous" i]',
            'button:has-text("<")',
            '.nav-prev',
            '.btn-prev',
            '#prevBtn',
            '#prev'
        ]
        
        # Common patterns for submit buttons
        submit_patterns = [
            'button:has-text("Submit")',
            'input[type="submit"]',
            'button[type="submit"]',
            '[class*="submit"]',
            '#submitBtn'
        ]
        
        for pattern in next_patterns:
            try:
                element = await self._page.query_selector(pattern)
                if element and await element.is_visible():
                    nav_buttons['next'] = pattern
                    break
            except:
                continue
        
        for pattern in prev_patterns:
            try:
                element = await self._page.query_selector(pattern)
                if element and await element.is_visible():
                    nav_buttons['prev'] = pattern
                    break
            except:
                continue
        
        for pattern in submit_patterns:
            try:
                element = await self._page.query_selector(pattern)
                if element and await element.is_visible():
                    nav_buttons['submit'] = pattern
                    break
            except:
                continue
        
        return nav_buttons
    
    async def click_next(self) -> bool:
        """Try to click the next button."""
        nav = await self.find_navigation_buttons()
        if nav['next']:
            return await self.click_element(nav['next'])
        return False
    
    async def press_key(self, key: str):
        """Press a keyboard key."""
        await self._page.keyboard.press(key)
    
    async def press_skip_key(self, combo: str = "Control+Shift+S"):
        """Press the skip key combination."""
        keys = combo.split('+')
        modifiers = []
        key = keys[-1]
        
        for k in keys[:-1]:
            if k.lower() in ['control', 'ctrl']:
                modifiers.append('Control')
            elif k.lower() in ['shift']:
                modifiers.append('Shift')
            elif k.lower() in ['alt']:
                modifiers.append('Alt')
            elif k.lower() in ['meta', 'cmd', 'command']:
                modifiers.append('Meta')
        
        for mod in modifiers:
            await self._page.keyboard.down(mod)
        
        await self._page.keyboard.press(key)
        
        for mod in reversed(modifiers):
            await self._page.keyboard.up(mod)
    
    async def get_all_buttons(self) -> list[Dict[str, Any]]:
        """Get all visible buttons on the page."""
        try:
            return await self._page.evaluate('''() => {
                const buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"], a.btn, [role="button"]');
                return Array.from(buttons)
                    .filter(b => {
                        const style = window.getComputedStyle(b);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    })
                    .map(b => ({
                        tag: b.tagName.toLowerCase(),
                        text: b.textContent?.trim() || b.value || '',
                        id: b.id,
                        className: b.className,
                        disabled: b.disabled || false,
                        visible: true
                    }));
            }''')
        except:
            return []
    
    async def get_media_elements(self) -> list[Dict[str, Any]]:
        """Get all media elements on the page."""
        try:
            return await self._page.evaluate('''() => {
                const media = [];
                
                // Audio elements
                document.querySelectorAll('audio').forEach(el => {
                    media.push({
                        type: 'audio',
                        src: el.src || el.querySelector('source')?.src,
                        paused: el.paused,
                        duration: el.duration,
                        error: el.error?.message
                    });
                });
                
                // Video elements
                document.querySelectorAll('video').forEach(el => {
                    media.push({
                        type: 'video',
                        src: el.src || el.querySelector('source')?.src,
                        paused: el.paused,
                        duration: el.duration,
                        width: el.videoWidth,
                        height: el.videoHeight,
                        error: el.error?.message
                    });
                });
                
                // Iframes (potential embedded media)
                document.querySelectorAll('iframe').forEach(el => {
                    media.push({
                        type: 'iframe',
                        src: el.src
                    });
                });
                
                return media;
            }''')
        except:
            return []
    
    async def check_for_errors(self) -> list[str]:
        """Check for JavaScript errors on the page."""
        try:
            return await self._page.evaluate('''() => {
                return window.__pageErrors || [];
            }''')
        except:
            return []
    
    async def wait_for_stable(self, timeout: float = 2.0):
        """Wait for the page to become stable (no network activity)."""
        try:
            await self._page.wait_for_load_state('networkidle', timeout=timeout * 1000)
        except:
            pass
        
        # Additional wait for animations
        await asyncio.sleep(0.5)
    
    async def get_current_url(self) -> str:
        """Get the current page URL."""
        return self._page.url
    
    async def has_content_changed(self, previous_text: str) -> bool:
        """Check if page content has changed from previous state."""
        current_text = await self.get_page_text()
        return current_text != previous_text
    
    def _on_console(self, msg):
        """Handle console messages."""
        # Could log these for debugging
        pass
    
    def _on_error(self, error):
        """Handle page errors."""
        print(f"Page error: {error}")
