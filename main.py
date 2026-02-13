"""
Email Categorization App
Main application that orchestrates email scanning, categorization, and newsletter opt-out
"""
import logging
import os
from dotenv import load_dotenv
from config_manager import ConfigManager
from email_scanner import EmailScanner
from email_categorizer import EmailCategorizer
from newsletter_optout import NewsletterOptOut
from data_storage import DataStorage
from llm_memory import LLMMemory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mapping of categories to folder names
CATEGORY_TO_FOLDER = {
    'important': 'Important',
    'invoice': 'Invoices',
    'newsletter': 'Newsletters',
    'promotional': 'Promotions',
    'spam': 'Spam',
    'social': 'Social',
    'notification': 'Notifications',
    'other': 'Other'
}


class EmailCategorizationApp:
    def __init__(self, config_file: str = "config.json"):
        """Initialize the email categorization app"""
        # Initialize configuration manager
        self.config_manager = ConfigManager(config_file=config_file)
        
        # Get configurations
        email_config = self.config_manager.get_email_config()
        llm_config = self.config_manager.get_llm_config()
        app_config = self.config_manager.get_app_config()
        
        # Initialize components
        self.scanner = EmailScanner(
            imap_server=email_config['imap_server'],
            imap_port=email_config['imap_port'],
            email_address=email_config['email_address'],
            password=email_config['password']
        )
        
        self.categorizer = EmailCategorizer(
            api_key=llm_config['api_key'],
            model=llm_config['model'],
            base_url=llm_config['url']  # Optional for local LLMs
        )
        
        self.optout_handler = NewsletterOptOut(
            headless=True, 
            openai_api_key=llm_config['api_key']
        )
        self.storage = DataStorage()
        self.memory = LLMMemory()
        
        # Configuration
        self.process_unread_only = app_config['process_unread_only']
        self.max_emails = app_config['max_emails']
        self.enable_auto_optout = app_config['enable_auto_optout']
        
        logger.info("Email Categorization App initialized successfully")
    
    def run(self):
        """Main application flow"""
        try:
            logger.info("Starting Email Categorization App")
            
            # Connect to email
            if not self.scanner.connect():
                logger.error("Failed to connect to email server")
                return
            
            try:
                # Fetch emails
                logger.info("Fetching emails...")
                if self.process_unread_only:
                    emails = self.scanner.get_unread_emails(max_count=self.max_emails)
                else:
                    emails = self.scanner.get_all_emails(max_count=self.max_emails)
                
                if not emails:
                    logger.info("No unread emails found")
                    return
                
                logger.info(f"Processing {len(emails)} emails...")
                
                # Categorize each email
                for email in emails:
                    # Categorize email
                    result = self.categorizer.categorize_email(email)
                    self.storage.save_categorization_result(result)
                    
                    # Move email to categorized folder
                    self._move_email_to_category_folder(email, result)
                    
                    # Handle newsletters
                    if result.get('is_newsletter') and self.enable_auto_optout:
                        logger.info(f"Newsletter detected: {result['subject']}")
                        self._handle_newsletter_optout(email, result)
                    
                    # Mark as read
                    self.scanner.mark_as_read(email['id'])
                
                # Print report
                logger.info("Categorization complete!")
                self.storage.print_report()
                self._print_folder_stats()
                self._print_memory_report()
                
            finally:
                self.scanner.disconnect()
        
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
    
    def _move_email_to_category_folder(self, email: dict, result: dict):
        """Move email to folder based on its category"""
        try:
            category = result.get('category', 'other')
            folder_name = CATEGORY_TO_FOLDER.get(category, 'Other')
            
            # Move email to category folder (remove from INBOX)
            success = self.scanner.copy_email_to_folder(
                email['id'], 
                folder_name, 
                keep_in_inbox=False
            )
            
            if success:
                logger.info(f"Email '{email['subject'][:50]}' moved to {folder_name}")
            else:
                logger.warning(f"Failed to move email to {folder_name}")
        
        except Exception as e:
            logger.error(f"Error moving email to category folder: {e}")
    
    def _handle_newsletter_optout(self, email: dict, categorization_result: dict):
        """Handle newsletter opt-out"""
        try:
            # Try to find unsubscribe link
            unsubscribe_url = self.scanner.get_unsubscribe_link(email['full_message'])
            
            if not unsubscribe_url:
                # Try to find it in email body
                unsubscribe_url = self.optout_handler.find_unsubscribe_link(
                    email['body'],
                    {k: str(v) for k, v in email['full_message'].items()}
                )
            
            if unsubscribe_url:
                logger.info(f"Found unsubscribe link: {unsubscribe_url}")
                success, message = self.optout_handler.opt_out_from_newsletter(
                    unsubscribe_url,
                    email['subject']
                )
                
                self.storage.save_optout_attempt(
                    email_id=email['id_str'],
                    subject=email['subject'],
                    url=unsubscribe_url,
                    success=success,
                    message=message
                )
                
                logger.info(f"Opt-out result: {message}")
            else:
                logger.warning(f"No unsubscribe link found for: {email['subject']}")
        
        except Exception as e:
            logger.error(f"Error handling newsletter opt-out: {e}", exc_info=True)
    
    def _print_folder_stats(self):
        """Print categorized folder statistics"""
        try:
            print("\n" + "="*50)
            print("CATEGORIZED FOLDERS")
            print("="*50)
            for category, folder_name in sorted(CATEGORY_TO_FOLDER.items()):
                count = self.scanner.get_folder_email_count(folder_name)
                print(f"  {folder_name}: {count} emails")
            print("="*50 + "\n")
        except Exception as e:
            logger.error(f"Failed to print folder stats: {e}")
    
    def _print_memory_report(self):
        """Print LLM memory statistics"""
        try:
            memory_stats = self.memory.context
            print("\n" + "="*50)
            print("LLM MEMORY STATISTICS")
            print("="*50)
            print(f"Total emails processed: {memory_stats.get('total_emails_processed', 0)}")
            print(f"Newsletters identified: {memory_stats.get('total_newsletters_identified', 0)}")
            print("\nCategories learned:")
            for category, count in sorted(memory_stats.get('categories_learned', {}).items()):
                print(f"  {category}: {count}")
            print("="*50 + "\n")
        except Exception as e:
            logger.error(f"Failed to print memory report: {e}")


def main():
    """Entry point"""
    app = EmailCategorizationApp()
    app.run()


if __name__ == "__main__":
    main()
