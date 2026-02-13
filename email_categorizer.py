"""
Email Categorizer Module
Uses OpenAI API to categorize emails with LLM memory for learning
"""
import logging
from typing import Dict, Optional
from openai import OpenAI
from llm_memory import LLMMemory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATEGORIES = [
    "important",
    "invoice", 
    "newsletter",
    "promotional",
    "spam",
    "social",
    "notification",
    "other"
]


class EmailCategorizer:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize email categorizer with OpenAI API key and LLM memory"""
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.memory = LLMMemory()
    
    def _build_memory_context(self, email: Dict) -> str:
        """Build context from LLM memory for better categorization"""
        context_parts = []
        
        # Get sender history
        sender_history = self.memory.get_sender_history(email['from'])
        if sender_history:
            context_parts.append(
                f"Sender history: Previously categorized as '{sender_history.get('category')}'. "
                f"Seen {sender_history.get('interaction_count', 0)} times. "
                f"Is newsletter: {sender_history.get('is_newsletter', False)}"
            )
        
        # Get relevant patterns
        memory_context = self.memory.get_memory_context()
        
        if memory_context.get('known_newsletters'):
            newsletter_names = list(memory_context['known_newsletters'].keys())
            context_parts.append(f"Known newsletters: {', '.join(newsletter_names[:5])}")
        
        if context_parts:
            return "\n".join(context_parts)
        return ""
    
    def categorize_email(self, email: Dict) -> Dict:
        """
        Categorize an email using LLM with memory context
        Returns dict with category, confidence, and is_newsletter flag
        """
        try:
            # Build memory context for better categorization
            memory_context = self._build_memory_context(email)
            
            memory_section = ""
            if memory_context:
                memory_section = f"\n\nMemory Context:\n{memory_context}"
            
            prompt = f"""
Analyze the following email and categorize it into one of these categories: {', '.join(CATEGORIES)}

Email Details:
From: {email['from']}
Subject: {email['subject']}
To: {email['to']}
Body (first 1000 chars): {email['body'][:500]}{memory_section}

Provide your response in this JSON format:
{{
    "category": "category_name",
    "confidence": 0.95,
    "is_newsletter": true/false,
    "reason": "brief explanation"
}}

Only respond with valid JSON, no additional text.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an email categorization assistant. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            result['email_id'] = email['id']
            result['subject'] = email['subject']
            result['from'] = email['from']
            
            logger.info(f"Categorized email: {email['subject']} -> {result['category']}")
            
            # Store information in memory for future use
            self._store_email_in_memory(email, result)
            self.memory.update_stats(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to categorize email: {e}")
            return {
                'email_id': email['id'],
                'subject': email['subject'],
                'from': email['from'],
                'category': 'other',
                'confidence': 0.0,
                'is_newsletter': False,
                'reason': f'Categorization failed: {str(e)}'
            }
    
    def _store_email_in_memory(self, email: Dict, result: Dict):
        """Store email information in memory for pattern learning"""
        try:
            # Store sender profile
            sender_history = self.memory.get_sender_history(email['from'])
            interaction_count = sender_history.get('interaction_count', 0) + 1 if sender_history else 1
            
            self.memory.store_sender_profile(
                email['from'],
                {
                    'category': result.get('category'),
                    'typical_content': email['subject'][:100],
                    'interaction_count': interaction_count,
                    'is_newsletter': result.get('is_newsletter', False),
                    'first_seen': sender_history.get('first_seen') if sender_history else None
                }
            )
            
            # Store pattern information
            self.memory.store_email_pattern({
                'sender': email['from'],
                'category': result.get('category'),
                'confidence': result.get('confidence'),
                'keywords': self._extract_keywords(email['subject'], email['body']),
                'reason': result.get('reason')
            })
            
            # If it's a newsletter, store newsletter info
            if result.get('is_newsletter'):
                self.memory.store_newsletter_info({
                    'name': email['subject'][:50],
                    'sender': email['from'],
                    'keywords': self._extract_keywords(email['subject'], email['body'])
                })
        except Exception as e:
            logger.error(f"Failed to store email in memory: {e}")
    
    def _extract_keywords(self, subject: str, body: str) -> list:
        """Extract potential keywords from subject and body"""
        # Simple keyword extraction - can be enhanced
        words = (subject + " " + body[:200]).lower().split()
        # Filter out common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'is', 'it', 'to', 'from', 'for', 'in', 'of', 'on', 'at', 'by'}
        keywords = [w.strip('.,!?;:') for w in words if w.lower() not in common_words and len(w) > 3]
        return list(set(keywords))[:10]  # Return unique keywords
    
    def batch_categorize(self, emails: list) -> list:
        """Categorize multiple emails"""
        results = []
        for email in emails:
            result = self.categorize_email(email)
            results.append(result)
        return results
    
    def get_memory_stats(self) -> Dict:
        """Get memory statistics"""
        return self.memory.context
