import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.schemas import (
    Issue, 
    IssueType, 
    IssueSeverity, 
    FunctionalCheckResult
)
from src.browser.manager import BrowserManager


class FunctionalAgent:
    """Agent for functional testing of SCORM course slides."""
    
    def __init__(self, browser: BrowserManager):
        self.browser = browser
        self._media_errors: List[str] = []
    
    async def check_slide(self, slide_number: int) -> FunctionalCheckResult:
        """
        Run all functional checks on the current slide.
        
        Args:
            slide_number: Current slide number for issue reporting
            
        Returns:
            FunctionalCheckResult with all findings
        """
        result = FunctionalCheckResult()
        
        # Run checks in parallel where possible
        buttons_task = self._check_buttons(slide_number)
        media_task = self._check_media(slide_number)
        nav_task = self._check_navigation(slide_number)
        
        buttons_result, media_result, nav_result = await asyncio.gather(
            buttons_task, media_task, nav_task
        )
        
        # Merge results
        result.buttons_found = buttons_result['found']
        result.buttons_working = buttons_result['working']
        result.issues.extend(buttons_result['issues'])
        
        result.media_elements = media_result['elements']
        result.media_errors = media_result['errors']
        result.issues.extend(media_result['issues'])
        
        result.navigation_working = nav_result['working']
        result.issues.extend(nav_result['issues'])
        
        # Check for timers
        timers_result = await self._check_timers(slide_number)
        result.timers_found = timers_result['timers']
        result.issues.extend(timers_result['issues'])
        
        return result
    
    async def _check_buttons(self, slide_number: int) -> Dict[str, Any]:
        """Check all buttons on the page."""
        result = {
            'found': [],
            'working': [],
            'issues': []
        }
        
        buttons = await self.browser.get_all_buttons()
        
        for button in buttons:
            button_id = button.get('id') or button.get('text') or 'unknown'
            result['found'].append(button_id)
            
            # Check if button is disabled inappropriately
            if button.get('disabled'):
                # Not necessarily an issue, but track it
                pass
            else:
                result['working'].append(button_id)
            
            # Check for empty buttons (no text, no aria-label)
            if not button.get('text') and not button.get('id'):
                result['issues'].append(Issue(
                    issue_type=IssueType.BUTTON,
                    severity=IssueSeverity.WARNING,
                    message="Button without accessible text found",
                    slide_number=slide_number,
                    element_selector=f"button#{button.get('id', '')}",
                    details={'button': button}
                ))
        
        return result
    
    async def _check_media(self, slide_number: int) -> Dict[str, Any]:
        """Check all media elements on the page."""
        result = {
            'elements': [],
            'errors': [],
            'issues': []
        }
        
        media_elements = await self.browser.get_media_elements()
        
        for media in media_elements:
            result['elements'].append(media)
            
            # Check for media errors
            if media.get('error'):
                error_msg = f"{media['type']} error: {media['error']}"
                result['errors'].append(error_msg)
                result['issues'].append(Issue(
                    issue_type=IssueType.MEDIA,
                    severity=IssueSeverity.ERROR,
                    message=error_msg,
                    slide_number=slide_number,
                    details={'media': media}
                ))
            
            # Check for missing source
            if not media.get('src') and media['type'] in ['audio', 'video']:
                result['issues'].append(Issue(
                    issue_type=IssueType.MEDIA,
                    severity=IssueSeverity.ERROR,
                    message=f"{media['type']} element without source",
                    slide_number=slide_number,
                    details={'media': media}
                ))
            
            # Check video dimensions
            if media['type'] == 'video':
                if media.get('width') == 0 or media.get('height') == 0:
                    result['issues'].append(Issue(
                        issue_type=IssueType.MEDIA,
                        severity=IssueSeverity.WARNING,
                        message="Video element has zero dimensions",
                        slide_number=slide_number,
                        details={'media': media}
                    ))
        
        return result
    
    async def _check_navigation(self, slide_number: int) -> Dict[str, Any]:
        """Check navigation functionality."""
        result = {
            'working': True,
            'issues': []
        }
        
        nav_buttons = await self.browser.find_navigation_buttons()
        
        # Check if we have any navigation
        if not nav_buttons['next'] and not nav_buttons['prev']:
            result['issues'].append(Issue(
                issue_type=IssueType.NAVIGATION,
                severity=IssueSeverity.WARNING,
                message="No standard navigation buttons found",
                slide_number=slide_number,
                details={'nav_buttons': nav_buttons}
            ))
        
        return result
    
    async def _check_timers(self, slide_number: int) -> Dict[str, Any]:
        """Check for timer elements on the page."""
        result = {
            'timers': [],
            'issues': []
        }
        
        try:
            timers = await self.browser._page.evaluate('''() => {
                const timers = [];
                
                // Look for common timer patterns
                const timerSelectors = [
                    '[class*="timer"]',
                    '[id*="timer"]',
                    '[class*="countdown"]',
                    '[id*="countdown"]',
                    '[class*="clock"]',
                    '[class*="time-remaining"]'
                ];
                
                timerSelectors.forEach(selector => {
                    document.querySelectorAll(selector).forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.display !== 'none') {
                            timers.push({
                                selector: selector,
                                text: el.textContent?.trim(),
                                visible: true
                            });
                        }
                    });
                });
                
                return timers;
            }''')
            
            result['timers'] = timers
            
        except Exception as e:
            result['issues'].append(Issue(
                issue_type=IssueType.TIMER,
                severity=IssueSeverity.INFO,
                message=f"Could not check timers: {str(e)}",
                slide_number=slide_number
            ))
        
        return result
    
    async def try_navigate_next(self) -> tuple[bool, str]:
        """
        Try to navigate to the next slide.
        
        Returns:
            Tuple of (success, method_used)
        """
        # Store current state
        previous_url = await self.browser.get_current_url()
        previous_text = await self.browser.get_page_text()
        
        # Try clicking next button
        nav_buttons = await self.browser.find_navigation_buttons()
        
        if nav_buttons['next']:
            success = await self.browser.click_element(nav_buttons['next'])
            if success:
                await self.browser.wait_for_stable()
                
                # Check if content changed
                current_url = await self.browser.get_current_url()
                content_changed = await self.browser.has_content_changed(previous_text)
                
                if current_url != previous_url or content_changed:
                    return True, "button"
        
        # Try keyboard navigation
        for key in ['ArrowRight', 'Space', 'Enter', 'PageDown']:
            await self.browser.press_key(key)
            await asyncio.sleep(0.5)
            
            content_changed = await self.browser.has_content_changed(previous_text)
            if content_changed:
                return True, f"key:{key}"
        
        return False, "none"
    
    async def use_skip_key(self, combo: str = "Control+Shift+S") -> bool:
        """
        Use the skip key combination when stuck.
        
        Args:
            combo: Key combination string
            
        Returns:
            True if skip appeared to work
        """
        previous_text = await self.browser.get_page_text()
        
        await self.browser.press_skip_key(combo)
        await asyncio.sleep(1.0)
        
        return await self.browser.has_content_changed(previous_text)
    
    async def check_scorm_errors(self, slide_number: int) -> List[Issue]:
        """Check for SCORM API errors."""
        issues = []
        
        scorm_data = await self.browser.get_scorm_data()
        
        if not scorm_data:
            return issues
        
        # Check if SCORM was initialized
        if not scorm_data.get('initialized'):
            issues.append(Issue(
                issue_type=IssueType.SCORM_ERROR,
                severity=IssueSeverity.ERROR,
                message="SCORM API not initialized",
                slide_number=slide_number
            ))
        
        # Check for errors in calls
        for error in scorm_data.get('errors', []):
            issues.append(Issue(
                issue_type=IssueType.SCORM_ERROR,
                severity=IssueSeverity.ERROR,
                message=f"SCORM error: {error}",
                slide_number=slide_number,
                details={'error': error}
            ))
        
        return issues
    
    async def is_course_complete(self) -> bool:
        """Check if the course appears to be complete."""
        scorm_data = await self.browser.get_scorm_data()
        
        if not scorm_data or not scorm_data.get('data'):
            return False
        
        data = scorm_data['data']
        
        # Check SCORM 1.2 completion
        lesson_status = data.get('cmi.core.lesson_status', '')
        if lesson_status in ['completed', 'passed']:
            return True
        
        # Check SCORM 2004 completion
        completion_status = data.get('cmi.completion_status', '')
        if completion_status == 'completed':
            return True
        
        # Check if terminated
        if scorm_data.get('terminated'):
            return True
        
        return False
