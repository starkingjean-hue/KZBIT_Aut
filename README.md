# KZBIT Automation System

Ultra-fast browser automation for time-sensitive BTC code submission on kzbit.com with Telegram control.
# KZBIT Ultra-Fast Automation 🚀

High-performance Telegram-controlled bot for BTC code submission on KZBIT.

## Features
- **Parallel Processing**: Up to 5 accounts concurrently.
- **Stealth Mode**: Advanced browser fingerprinting mitigation.
- **Real-time Feedback**: Detailed reporting via Telegram.
- **Crash Recovery**: Automatic browser cleanup and session management.

## Deployment Guide
1. **Clone & Install**:
   ```bash
   git clone https://github.com/starkingjean-hue/KZBIT_Aut.git
   pip install -r requirements.txt
   playwright install chromium
   ```
2. **Configure `.env`**:
   - `TELEGRAM_BOT_TOKEN`: Your bot token.
   - `HEADLESS=true`: For server performance.
3. **Run**:
   ```bash
   python main.py
   ```

## Commands
- `/code <N>f <CODE>`: Launch automation.
- `/status`: Check bot activity.
- `/add_c`: Add trade account.
- `/show`: List managed accounts.

---
*Locked for production stability.*

Edit `.env`:
```ini
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
```

### 3. Configure Accounts

Edit `accounts.json`:
```json
[
  {"email": "user1@example.com", "password": "pass1"},
  {"email": "user2@example.com", "password": "pass2"}
]
```

### 4. Run

```bash
python main.py
```

## 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/code <N> <CODE>` | Submit code N times on all accounts |
| `/status` | Check bot status |
| `/help` | Show help |

**Example:**
```
/code 2 j2f4ffjb
```

## 📁 Project Structure

```
KZBIT/
├── main.py              # Entry point
├── config.py            # Configuration & selectors
├── models.py            # Pydantic models (Data validation)
├── timing.py            # Deadline enforcement (Global & Account)
├── browser.py           # Playwright manager (Resource blocking)
├── popup_monitor.py     # Popup detection (MutationObserver)
├── automation.py        # Core workflow (Login, Nav, Submit)
├── account_manager.py   # Parallel execution controller
├── telegram_bot.py      # Telegram interface (python-telegram-bot)
├── screenshot.py        # Screenshot management
├── accounts.json        # Account credentials
├── .env                 # Environment variables
└── tests/               # Unit tests
```

## ⚡ Performance Optimizations

- **Headless Chromium** with optimized args
- **Resource blocking** (images, fonts, analytics)
- **Direct URL navigation** (bypass homepage)
- **Controlled parallelism** (semaphore-based)
- **Intelligent popup detection** (instant JS-based)

## 🧪 Testing

```bash
# Run unit tests
pytest tests/ -v
```

## 📊 Workflow Diagram

```
Telegram → Parser → Orchestrator → [Account 1] → Login → BTC Page → Submit ×N → Popup
                                 → [Account 2] → Login → BTC Page → Submit ×N → Popup
                                 → [Account 3] → ...
```

## 🔧 Configuration

All settings can be adjusted in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_CONCURRENT_ACCOUNTS` | 3 | Parallel accounts |
| `GLOBAL_TIMEOUT_SECONDS` | 600 | 10-minute deadline |
| `ACCOUNT_TIMEOUT_SECONDS` | 90 | Per-account limit |
| `SUBMIT_TIMEOUT_SECONDS` | 5 | Per-submit limit |
