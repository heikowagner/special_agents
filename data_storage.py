"""
Data Storage Module
Stores categorization results and opt-out history
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataStorage:
    def __init__(self, data_dir: str = "data"):
        """Initialize data storage"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.results_file = self.data_dir / "categorization_results.jsonl"
        self.optout_file = self.data_dir / "optout_history.jsonl"
    
    def save_categorization_result(self, result: Dict):
        """Save email categorization result"""
        try:
            result['timestamp'] = datetime.now().isoformat()
            with open(self.results_file, 'a') as f:
                f.write(json.dumps(result) + '\n')
            logger.info(f"Saved categorization result for: {result.get('subject', 'Unknown')}")
        except Exception as e:
            logger.error(f"Failed to save categorization result: {e}")
    
    def save_optout_attempt(self, email_id: str, subject: str, url: str, success: bool, message: str):
        """Save newsletter opt-out attempt"""
        try:
            optout_record = {
                'email_id': email_id,
                'subject': subject,
                'url': url,
                'success': success,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            with open(self.optout_file, 'a') as f:
                f.write(json.dumps(optout_record) + '\n')
            logger.info(f"Saved opt-out attempt for: {subject}")
        except Exception as e:
            logger.error(f"Failed to save opt-out attempt: {e}")
    
    def load_categorization_results(self) -> List[Dict]:
        """Load all categorization results"""
        results = []
        try:
            if self.results_file.exists():
                with open(self.results_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            results.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to load results: {e}")
        return results
    
    def get_stats(self) -> Dict:
        """Get statistics from categorization results"""
        results = self.load_categorization_results()
        if not results:
            return {}
        
        stats = {
            'total': len(results),
            'by_category': {},
            'newsletters_found': 0
        }
        
        for result in results:
            category = result.get('category', 'unknown')
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            if result.get('is_newsletter'):
                stats['newsletters_found'] += 1
        
        return stats
    
    def print_report(self):
        """Print categorization report"""
        stats = self.get_stats()
        if not stats:
            print("No categorization results found.")
            return
        
        print("\n" + "="*50)
        print("EMAIL CATEGORIZATION REPORT")
        print("="*50)
        print(f"Total emails processed: {stats['total']}")
        print(f"Newsletters found: {stats['newsletters_found']}")
        print("\nBreakdown by category:")
        for category, count in sorted(stats['by_category'].items()):
            percentage = (count / stats['total']) * 100
            print(f"  {category}: {count} ({percentage:.1f}%)")
        print("="*50 + "\n")
