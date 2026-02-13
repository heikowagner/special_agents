# Email Categorization & Newsletter Opt-Out App

An intelligent email management application that uses OpenAI's API to automatically categorize emails and opt-out from newsletters.

## Features

- **Email Scanning**: Connect to your email via IMAP and retrieve unread messages
- **AI Categorization**: Uses OpenAI API to categorize emails into:
  - Important
  - Invoice
  - Newsletter
  - Promotional
  - Spam
  - Social
  - Notification
  - Other

- **Automated Newsletter Opt-Out**: 
  - Detects newsletters
  - Finds unsubscribe links automatically
  - Uses web automation to opt-out from newsletters
  - Tracks opt-out history

- **Data Storage & Reporting**:
  - Saves categorization results
  - Generates statistics and reports
  - Maintains opt-out history

## Prerequisites

- Python 3.8+
- OpenAI API key
- IMAP-enabled email account (Gmail, Outlook, etc.)

## Setup Instructions

### 1. Clone/Create Project

```bash
cd /Users/heikowagner/special_agents
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Additionally, you'll need ChromeDriver for Selenium web automation. Install it via:

```bash
python -m pip install webdriver-manager
```

Or manually download from: https://chromedriver.chromium.org/

### 3. Configure Environment

Copy the example configuration:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Email Configuration
IMAP_SERVER=imap.gmail.com              # or imap.outlook.com, etc.
IMAP_PORT=993
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password        # Use app-specific password for Gmail

# OpenAI Configuration
OPENAI_API_KEY=sk-...your-api-key...

# App Configuration
PROCESS_UNREAD_ONLY=true
MAX_EMAILS_TO_PROCESS=50
ENABLE_AUTO_OPTOUT=true
```

### 4. Gmail Setup (if using Gmail)

For Gmail, you need an App Password:

1. Enable 2-Factor Authentication on your Google Account
2. Go to https://myaccount.google.com/apppasswords
3. Select "Mail" and "Windows Computer"
4. Copy the generated password to `.env`

## Usage

Run the application:

```bash
python main.py
```

The app will:
1. Connect to your email
2. Fetch unread emails
3. Categorize each email using OpenAI
4. Automatically opt-out from detected newsletters
5. Generate a report with statistics

## Output

Results are saved in the `data/` directory:

- `categorization_results.jsonl` - All categorization results (one JSON per line)
- `optout_history.jsonl` - History of opt-out attempts

A summary report is printed to console after processing completes.

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `IMAP_SERVER` | imap.gmail.com | IMAP server address |
| `IMAP_PORT` | 993 | IMAP port (SSL) |
| `EMAIL_ADDRESS` | - | Your email address |
| `EMAIL_PASSWORD` | - | Your app password |
| `OPENAI_API_KEY` | - | Your OpenAI API key |
| `PROCESS_UNREAD_ONLY` | true | Only process unread emails |
| `MAX_EMAILS_TO_PROCESS` | 50 | Max emails to process per run |
| `ENABLE_AUTO_OPTOUT` | true | Enable automatic newsletter opt-out |

## Architecture

### Modules

1. **email_scanner.py** - Connects to IMAP server and fetches emails
2. **email_categorizer.py** - Uses OpenAI API to categorize emails
3. **newsletter_optout.py** - Automates newsletter unsubscription
4. **data_storage.py** - Stores results and generates reports
5. **main.py** - Orchestrates the entire workflow

### Flow

```
Email Scanner → Fetch Emails
    ↓
Email Categorizer → Classify & Detect Newsletters
    ↓
Newsletter Opt-Out → Find & Click Unsubscribe Links
    ↓
Data Storage → Save Results & Generate Reports
```

## Troubleshooting

### Authentication Issues
- For Gmail: Use [App Password](https://myaccount.google.com/apppasswords), not your regular password
- For Outlook: Use your email password
- Check IMAP is enabled in your email settings

### OpenAI API Errors
- Verify your API key is correct
- Check you have sufficient credits/quota
- Monitor rate limits

### Newsletter Opt-Out Issues
- Some newsletters may not have unsubscribe links
- Manual intervention required for some services
- Check `data/optout_history.jsonl` for attempts and results

### Selenium/ChromeDriver Issues
```bash
# If ChromeDriver fails, reinstall:
pip install --upgrade webdriver-manager
```

## Cost Considerations

- **OpenAI API**: ~$0.001-0.003 per email depending on content length
- Processing 50 emails typically costs $0.05-0.15

## Safety Notes

- Store `.env` in `.gitignore` to protect credentials
- App passwords are safer than regular passwords
- The app only marks emails as read, doesn't delete them
- Opt-out attempts are logged in `optout_history.jsonl`

## Advanced Usage

### Custom Email Processing

Edit `main.py` to process specific folders:

```python
# In EmailScanner class, modify get_unread_emails():
self.mail.select('ARCHIVE')  # Select different folder
```

### Customize Categories

Edit the `CATEGORIES` list in `email_categorizer.py`:

```python
CATEGORIES = [
    "your_category_1",
    "your_category_2",
    # ...
]
```

### Adjust LLM Behavior

Modify the prompt in `email_categorizer.py` for different categorization logic.

## Future Enhancements

- [ ] Web dashboard for viewing results
- [ ] Scheduled email processing (cron/scheduler)
- [ ] Support for multiple email accounts
- [ ] Custom categorization rules
- [ ] Email archive/cleanup capabilities
- [ ] Webhook notifications
- [ ] Database backend instead of JSONL

## License

MIT

## Support

For issues or feature requests, check the logs and review `data/` directory contents.
