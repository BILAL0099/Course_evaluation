import asyncio
import json
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field

from config import settings
from src.schemas import (
    Issue,
    IssueType,
    IssueSeverity,
    AIAnalysisResult,
    SlideAIAnalysis
)


# ============================================================================
# Output Schemas for structured LLM responses
# ============================================================================

class ContentIssue(BaseModel):
    """Schema for a content issue found by AI."""
    issue_type: str = Field(description="Type of issue: clarity, accuracy, tone, consistency, readability, structure, engagement, accessibility")
    severity: str = Field(description="Severity: info, warning, error, critical")
    message: str = Field(description="Clear description of the issue")
    suggestion: str = Field(description="Specific suggestion to fix the issue")
    location: Optional[str] = Field(default=None, description="Specific text or location of the issue")


class AnalysisOutput(BaseModel):
    """Schema for AI analysis output."""
    score: int = Field(description="Score from 0-100, where 100 is perfect")
    summary: str = Field(description="Brief summary of the analysis")
    issues: List[ContentIssue] = Field(default_factory=list, description="List of issues found")
    suggestions: List[str] = Field(default_factory=list, description="General improvement suggestions")


# ============================================================================
# Base Agent Class
# ============================================================================

class BaseAIAgent(ABC):
    """Base class for AI content evaluation agents."""
    
    def __init__(self, llm=None):
        self.llm = llm or self._create_llm()
        self.parser = JsonOutputParser(pydantic_object=AnalysisOutput)
        self._tokens_used = 0
    
    def _create_llm(self):
        """Create the LLM based on configuration."""
        if settings.llm_provider == "openai" and settings.openai_api_key:
            return ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens
            )
        elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            return ChatAnthropic(
                model=settings.anthropic_model,
                api_key=settings.anthropic_api_key,
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens
            )
        else:
            # Return None if no API key configured
            return None
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Name of the agent."""
        pass
    
    @property
    @abstractmethod
    def analysis_type(self) -> str:
        """Type of analysis this agent performs."""
        pass
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for the agent."""
        pass
    
    @abstractmethod
    def get_analysis_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """Get the analysis prompt for the given text."""
        pass
    
    async def analyze(
        self, 
        text: str, 
        slide_number: int,
        context: Optional[Dict[str, Any]] = None
    ) -> AIAnalysisResult:
        """
        Analyze the given text content.
        
        Args:
            text: Text content to analyze
            slide_number: Slide number for issue reporting
            context: Additional context (course title, previous slides, etc.)
            
        Returns:
            AIAnalysisResult with findings
        """
        if not self.llm:
            return AIAnalysisResult(
                agent_name=self.agent_name,
                analysis_type=self.analysis_type,
                summary="AI analysis not available - no LLM configured"
            )
        
        if not text or len(text.strip()) < 10:
            return AIAnalysisResult(
                agent_name=self.agent_name,
                analysis_type=self.analysis_type,
                score=100,
                summary="No substantial text content to analyze"
            )
        
        context = context or {}
        
        try:
            # Create the prompt
            prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=self.get_analysis_prompt(text, context))
            ])
            
            # Create chain with JSON output
            chain = prompt | self.llm
            
            # Run analysis
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: chain.invoke({})
            )
            
            # Parse response
            raw_content = response.content
            
            # Try to extract JSON from response
            analysis_data = self._parse_response(raw_content)
            
            # Convert to issues
            issues = self._convert_to_issues(analysis_data.get('issues', []), slide_number)
            
            return AIAnalysisResult(
                agent_name=self.agent_name,
                analysis_type=self.analysis_type,
                score=analysis_data.get('score'),
                summary=analysis_data.get('summary', ''),
                issues=issues,
                suggestions=analysis_data.get('suggestions', []),
                raw_response=raw_content,
                tokens_used=self._tokens_used
            )
            
        except Exception as e:
            return AIAnalysisResult(
                agent_name=self.agent_name,
                analysis_type=self.analysis_type,
                summary=f"Analysis error: {str(e)}"
            )
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        # Try to find JSON in the response
        try:
            # First try direct parse
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code block
        import re
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Return empty structure if parsing fails
        return {
            'score': None,
            'summary': content[:500],
            'issues': [],
            'suggestions': []
        }
    
    def _convert_to_issues(self, raw_issues: List[Dict], slide_number: int) -> List[Issue]:
        """Convert raw issue dicts to Issue objects."""
        issues = []
        
        issue_type_map = {
            'clarity': IssueType.CLARITY,
            'accuracy': IssueType.ACCURACY,
            'tone': IssueType.TONE,
            'consistency': IssueType.CONSISTENCY,
            'readability': IssueType.READABILITY,
            'structure': IssueType.STRUCTURE,
            'engagement': IssueType.ENGAGEMENT,
            'accessibility': IssueType.ACCESSIBILITY,
            'spelling': IssueType.SPELLING,
            'grammar': IssueType.GRAMMAR,
        }
        
        severity_map = {
            'info': IssueSeverity.INFO,
            'warning': IssueSeverity.WARNING,
            'error': IssueSeverity.ERROR,
            'critical': IssueSeverity.CRITICAL,
        }
        
        for raw_issue in raw_issues:
            try:
                issue_type_str = raw_issue.get('issue_type', 'clarity').lower()
                severity_str = raw_issue.get('severity', 'warning').lower()
                
                issue = Issue(
                    issue_type=issue_type_map.get(issue_type_str, IssueType.CLARITY),
                    severity=severity_map.get(severity_str, IssueSeverity.WARNING),
                    message=raw_issue.get('message', 'Issue detected'),
                    slide_number=slide_number,
                    details={
                        'suggestion': raw_issue.get('suggestion', ''),
                        'location': raw_issue.get('location', ''),
                        'agent': self.agent_name
                    }
                )
                issues.append(issue)
            except Exception:
                continue
        
        return issues


