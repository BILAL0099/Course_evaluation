"""
Review orchestrator - coordinates functional and content agents.
"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from config import settings
from src.schemas import (
    SCORMManifest,
    ReviewProgress,
    ReviewReport,
    ReviewStatus,
    SlideResult,
    Issue,
    IssueType,
    IssueSeverity
)
from src.browser.manager import BrowserManager
from src.agents.functional import FunctionalAgent
from src.agents.content import ContentAgent


class ReviewOrchestrator:
    """
    Main controller that coordinates the review process.
    
    Manages browser, navigates through slides, and coordinates
    functional and content agents.
    """
    
    def __init__(
        self,
        review_id: str,
        extract_path: Path,
        manifest: SCORMManifest,
        progress: ReviewProgress
    ):
        self.review_id = review_id
        self.extract_path = extract_path
        self.manifest = manifest
        self.progress = progress
        
        # Initialize components
        self.screenshot_dir = settings.screenshots_dir / review_id
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        self.browser: Optional[BrowserManager] = None
        self.functional_agent: Optional[FunctionalAgent] = None
        self.content_agent: Optional[ContentAgent] = None
        
        # Review state
        self.slides: list[SlideResult] = []
        self.current_slide = 0
        self.stuck_count = 0
        self.max_stuck = 3  # Max times to try skip before giving up
    
    async def run(self) -> ReviewReport:
        """
        Run the complete review process.
        
        Returns:
            ReviewReport with all findings
        """
        try:
            await self._initialize()
            await self._load_course()
            await self._review_slides()
            return self._generate_report()
        
        finally:
            await self._cleanup()
    
    async def _initialize(self):
        """Initialize all components."""
        # Start browser
        self.browser = BrowserManager(
            headless=settings.headless,
            timeout=settings.browser_timeout,
            screenshot_dir=self.screenshot_dir
        )
        await self.browser.start()
        
        # Initialize agents
        self.functional_agent = FunctionalAgent(self.browser)
        self.content_agent = ContentAgent()
        await self.content_agent.initialize()
        
        # Set course context for AI agents
        self.content_agent.set_course_context({
            'course_title': self.manifest.title,
            'scorm_version': self.manifest.scorm_version,
            'review_id': self.review_id
        })
    
    async def _load_course(self):
        """Load the SCORM course in the browser."""
        launch_file = self.extract_path / self.manifest.launch_file
        
        if not launch_file.exists():
            raise FileNotFoundError(f"Launch file not found: {launch_file}")
        
        success = await self.browser.navigate_to_file(launch_file)
        
        if not success:
            raise RuntimeError("Failed to load course in browser")
        
        # Wait for course to initialize
        await self.browser.wait_for_stable()
        await asyncio.sleep(settings.slide_wait_time)
        
        # Verify SCORM initialized
        scorm_data = await self.browser.get_scorm_data()
        if not scorm_data.get('initialized'):
            # Some courses take time to initialize
            await asyncio.sleep(2.0)
    
    async def _review_slides(self):
        """Review all slides in the course."""
        self.progress.status = ReviewStatus.REVIEWING
        
        previous_content = ""
        
        while self.current_slide < settings.max_slides:
            self.current_slide += 1
            self.progress.current_slide = self.current_slide
            
            # Review current slide
            slide_result = await self._review_current_slide()
            self.slides.append(slide_result)
            
            # Update progress
            self.progress.total_slides = self.current_slide
            self.progress.issues_found = sum(len(s.issues) for s in self.slides)
            
            # Check if course is complete
            if await self.functional_agent.is_course_complete():
                break
            
            # Try to navigate to next slide
            nav_success, nav_method = await self._navigate_next()
            
            if not nav_success:
                # We're stuck - try skip key
                self.stuck_count += 1
                
                if self.stuck_count >= self.max_stuck:
                    # Completely stuck, end review
                    slide_result.issues.append(Issue(
                        issue_type=IssueType.STUCK,
                        severity=IssueSeverity.CRITICAL,
                        message="Course navigation completely stuck - ending review",
                        slide_number=self.current_slide
                    ))
                    break
                
                # Try skip key
                skip_success = await self.functional_agent.use_skip_key(
                    settings.skip_key_combo
                )
                
                if skip_success:
                    slide_result.navigation_method = "skip"
                    slide_result.issues.append(Issue(
                        issue_type=IssueType.STUCK,
                        severity=IssueSeverity.WARNING,
                        message=f"Had to use skip key ({settings.skip_key_combo}) to proceed",
                        slide_number=self.current_slide
                    ))
                else:
                    # Skip didn't work either
                    slide_result.issues.append(Issue(
                        issue_type=IssueType.STUCK,
                        severity=IssueSeverity.ERROR,
                        message="Navigation stuck - skip key did not help",
                        slide_number=self.current_slide
                    ))
            else:
                slide_result.navigation_method = nav_method
                self.stuck_count = 0  # Reset stuck counter on successful navigation
            
            # Check for duplicate content (might indicate we're stuck in a loop)
            current_content = slide_result.text_content
            if current_content and current_content == previous_content:
                slide_result.issues.append(Issue(
                    issue_type=IssueType.NAVIGATION,
                    severity=IssueSeverity.WARNING,
                    message="Slide content identical to previous slide - possible navigation loop",
                    slide_number=self.current_slide
                ))
            previous_content = current_content
            
            # Small delay between slides
            await asyncio.sleep(settings.slide_wait_time)
    
    async def _review_current_slide(self) -> SlideResult:
        """
        Run all checks on the current slide.
        
        Returns:
            SlideResult with all findings
        """
        start_time = datetime.utcnow()
        
        # Get basic info
        title = await self.browser.get_page_title()
        url = await self.browser.get_current_url()
        text_content = await self.browser.get_page_text()
        
        # Take screenshot
        screenshot_path = await self.browser.take_screenshot(
            f"slide_{self.current_slide:04d}"
        )
        
        # Run functional checks
        functional_result = await self.functional_agent.check_slide(self.current_slide)
        
        # Run content checks
        content_result = await self.content_agent.check_slide(
            text_content, 
            self.current_slide
        )
        
        # Check SCORM errors
        scorm_issues = await self.functional_agent.check_scorm_errors(self.current_slide)
        
        # Get SCORM calls for this slide
        scorm_calls = await self.browser.get_scorm_calls()
        
        # Calculate load time
        load_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Combine all issues
        all_issues = (
            functional_result.issues + 
            content_result.issues + 
            scorm_issues
        )
        
        return SlideResult(
            slide_number=self.current_slide,
            title=title,
            url=url,
            screenshot_path=str(screenshot_path) if screenshot_path else None,
            text_content=text_content[:5000],  # Truncate long content
            issues=all_issues,
            scorm_calls=scorm_calls[-20:],  # Keep last 20 calls
            load_time_ms=load_time
        )
    
    async def _navigate_next(self) -> tuple[bool, str]:
        """
        Try to navigate to the next slide.
        
        Returns:
            Tuple of (success, method_used)
        """
        return await self.functional_agent.try_navigate_next()
    
    def _generate_report(self) -> ReviewReport:
        """Generate the final review report."""
        # Count issues by type and severity
        issues_by_type: dict[str, int] = {}
        issues_by_severity: dict[str, int] = {}
        total_issues = 0
        
        for slide in self.slides:
            for issue in slide.issues:
                total_issues += 1
                
                issue_type = issue.issue_type.value
                issues_by_type[issue_type] = issues_by_type.get(issue_type, 0) + 1
                
                severity = issue.severity.value
                issues_by_severity[severity] = issues_by_severity.get(severity, 0) + 1
        
        # Calculate duration
        duration = None
        if self.progress.started_at and self.progress.completed_at:
            duration = (
                self.progress.completed_at - self.progress.started_at
            ).total_seconds()
        
        # Generate summary
        summary = self._generate_summary(total_issues, issues_by_type, issues_by_severity)
        
        return ReviewReport(
            review_id=self.review_id,
            course_title=self.manifest.title,
            scorm_version=self.manifest.scorm_version,
            status=self.progress.status,
            total_slides=len(self.slides),
            total_issues=total_issues,
            issues_by_type=issues_by_type,
            issues_by_severity=issues_by_severity,
            slides=self.slides,
            started_at=self.progress.started_at,
            completed_at=self.progress.completed_at,
            duration_seconds=duration,
            summary=summary
        )
    
    def _generate_summary(
        self, 
        total_issues: int,
        issues_by_type: dict[str, int],
        issues_by_severity: dict[str, int]
    ) -> str:
        """Generate a human-readable summary."""
        lines = []
        
        lines.append(f"Reviewed {len(self.slides)} slides in course '{self.manifest.title}'")
        lines.append(f"Found {total_issues} total issues")
        
        if issues_by_severity:
            severity_parts = []
            for sev in ['critical', 'error', 'warning', 'info']:
                count = issues_by_severity.get(sev, 0)
                if count > 0:
                    severity_parts.append(f"{count} {sev}")
            if severity_parts:
                lines.append(f"Severity breakdown: {', '.join(severity_parts)}")
        
        if issues_by_type:
            type_parts = [f"{v} {k}" for k, v in sorted(
                issues_by_type.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:5]]
            if type_parts:
                lines.append(f"Top issue types: {', '.join(type_parts)}")
        
        # Key observations
        critical_count = issues_by_severity.get('critical', 0)
        error_count = issues_by_severity.get('error', 0)
        
        if critical_count > 0:
            lines.append(f"CRITICAL: {critical_count} critical issues require immediate attention")
        
        if issues_by_type.get('stuck', 0) > 0:
            lines.append("WARNING: Navigation issues detected - some slides required skip key")
        
        if issues_by_type.get('media', 0) > 0:
            lines.append(f"Media issues: {issues_by_type['media']} problems with audio/video elements")
        
        # AI-detected content quality issues
        ai_issue_types = ['clarity', 'accuracy', 'tone', 'consistency', 'readability', 'structure', 'engagement']
        ai_issues_count = sum(issues_by_type.get(t, 0) for t in ai_issue_types)
        if ai_issues_count > 0:
            lines.append(f"AI Analysis: {ai_issues_count} content quality issues detected")
            for issue_type in ai_issue_types:
                count = issues_by_type.get(issue_type, 0)
                if count > 0:
                    lines.append(f"  - {issue_type.title()}: {count}")
        
        return "\n".join(lines)
    
    async def _cleanup(self):
        """Clean up resources."""
        if self.content_agent:
            await self.content_agent.shutdown()
        
        if self.browser:
            await self.browser.stop()
