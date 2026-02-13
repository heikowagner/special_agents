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
                _, msg_data = self.mail.fetch(email_id, '(RFC822)')
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                email_dict = {
                    'id': email_id.decode(),
                    'from': self._decode_header(email_message.get('From', '')),
                    'subject': self._decode_header(email_message.get('Subject', '')),
                    'to': self._decode_header(email_message.get('To', '')),
                    'date': email_message.get('Date', ''),
                    'body': self._get_email_body(email_message),
                    'full_message': email_message,
                }
                emails.append(email_dict)
            
            logger.info(f"Retrieved {len(emails)} unread emails")
            return emails
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            return []
    
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
    
    def mark_as_read(self, email_id: str):
        """Mark email as read"""
        try:
            self.mail.store(email_id, '+FLAGS', '\\Seen')
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