# ============================================================================
# Specialized Agents
# ============================================================================

class ClarityAgent(BaseAIAgent):
    """Agent for analyzing content clarity and readability."""
    
    @property
    def agent_name(self) -> str:
        return "Clarity Agent"
    
    @property
    def analysis_type(self) -> str:
        return "clarity"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert in educational content clarity and readability analysis.
Your job is to evaluate e-learning course text for clarity, readability, and ease of understanding.

Analyze content for:
1. Sentence complexity - Are sentences too long or convoluted?
2. Vocabulary level - Is the language appropriate for the target audience?
3. Jargon usage - Is technical terminology explained?
4. Logical flow - Do ideas connect clearly?
5. Ambiguity - Are there unclear or ambiguous statements?

Always respond with valid JSON matching this structure:
{
    "score": <0-100>,
    "summary": "<brief summary>",
    "issues": [
        {
            "issue_type": "clarity|readability",
            "severity": "info|warning|error|critical",
            "message": "<issue description>",
            "suggestion": "<how to fix>",
            "location": "<specific text if applicable>"
        }
    ],
    "suggestions": ["<general improvement suggestions>"]
}"""
    
    def get_analysis_prompt(self, text: str, context: Dict[str, Any]) -> str:
        return f"""Analyze the following e-learning course content for clarity and readability:

---
{text[:3000]}
---

Consider:
- Is the content easy to understand?
- Are there complex sentences that should be simplified?
- Is jargon properly explained?
- Does the content flow logically?

Provide your analysis as JSON."""


class AccuracyAgent(BaseAIAgent):
    """Agent for checking factual accuracy and consistency."""
    
    @property
    def agent_name(self) -> str:
        return "Accuracy Agent"
    
    @property
    def analysis_type(self) -> str:
        return "accuracy"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert fact-checker and content accuracy reviewer for e-learning courses.
Your job is to identify potential factual issues, inconsistencies, and outdated information.

Analyze content for:
1. Internal consistency - Do statements contradict each other?
2. Factual claims - Are there claims that seem incorrect or need verification?
3. Outdated information - Does any information seem potentially outdated?
4. Logical errors - Are there reasoning or logic errors?
5. Missing context - Are important caveats or context missing?

Note: You cannot verify external facts, but you can flag claims that seem suspicious or need verification.

Always respond with valid JSON matching this structure:
{
    "score": <0-100>,
    "summary": "<brief summary>",
    "issues": [
        {
            "issue_type": "accuracy|consistency",
            "severity": "info|warning|error|critical",
            "message": "<issue description>",
            "suggestion": "<how to fix>",
            "location": "<specific text if applicable>"
        }
    ],
    "suggestions": ["<general improvement suggestions>"]
}"""
    
    def get_analysis_prompt(self, text: str, context: Dict[str, Any]) -> str:
        course_title = context.get('course_title', 'Unknown Course')
        return f"""Analyze the following e-learning content for accuracy and consistency.
Course: {course_title}

---
{text[:3000]}
---

Look for:
- Statements that might be factually incorrect
- Internal contradictions
- Information that might be outdated
- Logical errors or reasoning problems
- Claims that need sources or verification

Provide your analysis as JSON."""


