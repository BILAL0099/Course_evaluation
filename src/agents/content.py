"""
Content testing agent for SCORM courses.

Tests spelling and grammar using pyspellchecker and language-tool-python.
Integrates LangChain AI agents for advanced content analysis.
"""

import asyncio
import re
from typing import List, Set, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from spellchecker import SpellChecker
import language_tool_python

from src.schemas import (
    Issue,
    IssueType,
    IssueSeverity,
    ContentCheckResult,
    SlideAIAnalysis
)
from config import settings
from src.agents.ai_agents import AIAgentOrchestrator


class ContentAgent:
    """Agent for content quality testing of SCORM course slides."""
    
    def __init__(self):
        self._spell_checker: Optional[SpellChecker] = None
        self._grammar_tool: Optional[language_tool_python.LanguageTool] = None
        self._ai_orchestrator: Optional[AIAgentOrchestrator] = None
        self._executor = ThreadPoolExecutor(max_workers=2)
        
        # Words to ignore
        self._ignore_words: Set[str] = set(settings.ignore_words)
        self._custom_words: Set[str] = set()
        
        # Common technical/e-learning terms to ignore
        self._technical_terms = {
            'scorm', 'lms', 'xapi', 'aicc', 'cmi', 'api', 'url', 'urls',
            'html', 'css', 'javascript', 'js', 'json', 'xml',
            'elearning', 'e-learning', 'courseware', 'webinar',
            'pdf', 'ppt', 'doc', 'xlsx', 'mp4', 'mp3', 'jpg', 'png', 'gif',
            'login', 'logout', 'username', 'admin', 'config',
            'dropdown', 'checkbox', 'tooltip', 'popup', 'modal',
            'prev', 'btn', 'nav', 'href', 'src', 'img', 'div',
            'ok', 'etc', 'eg', 'ie', 'vs'
        }
        
        self._ignore_words.update(self._technical_terms)
        
        # Context for AI analysis
        self._course_context: Dict[str, Any] = {}
    
    async def initialize(self):
        """Initialize the spell checker, grammar tool, and AI agents."""
        loop = asyncio.get_event_loop()
        
        # Initialize spell checker
        self._spell_checker = SpellChecker()
        self._spell_checker.word_frequency.load_words(list(self._ignore_words))
        
        # Initialize grammar tool (can be slow on first run)
        try:
            self._grammar_tool = await loop.run_in_executor(
                self._executor,
                lambda: language_tool_python.LanguageTool('en-US')
            )
        except Exception as e:
            print(f"Warning: Could not initialize grammar tool: {e}")
            self._grammar_tool = None
        
        # Initialize AI agent orchestrator
        if settings.enable_ai_agents:
            self._ai_orchestrator = AIAgentOrchestrator()
            await self._ai_orchestrator.initialize()
    
    def set_course_context(self, context: Dict[str, Any]):
        """Set course context for AI analysis."""
        self._course_context = context
    
    async def check_slide(
        self, 
        text: str, 
        slide_number: int,
        include_ai_analysis: bool = True
    ) -> ContentCheckResult:
        """
        Run content checks on slide text.
        
        Args:
            text: Text content from the slide
            slide_number: Current slide number for issue reporting
            include_ai_analysis: Whether to run AI-powered analysis
            
        Returns:
            ContentCheckResult with all findings
        """
        result = ContentCheckResult(text_content=text)
        
        # Clean and prepare text
        cleaned_text = self._clean_text(text)
        words = self._extract_words(cleaned_text)
        result.word_count = len(words)
        
        if not words:
            return result
        
        # Run checks
        loop = asyncio.get_event_loop()
        
        # Spelling check
        spelling_task = loop.run_in_executor(
            self._executor,
            self._check_spelling,
            words,
            slide_number
        )
        
        # Grammar check (if available)
        grammar_task = None
        if self._grammar_tool and len(cleaned_text) > 10:
            grammar_task = loop.run_in_executor(
                self._executor,
                self._check_grammar,
                cleaned_text,
                slide_number
            )
        
        # AI analysis (if enabled and orchestrator is available)
        ai_task = None
        if (include_ai_analysis and 
            self._ai_orchestrator and 
            settings.enable_ai_agents and
            len(cleaned_text) > 50):  # Only analyze substantial content
            ai_task = self._ai_orchestrator.analyze_slide(
                cleaned_text,
                slide_number,
                self._course_context
            )
        
        # Gather results
        spelling_results = await spelling_task
        result.spelling_errors = spelling_results['errors']
        result.issues.extend(spelling_results['issues'])
        
        if grammar_task:
            grammar_results = await grammar_task
            result.grammar_errors = grammar_results['errors']
            result.issues.extend(grammar_results['issues'])
        
        # Add AI analysis results
        if ai_task:
            try:
                ai_results = await ai_task
                result.issues.extend(ai_results.all_issues)
            except Exception as e:
                print(f"AI analysis error: {e}")
        
        return result
    
    async def get_detailed_ai_analysis(
        self, 
        text: str, 
        slide_number: int
    ) -> Optional[SlideAIAnalysis]:
        """
        Get detailed AI analysis for a slide (for comprehensive reports).
        
        Args:
            text: Text content from the slide
            slide_number: Slide number for reporting
            
        Returns:
            SlideAIAnalysis with detailed findings from all AI agents
        """
        if not self._ai_orchestrator or not settings.enable_ai_agents:
            return None
        
        cleaned_text = self._clean_text(text)
        if len(cleaned_text) < 50:
            return None
            
        return await self._ai_orchestrator.analyze_slide(
            cleaned_text,
            slide_number,
            self._course_context
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean text for analysis."""
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'www\.\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Remove file paths
        text = re.sub(r'[A-Za-z]:\\[\w\\/]+', '', text)
        text = re.sub(r'/[\w/]+\.\w+', '', text)
        
        # Remove HTML entities
        text = re.sub(r'&\w+;', '', text)
        
        # Remove numbers with units
        text = re.sub(r'\d+\s*(px|em|rem|%|pt|cm|mm|in|vh|vw|ms|s|kb|mb|gb)', '', text, flags=re.IGNORECASE)
        
        # Remove standalone numbers
        text = re.sub(r'\b\d+\b', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_words(self, text: str) -> List[str]:
        """Extract words from text."""
        # Split on non-word characters
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Filter by minimum length
        words = [w for w in words if len(w) >= settings.min_word_length]
        
        return words
    
    def _check_spelling(self, words: List[str], slide_number: int) -> dict:
        """Check spelling of words."""
        result = {
            'errors': [],
            'issues': []
        }
        
        if not self._spell_checker:
            return result
        
        # Filter out ignored words
        words_to_check = [
            w for w in words 
            if w.lower() not in self._ignore_words 
            and w.lower() not in self._custom_words
        ]
        
        # Find misspelled words
        misspelled = self._spell_checker.unknown(words_to_check)
        
        for word in misspelled:
            # Get suggestions
            suggestions = list(self._spell_checker.candidates(word))[:5]
            
            error_info = {
                'word': word,
                'suggestions': suggestions
            }
            result['errors'].append(error_info)
            
            # Create issue
            message = f"Possible spelling error: '{word}'"
            if suggestions:
                message += f" (suggestions: {', '.join(suggestions[:3])})"
            
            result['issues'].append(Issue(
                issue_type=IssueType.SPELLING,
                severity=IssueSeverity.WARNING,
                message=message,
                slide_number=slide_number,
                details=error_info
            ))
        
        return result
    
    def _check_grammar(self, text: str, slide_number: int) -> dict:
        """Check grammar of text."""
        result = {
            'errors': [],
            'issues': []
        }
        
        if not self._grammar_tool:
            return result
        
        try:
            matches = self._grammar_tool.check(text)
            
            for match in matches:
                # Skip certain rule categories
                if match.ruleId in ['WHITESPACE_RULE', 'COMMA_PARENTHESIS_WHITESPACE']:
                    continue
                
                # Skip very minor issues
                if match.category == 'TYPOGRAPHY':
                    continue
                
                error_info = {
                    'message': match.message,
                    'context': match.context,
                    'offset': match.offset,
                    'length': match.errorLength,
                    'rule_id': match.ruleId,
                    'replacements': match.replacements[:5] if match.replacements else []
                }
                result['errors'].append(error_info)
                
                # Determine severity
                severity = IssueSeverity.WARNING
                if 'error' in match.category.lower():
                    severity = IssueSeverity.ERROR
                
                result['issues'].append(Issue(
                    issue_type=IssueType.GRAMMAR,
                    severity=severity,
                    message=match.message,
                    slide_number=slide_number,
                    details=error_info
                ))
        
        except Exception as e:
            print(f"Grammar check error: {e}")
        
        return result
    
    def add_custom_words(self, words: List[str]):
        """Add custom words to ignore list."""
        self._custom_words.update(w.lower() for w in words)
        if self._spell_checker:
            self._spell_checker.word_frequency.load_words(words)
    
    async def extract_glossary(self, text: str) -> List[str]:
        """
        Extract potential glossary/technical terms from text.
        
        These are capitalized words or words in quotes that might be
        course-specific terminology.
        """
        # Find capitalized words (potential proper nouns/terms)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        
        # Find quoted terms
        quoted = re.findall(r'["\']([^"\']+)["\']', text)
        
        # Find terms in bold (common in e-learning for definitions)
        # This would need HTML parsing in actual implementation
        
        terms = list(set(capitalized + quoted))
        return terms
    
    async def shutdown(self):
        """Clean up resources."""
        if self._grammar_tool:
            try:
                self._grammar_tool.close()
            except:
                pass
        
        if self._ai_orchestrator:
            await self._ai_orchestrator.shutdown()
        
        self._executor.shutdown(wait=False)
