"""
Email Scanner Module
Connects to IMAP server and retrieves emails
"""
import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailScanner:
    def __init__(self, imap_server: str, imap_port: int, email_address: str, password: str):
        """Initialize email scanner with IMAP credentials"""
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.email_address = email_address
        self.password = password
        self.mail = None
    
    def _get_full_folder_name(self, folder_name: str) -> str:
        """
        Get the full IMAP folder name with proper prefix for the server
        T-Online requires custom folders to be prefixed with 'INBOX.'
        
        Args:
            folder_name: Simple folder name (e.g., 'Promotions')
        
        Returns:
            Full folder name (e.g., 'INBOX.Promotions')
        """
        if folder_name == 'INBOX':
            return folder_name
        # Prefix with INBOX. for T-Online and Gmail
        if not folder_name.startswith('INBOX.'):
            return f'INBOX.{folder_name}'
        return folder_name
        
    def connect(self) -> bool:
        """Connect to IMAP server"""
        try:
            self.mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.mail.login(self.email_address, self.password)
            logger.info(f"Connected to {self.imap_server}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.mail:
            self.mail.close()
            self.mail.logout()
            logger.info("Disconnected from email server")
    
    def get_unread_emails(self, max_count: int = 50) -> List[Dict]:
        """Fetch unread emails from inbox"""
        try:
            self.mail.select('INBOX')
            _, message_numbers = self.mail.search(None, 'UNSEEN')
            email_ids = message_numbers[0].split()[-max_count:]
            
            emails = []
            for email_id in email_ids:
                email_dict = self._fetch_email(email_id)
                if email_dict:
                    emails.append(email_dict)
            
            logger.info(f"Retrieved {len(emails)} unread emails")
            return emails
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            return []
    
    def get_all_emails(self, max_count: int = 50) -> List[Dict]:
        """Fetch all emails (read and unread) from inbox"""
        try:
            self.mail.select('INBOX')
            _, message_numbers = self.mail.search(None, 'ALL')
            email_ids = message_numbers[0].split()[-max_count:]
            
            emails = []
            for email_id in email_ids:
                email_dict = self._fetch_email(email_id)
                if email_dict:
                    emails.append(email_dict)
            
            logger.info(f"Retrieved {len(emails)} emails (read and unread)")
            return emails
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            return []
    
    def _fetch_email(self, email_id: bytes) -> Optional[Dict]:
        """Fetch a single email and parse it"""
        try:
            _, msg_data = self.mail.fetch(email_id, '(RFC822)')
            email_body = msg_data[0][1]
            email_message = email.message_from_bytes(email_body)
            
            email_dict = {
                'id': email_id,  # Keep as bytes for IMAP operations
                'id_str': email_id.decode(),  # Store decoded version for logging/storage
                'from': self._decode_header(email_message.get('From', '')),
                'subject': self._decode_header(email_message.get('Subject', '')),
                'to': self._decode_header(email_message.get('To', '')),
                'date': email_message.get('Date', ''),
                'body': self._get_email_body(email_message),
                'full_message': email_message,
            }
            return email_dict
        except Exception as e:
            logger.error(f"Failed to fetch email {email_id}: {e}")
            return None
    
    def _decode_header(self, header: str) -> str:
        """Decode email header"""
        if not header:
            return ""
        decoded_parts = []
        for part, charset in decode_header(header):
            if isinstance(part, bytes):
                decoded_parts.append(part.decode(charset or 'utf-8', errors='ignore'))
            else:
                decoded_parts.append(str(part))
        return ''.join(decoded_parts)
    
    def _get_email_body(self, email_message) -> str:
        """Extract email body text"""
        body = ""
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        charset = part.get_content_charset() or 'utf-8'
                        body = part.get_payload(decode=True).decode(charset, errors='ignore')
                        break
                    elif content_type == "text/html":
                        charset = part.get_content_charset() or 'utf-8'
                        body = part.get_payload(decode=True).decode(charset, errors='ignore')
            else:
                charset = email_message.get_content_charset() or 'utf-8'
                body = email_message.get_payload(decode=True).decode(charset, errors='ignore')
        except Exception as e:
            logger.error(f"Failed to extract email body: {e}")
        
        return body[:1000]  # Limit to 1000 chars to save tokens
    
    def mark_as_read(self, email_id):
        """Mark email as read"""
        try:
            # Handle both bytes and string formats
            if isinstance(email_id, str):
                email_id_bytes = email_id.encode()
            else:
                email_id_bytes = email_id
            self.mail.store(email_id_bytes, '+FLAGS', '\\Seen')
        except Exception as e:
            logger.error(f"Failed to mark email as read: {e}")
    
    def get_unsubscribe_link(self, email_message) -> Optional[str]:
        """Extract unsubscribe link from email headers"""
        list_unsubscribe = email_message.get('List-Unsubscribe', '')
        if list_unsubscribe:
            # Extract URL from <URL> format
            import re
            url_match = re.search(r'<(https?://[^>]+)>', list_unsubscribe)
            if url_match:
                return url_match.group(1)
        return None

    def move_email_to_folder(self, email_id, folder_name: str) -> bool:
        """
        Move an email to a specific folder
        
        Args:
            email_id: ID of the email to move (bytes or string)
            folder_name: Name of the destination folder
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to bytes if needed
            email_id_bytes = email_id if isinstance(email_id, bytes) else email_id.encode()
            email_id_str = email_id_bytes.decode() if isinstance(email_id_bytes, bytes) else str(email_id_bytes)
            
            # Ensure we're in INBOX first
            self.mail.select('INBOX')
            
            # Ensure folder exists
            full_folder_name = self._get_full_folder_name(folder_name)
            self._ensure_folder_exists(full_folder_name)
            
            # Make sure we're back in INBOX before copying
            self.mail.select('INBOX')
            
            # Copy email to destination folder
            status, response = self.mail.copy(email_id_bytes, full_folder_name)
            if status != 'OK':
                logger.error(f"Failed to copy email {email_id_str} to {full_folder_name}: {response}")
                return False
            
            # Mark for deletion in current folder (move operation)
            self.mail.store(email_id_bytes, '+FLAGS', '\\Deleted')
            self.mail.expunge()
            
            logger.info(f"Moved email {email_id_str} to {full_folder_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move email {email_id}: {e}")
            return False
    
    def copy_email_to_folder(self, email_id, folder_name: str, keep_in_inbox: bool = True) -> bool:
        """
        Copy an email to a folder
        
        Args:
            email_id: ID of the email to copy (bytes or string)
            folder_name: Name of the destination folder
            keep_in_inbox: If True, keep email in INBOX; if False, remove from INBOX
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to bytes if needed
            email_id_bytes = email_id if isinstance(email_id, bytes) else email_id.encode()
            email_id_str = email_id_bytes.decode() if isinstance(email_id_bytes, bytes) else str(email_id_bytes)
            
            # Ensure we're in INBOX first
            self.mail.select('INBOX')
            
            # Get full folder name with proper prefix
            full_folder_name = self._get_full_folder_name(folder_name)
            
            # Ensure folder exists
            self._ensure_folder_exists(full_folder_name)
            
            # Make sure we're back in INBOX before copying
            self.mail.select('INBOX')
            
            # Copy email to destination folder
            status, response = self.mail.copy(email_id_bytes, full_folder_name)
            if status != 'OK':
                logger.error(f"Failed to copy email {email_id_str} to {full_folder_name}: {response}")
                return False
            
            # Optionally remove from INBOX
            if not keep_in_inbox:
                self.mail.store(email_id_bytes, '+FLAGS', '\\Deleted')
                self.mail.expunge()
            
            logger.info(f"Copied email {email_id_str} to {full_folder_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy email {email_id}: {e}")
            return False
    
    def _ensure_folder_exists(self, folder_name: str) -> bool:
        """
        Ensure a folder exists on the server, create if needed
        
        Args:
            folder_name: Full folder name (e.g., 'INBOX.Promotions')
        
        Returns:
            True if folder exists or was created, False otherwise
        """
        try:
            # Try to select the folder - if it exists, this will succeed
            status, _ = self.mail.select(folder_name, readonly=True)
            if status == 'OK':
                logger.debug(f"Folder {folder_name} exists")
                return True
            
            # Folder doesn't exist, try to create it
            status, response = self.mail.create(folder_name)
            if status == 'OK':
                logger.info(f"Created folder: {folder_name}")
                return True
            else:
                logger.warning(f"Failed to create folder {folder_name}: {response}")
                return False
                
        except Exception as e:
            logger.debug(f"Folder check failed, attempting create: {e}")
            try:
                status, response = self.mail.create(folder_name)
                if status == 'OK':
                    logger.info(f"Created folder: {folder_name}")
                    return True
                else:
                    logger.debug(f"Folder {folder_name} may already exist")
                    return True
            except Exception as create_error:
                logger.error(f"Error ensuring folder {folder_name} exists: {create_error}")
                return False
    
    def get_folder_email_count(self, folder_name: str) -> int:
        """
        Get the number of emails in a folder
        
        Args:
            folder_name: Name of the folder
        
        Returns:
            Number of emails in the folder
        """
        try:
            full_folder_name = self._get_full_folder_name(folder_name)
            status, _ = self.mail.select(full_folder_name)
            
            # If folder selection failed, return 0
            if status != 'OK':
                logger.warning(f"Failed to select folder {full_folder_name}")
                return 0
            
            _, message_numbers = self.mail.search(None, 'ALL')
            count = len(message_numbers[0].split()) if message_numbers[0] else 0
            return count
        except Exception as e:
            logger.error(f"Failed to get email count for {folder_name}: {e}")
            return 0
        finally:
            # Always return to INBOX to keep connection in valid state
            try:
                self.mail.select('INBOX')
            except Exception as e:
                logger.warning(f"Failed to return to INBOX: {e}")