class ToneAgent(BaseAIAgent):
    """Agent for analyzing tone and appropriateness."""
    
    @property
    def agent_name(self) -> str:
        return "Tone Agent"
    
    @property
    def analysis_type(self) -> str:
        return "tone"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert in professional communication and tone analysis for e-learning content.
Your job is to evaluate if the tone is appropriate for educational content.

Analyze content for:
1. Professional tone - Is the language professional and appropriate?
2. Inclusivity - Is the language inclusive and bias-free?
3. Engagement - Is the tone engaging without being unprofessional?
4. Consistency - Is the tone consistent throughout?
5. Audience appropriateness - Is the tone suitable for the target audience?

Always respond with valid JSON matching this structure:
{
    "score": <0-100>,
    "summary": "<brief summary>",
    "issues": [
        {
            "issue_type": "tone|engagement",
            "severity": "info|warning|error|critical",
            "message": "<issue description>",
            "suggestion": "<how to fix>",
            "location": "<specific text if applicable>"
        }
    ],
    "suggestions": ["<general improvement suggestions>"]
}"""
    
    def get_analysis_prompt(self, text: str, context: Dict[str, Any]) -> str:
        return f"""Analyze the following e-learning content for tone and appropriateness:

---
{text[:3000]}
---

Consider:
- Is the tone professional and suitable for learning?
- Is the language inclusive and free of bias?
- Is it engaging while remaining appropriate?
- Are there any tone inconsistencies?

Provide your analysis as JSON."""


class AccessibilityAgent(BaseAIAgent):
    """Agent for checking content accessibility."""
    
    @property
    def agent_name(self) -> str:
        return "Accessibility Agent"
    
    @property
    def analysis_type(self) -> str:
        return "accessibility"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert in digital accessibility and inclusive design for e-learning.
Your job is to evaluate text content for accessibility issues.

Analyze content for:
1. Plain language - Is content written in clear, simple language?
2. Acronyms - Are acronyms defined on first use?
3. Instructions clarity - Are instructions clear and unambiguous?
4. Color references - Does text rely on color alone to convey meaning?
5. Sensory language - Does text assume specific sensory abilities?
6. Reading level - Is the content accessible to readers with varying abilities?

Always respond with valid JSON matching this structure:
{
    "score": <0-100>,
    "summary": "<brief summary>",
    "issues": [
        {
            "issue_type": "accessibility",
            "severity": "info|warning|error|critical",
            "message": "<issue description>",
            "suggestion": "<how to fix>",
            "location": "<specific text if applicable>"
        }
    ],
    "suggestions": ["<general improvement suggestions>"]
}"""
    
    def get_analysis_prompt(self, text: str, context: Dict[str, Any]) -> str:
        return f"""Analyze the following e-learning content for accessibility:

---
{text[:3000]}
---

Check for:
- Use of plain, clear language
- Undefined acronyms or abbreviations
- Instructions that might be unclear
- References to color without text alternatives
- Assumptions about sensory abilities
- Content that might be difficult for users with cognitive disabilities

Provide your analysis as JSON."""


class StructureAgent(BaseAIAgent):
    """Agent for analyzing content structure and organization."""
    
    @property
    def agent_name(self) -> str:
        return "Structure Agent"
    
    @property
    def analysis_type(self) -> str:
        return "structure"
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert in instructional design and content structure for e-learning.
Your job is to evaluate how well the content is organized and structured.

Analyze content for:
1. Logical organization - Is information presented in a logical order?
2. Chunking - Is content properly broken into digestible chunks?
3. Headings/sections - Are topics clearly delineated?
4. Transitions - Are there smooth transitions between ideas?
5. Key points - Are main points clearly highlighted?
6. Information hierarchy - Is there a clear hierarchy of information?

Always respond with valid JSON matching this structure:
{
    "score": <0-100>,
    "summary": "<brief summary>",
    "issues": [
        {
            "issue_type": "structure",
            "severity": "info|warning|error|critical",
            "message": "<issue description>",
            "suggestion": "<how to fix>",
            "location": "<specific text if applicable>"
        }
    ],
    "suggestions": ["<general improvement suggestions>"]
}"""
    
    def get_analysis_prompt(self, text: str, context: Dict[str, Any]) -> str:
        return f"""Analyze the following e-learning content for structure and organization:

---
{text[:3000]}
---

Consider:
- Is the content logically organized?
- Are ideas presented in digestible chunks?
- Is there a clear information hierarchy?
- Are transitions between topics smooth?

