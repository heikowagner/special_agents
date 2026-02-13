"""
LLM Memory Module
Manages memory storage for LLM to retain useful information across sessions
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMMemory:
    """
    Stores useful information for the LLM including:
    - Email patterns and sender information
    - Newsletter identification patterns
    - Categorization history and patterns
    - Sender profiles and behaviors
    """
    
    def __init__(self, memory_dir: str = "data/llm_memory"):
        """Initialize LLM memory storage"""
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True, parents=True)
        
        self.patterns_file = self.memory_dir / "patterns.jsonl"
        self.senders_file = self.memory_dir / "senders.jsonl"
        self.newsletters_file = self.memory_dir / "newsletters.json"
        self.context_file = self.memory_dir / "context.json"
        
        self._load_or_init_context()
    
    def _load_or_init_context(self):
        """Load or initialize context data"""
        if self.context_file.exists():
            with open(self.context_file, 'r') as f:
                self.context = json.load(f)
        else:
            self.context = {
                'total_emails_processed': 0,
                'total_newsletters_identified': 0,
                'categories_learned': {},
                'last_updated': datetime.now().isoformat()
            }
            self._save_context()
    
    def _save_context(self):
        """Save context data to file"""
        self.context['last_updated'] = datetime.now().isoformat()
        with open(self.context_file, 'w') as f:
            json.dump(self.context, f, indent=2)
    
    def store_email_pattern(self, pattern_info: Dict):
        """
        Store email pattern information for future reference
        
        Args:
            pattern_info: Dict with keys like 'sender', 'category', 'keywords', 'patterns'
        """
        try:
            pattern_info['timestamp'] = datetime.now().isoformat()
            pattern_info['id'] = hashlib.md5(
                f"{pattern_info.get('sender', '')}_{pattern_info.get('category', '')}".encode()
            ).hexdigest()
            
            with open(self.patterns_file, 'a') as f:
                f.write(json.dumps(pattern_info) + '\n')
            
            logger.info(f"Stored pattern for sender: {pattern_info.get('sender', 'Unknown')}")
        except Exception as e:
            logger.error(f"Failed to store email pattern: {e}")
    
    def store_sender_profile(self, sender_email: str, sender_info: Dict):
        """
        Store sender profile information
        
        Args:
            sender_email: Email address of the sender
            sender_info: Dict with keys like 'name', 'category', 'typical_content', 'frequency'
        """
        try:
            profile = {
                'sender_email': sender_email,
                'first_seen': sender_info.get('first_seen', datetime.now().isoformat()),
                'last_seen': datetime.now().isoformat(),
                'category': sender_info.get('category'),
                'typical_content': sender_info.get('typical_content'),
                'frequency': sender_info.get('frequency', 'unknown'),
                'interaction_count': sender_info.get('interaction_count', 1),
                'is_newsletter': sender_info.get('is_newsletter', False)
            }
            
            # Update existing or add new
            self._update_or_append_jsonl(self.senders_file, profile, 'sender_email')
            logger.info(f"Stored profile for sender: {sender_email}")
        except Exception as e:
            logger.error(f"Failed to store sender profile: {e}")
    
    def store_newsletter_info(self, newsletter_info: Dict):
        """
        Store newsletter identification information
        
        Args:
            newsletter_info: Dict with keys like 'name', 'sender', 'unsubscribe_url', 'keywords'
        """
        try:
            newsletters = self._load_json_file(self.newsletters_file, {})
            
            name = newsletter_info.get('name', 'Unknown')
            newsletters[name] = {
                'sender': newsletter_info.get('sender'),
                'unsubscribe_url': newsletter_info.get('unsubscribe_url'),
                'keywords': newsletter_info.get('keywords', []),
                'description': newsletter_info.get('description'),
                'last_seen': datetime.now().isoformat(),
                'times_seen': newsletters.get(name, {}).get('times_seen', 0) + 1
            }
            
            with open(self.newsletters_file, 'w') as f:
                json.dump(newsletters, f, indent=2)
            
            logger.info(f"Stored newsletter info: {name}")
        except Exception as e:
            logger.error(f"Failed to store newsletter info: {e}")
    
    def get_sender_history(self, sender_email: str) -> Optional[Dict]:
        """Retrieve historical information about a sender"""
        try:
            if not self.senders_file.exists():
                return None
            
            with open(self.senders_file, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if data.get('sender_email') == sender_email:
                        return data
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve sender history: {e}")
            return None
    
    def get_patterns_for_category(self, category: str) -> List[Dict]:
        """Retrieve learned patterns for a specific category"""
        try:
            patterns = []
            if not self.patterns_file.exists():
                return patterns
            
            with open(self.patterns_file, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if data.get('category') == category:
                        patterns.append(data)
            return patterns
        except Exception as e:
            logger.error(f"Failed to retrieve patterns: {e}")
            return []
    
    def get_newsletter_keywords(self) -> Dict[str, List[str]]:
        """Get all known newsletter keywords for pattern matching"""
        try:
            newsletters = self._load_json_file(self.newsletters_file, {})
            keywords_map = {}
            for name, info in newsletters.items():
                keywords_map[name] = info.get('keywords', [])
            return keywords_map
        except Exception as e:
            logger.error(f"Failed to retrieve newsletter keywords: {e}")
            return {}
    
    def get_memory_context(self) -> Dict:
        """
        Get comprehensive memory context for use in LLM prompts
        
        Returns:
            Dict with patterns, sender info, newsletters, and context
        """
        try:
            memory_context = {
                'global_context': self.context,
                'known_newsletters': self._load_json_file(self.newsletters_file, {}),
                'sender_patterns': self._load_jsonl_file(self.senders_file),
                'email_patterns': self._load_jsonl_file(self.patterns_file),
                'timestamp': datetime.now().isoformat()
            }
            return memory_context
        except Exception as e:
            logger.error(f"Failed to get memory context: {e}")
            return {}
    
    def update_stats(self, categorization_result: Dict):
        """Update memory statistics based on categorization"""
        try:
            self.context['total_emails_processed'] += 1
            
            if categorization_result.get('is_newsletter'):
                self.context['total_newsletters_identified'] += 1
            
            category = categorization_result.get('category', 'other')
            self.context['categories_learned'][category] = \
                self.context['categories_learned'].get(category, 0) + 1
            
            self._save_context()
        except Exception as e:
            logger.error(f"Failed to update stats: {e}")
    
    def clear_old_memory(self, days: int = 90):
        """Clear memory entries older than specified days"""
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Clear old patterns
            self._filter_old_entries(self.patterns_file, cutoff_date)
            
            # Clear old sender data
            self._filter_old_entries(self.senders_file, cutoff_date)
            
            logger.info(f"Cleared memory entries older than {days} days")
        except Exception as e:
            logger.error(f"Failed to clear old memory: {e}")
    
    def _update_or_append_jsonl(self, filepath: Path, data: Dict, key_field: str):
        """Update existing JSONL entry or append new one"""
        entries = []
        key_value = data.get(key_field)
        found = False
        
        if filepath.exists():
            with open(filepath, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get(key_field) == key_value:
                        entries.append(data)
                        found = True
                    else:
                        entries.append(entry)
        
        if not found:
            entries.append(data)
        
        with open(filepath, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
    
    def _load_jsonl_file(self, filepath: Path) -> List[Dict]:
        """Load all entries from JSONL file"""
        entries = []
        if not filepath.exists():
            return entries
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to load JSONL file: {e}")
        
        return entries
    
    def _load_json_file(self, filepath: Path, default=None):
        """Load JSON file"""
        if not filepath.exists():
            return default if default is not None else {}
        
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON file: {e}")
            return default if default is not None else {}
    
    def _filter_old_entries(self, filepath: Path, cutoff_date):
        """Remove entries older than cutoff_date"""
        if not filepath.exists():
            return
        
        from datetime import datetime
        entries = []
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    timestamp_str = entry.get('timestamp')
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str)
                        if timestamp >= cutoff_date:
                            entries.append(entry)
            
            with open(filepath, 'w') as f:
                for entry in entries:
                    f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to filter old entries: {e}")
