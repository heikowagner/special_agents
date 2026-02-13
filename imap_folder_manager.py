"""
IMAP Folder Manager Module
Handles creating folders and moving emails to categorized folders on the IMAP server
"""
import imaplib
import logging
from typing import Dict, Optional, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IMAPFolderManager:
    """Manages IMAP folders for email categorization"""
    
    # Default category to folder mapping
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
    
    def __init__(self, mail: imaplib.IMAP4_SSL):
        """
        Initialize folder manager with an existing IMAP connection
        
        Args:
            mail: Connected IMAP4_SSL instance
        """
        self.mail = mail
        self.existing_folders = self._get_existing_folders()
    
    def _get_existing_folders(self) -> List[str]:
        """Get list of existing folders on the server"""
        try:
            _, mailboxes = self.mail.list()
            folders = []
            for mailbox in mailboxes:
                # Extract folder name from mailbox response
                parts = mailbox.decode('utf-8').split('"')
                if len(parts) >= 3:
                    folder_name = parts[-1]
                else:
                    folder_name = mailbox.decode('utf-8').split()[-1]
                folders.append(folder_name)
            logger.debug(f"Found existing folders: {folders}")
            return folders
        except Exception as e:
            logger.error(f"Failed to get existing folders: {e}")
            return []
    
    def get_folder_for_category(self, category: str) -> str:
        """
        Get or create folder for a category
        
        Args:
            category: Email category
        
        Returns:
            Folder name for the category
        """
        folder_name = self.CATEGORY_TO_FOLDER.get(category, 'Other')
        
        # Check if folder exists, if not create it
        if folder_name not in self.existing_folders:
            self._create_folder(folder_name)
        
        return folder_name
    
    def _create_folder(self, folder_name: str) -> bool:
        """
        Create a new folder on the IMAP server
        
        Args:
            folder_name: Name of the folder to create
        
        Returns:
            True if successful, False otherwise
        """
        try:
            status, response = self.mail.create(folder_name)
            if status == 'OK':
                self.existing_folders.append(folder_name)
                logger.info(f"Created folder: {folder_name}")
                return True
            else:
                logger.warning(f"Failed to create folder {folder_name}: {response}")
                return False
        except Exception as e:
            # Folder might already exist
            if 'already exists' in str(e).lower() or 'exists' in str(e).lower():
                logger.info(f"Folder {folder_name} already exists")
                self.existing_folders.append(folder_name)
                return True
            logger.error(f"Error creating folder {folder_name}: {e}")
            return False
    
    def move_email(self, email_id: str, category: str) -> bool:
        """
        Move an email to the folder corresponding to its category
        
        Args:
            email_id: ID of the email to move
            category: Category to move the email to
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to string if needed
            email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
            
            folder_name = self.get_folder_for_category(category)
            
            # Copy email to destination folder
            status, response = self.mail.copy(email_id, folder_name)
            if status != 'OK':
                logger.error(f"Failed to copy email {email_id_str} to {folder_name}: {response}")
                return False
            
            # Mark for deletion in INBOX (move operation)
            self.mail.store(email_id, '+FLAGS', '\\Deleted')
            self.mail.expunge()
            
            logger.info(f"Moved email {email_id_str} to {folder_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move email {email_id}: {e}")
            return False
    
    def move_email_keep_inbox(self, email_id: str, category: str) -> bool:
        """
        Copy an email to a folder while keeping it in INBOX
        
        Args:
            email_id: ID of the email to copy
            category: Category folder to copy to
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to string if needed
            email_id_str = email_id.decode() if isinstance(email_id, bytes) else str(email_id)
            
            folder_name = self.get_folder_for_category(category)
            
            # Copy email to destination folder
            status, response = self.mail.copy(email_id, folder_name)
            if status != 'OK':
                logger.error(f"Failed to copy email {email_id_str} to {folder_name}: {response}")
                return False
            
            logger.info(f"Copied email {email_id_str} to {folder_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy email {email_id}: {e}")
            return False
    
    def get_folder_stats(self) -> Dict[str, int]:
        """
        Get email count for each categorized folder
        
        Returns:
            Dictionary with folder names and email counts
        """
        stats = {}
        try:
            for category, folder_name in self.CATEGORY_TO_FOLDER.items():
                if folder_name in self.existing_folders:
                    self.mail.select(folder_name)
                    _, message_numbers = self.mail.search(None, 'ALL')
                    email_ids = message_numbers[0].split()
                    stats[folder_name] = len(email_ids)
            
            # Return to INBOX
            self.mail.select('INBOX')
        except Exception as e:
            logger.error(f"Failed to get folder stats: {e}")
        
        return stats
    
    def print_folder_stats(self):
        """Print folder statistics"""
        stats = self.get_folder_stats()
        if not stats:
            print("No categorized folders found")
            return
        
        print("\n" + "="*50)
        print("FOLDER STATISTICS")
        print("="*50)
        for folder_name, count in sorted(stats.items()):
            print(f"  {folder_name}: {count} emails")
        print("="*50 + "\n")