Provide your analysis as JSON."""


# ============================================================================
# AI Agent Orchestrator
# ============================================================================

class AIAgentOrchestrator:
    """
    Orchestrates multiple AI agents for comprehensive content analysis.
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAIAgent] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize all enabled AI agents."""
        if self._initialized:
            return
        
        # Check if AI is enabled and configured
        if not settings.enable_ai_agents:
            return
        
        if not (settings.openai_api_key or settings.anthropic_api_key):
            print("Warning: AI agents enabled but no API key configured")
            return
        
        # Create shared LLM instance
        llm = self._create_llm()
        
        if not llm:
            return
        
        # Initialize enabled agents
        if settings.ai_clarity_check:
            self.agents['clarity'] = ClarityAgent(llm)
        
        if settings.ai_accuracy_check:
            self.agents['accuracy'] = AccuracyAgent(llm)
        
        if settings.ai_tone_check:
            self.agents['tone'] = ToneAgent(llm)
        
        if settings.ai_accessibility_check:
            self.agents['accessibility'] = AccessibilityAgent(llm)
        
        # Always include structure agent if AI is enabled
        self.agents['structure'] = StructureAgent(llm)
        
        self._initialized = True
        print(f"Initialized {len(self.agents)} AI agents: {list(self.agents.keys())}")
    
    def _create_llm(self):
        """Create the LLM based on configuration."""
        if settings.llm_provider == "openai" and settings.openai_api_key:
            return ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens
            )
        elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            return ChatAnthropic(
                model=settings.anthropic_model,
                api_key=settings.anthropic_api_key,
                temperature=settings.ai_temperature,
                max_tokens=settings.ai_max_tokens
            )
        return None
    
    async def analyze_slide(
        self,
        text: str,
        slide_number: int,
        context: Optional[Dict[str, Any]] = None
    ) -> SlideAIAnalysis:
        """
        Run all enabled AI agents on a slide's content.
        
        Args:
            text: Text content from the slide
            slide_number: Slide number for reporting
            context: Additional context
            
        Returns:
            SlideAIAnalysis with all agent results
        """
        result = SlideAIAnalysis(slide_number=slide_number)
        
        if not self.agents:
            result.overall_summary = "AI analysis not available"
            return result
        
        context = context or {}
        
        # Run all agents concurrently
        tasks = {
            name: agent.analyze(text, slide_number, context)
            for name, agent in self.agents.items()
        }
        
        # Gather results
        agent_results = {}
        for name, task in tasks.items():
            try:
                agent_results[name] = await task
            except Exception as e:
                agent_results[name] = AIAnalysisResult(
                    agent_name=name,
                    analysis_type=name,
                    summary=f"Error: {str(e)}"
                )
        
        # Assign results
        if 'clarity' in agent_results:
            result.clarity_analysis = agent_results['clarity']
        if 'accuracy' in agent_results:
            result.accuracy_analysis = agent_results['accuracy']
        if 'tone' in agent_results:
            result.tone_analysis = agent_results['tone']
        if 'accessibility' in agent_results:
            result.accessibility_analysis = agent_results['accessibility']
        
        # Collect all issues and suggestions
        all_issues = []
        all_suggestions = []
        scores = []
        
        for analysis in agent_results.values():
            all_issues.extend(analysis.issues)
            all_suggestions.extend(analysis.suggestions)
            if analysis.score is not None:
                scores.append(analysis.score)
        
        result.all_issues = all_issues
        result.all_suggestions = list(set(all_suggestions))  # Deduplicate
        
        # Calculate overall score
        if scores:
            result.overall_score = sum(scores) / len(scores)
        
        # Generate overall summary
        result.overall_summary = self._generate_summary(agent_results, all_issues)
        
        return result
    
    def _generate_summary(
        self, 
        results: Dict[str, AIAnalysisResult],
        issues: List[Issue]
    ) -> str:
        """Generate an overall summary from agent results."""
        parts = []
        
        for name, result in results.items():
            if result.score is not None:
                parts.append(f"{name.title()}: {result.score}/100")
        
        if issues:
            severity_counts = {}
            for issue in issues:
                sev = issue.severity.value
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            issue_parts = [f"{v} {k}" for k, v in severity_counts.items()]
            parts.append(f"Issues: {', '.join(issue_parts)}")
        
        return " | ".join(parts) if parts else "Analysis complete"
    
    async def shutdown(self):
        """Clean up resources."""
        self.agents.clear()
        self._initialized = False
