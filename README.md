# Wood Coffee

A Telegram bot for placing pre-orders at **Wood Coffee**. Customers can choose drinks or desserts, add items to a cart, select an arrival time, and notify staff about a new order.

## Features

- Choose coffee, tea, milk drinks, and desserts.
- Select a drink size with automatic price calculation.
- Add items to a cart and calculate the total.
- Complete a test checkout.
- Choose an arrival time of 5, 10, or 15 minutes.
- Send new-order notifications to staff in Telegram.

## Technologies

- Python 3
- [aiogram 2.25.1](https://docs.aiogram.dev/en/v2.25.1/)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
- SQLite (`coffee.db`)

## Installation and startup

1. Clone the repository and open its directory:

   ```bash
   git clone https://github.com/Dima1006/Wood-Coffee---project.git
   cd Wood-Coffee---project
   ```

2. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

   On Windows:

   ```powershell
   venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create your local configuration file from the safe template:

   ```bash
   cp .env.example .env
   ```

   Open `.env` and set:

   - `BOT_TOKEN` — the bot token obtained from [@BotFather](https://t.me/BotFather);
   - `STAFF_IDS` — a comma-separated list of Telegram IDs that should receive orders, for example `123456789,987654321`.

5. Start the bot:

   ```bash
   python bot.py
   ```

After startup, open a chat with the bot in Telegram and send the `/start` command.

## Project structure

| File | Purpose |
| --- | --- |
| `bot.py` | Command handlers, menu, and checkout flow. |
| `menu.py` | Product list, sizes, and prices. |
| `cart.py` | Temporary in-memory storage for user carts. |
| `states.py` | Conversation states for the bot. |
| `keyboards.py` | Inline keyboard for confirming an item addition. |
| `db.py` | SQLite cart-table setup. |
| `config.py` | Environment-based token and staff-ID configuration. |
| `.env.example` | Safe template for local environment variables. |

## Menu configuration

The products and prices are defined in `menu.py`. To add or update an item, edit the appropriate dictionary: `COFFEE`, `TEA`, `MILK_DRINK`, or `DESSERTS`.

## Security

Never commit a real Telegram bot token. The `.env` file is ignored by Git, while `.env.example` contains only safe placeholders. If a token has ever been published, revoke it through @BotFather and create a new one before using the bot again.
