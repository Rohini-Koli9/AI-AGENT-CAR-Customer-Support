# Car Warranty & CCP Support Agent

Car Warranty & CCP Support is a Streamlit-based AI assistant that helps vehicle owners manage warranties, file claims, and book service appointments. It combines a login/registration portal, AI-powered customer support, and automated notifications to deliver a dealership-style digital experience.

---

## Features

- **Customer Portal**
  - Email-based login/registration with `users.csv`
  - Streamlined dashboard (only the AI support page is active)

- **AI Support Chat**
  - Powered by Groq’s `openai/gpt-oss-20b` (configurable)
  - Uses embeddings ([data/vectors.json](cci:7://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/vectors.json:0:0-0:0)) for contextual answers
  - 16+ LangChain tools for warranty lookups, CCP claims, appointments, notifications

- **Warranty & CCP Workflows**
  - Claim filing with automated CSV updates and unique IDs
  - CCP coverage reference tables, warranty policy retrieval
  - Appointment booking with instructions and notifications

- **Multi-Channel Notifications**
  - Email confirmations (SMTP/Gmail out of the box)
  - SMS/WhatsApp hooks (Twilio) ready for future use

---

## UI Preview

![AI Customer Support Screenshot](Car-Warranty-System/assets/ai-customer-support.png)

> Save the screenshot above as `Car-Warranty-System/assets/ai-customer-support.png` (or adjust the path if you prefer a different location) so the image loads correctly when the README is viewed on GitHub.

---

## Project Structure

```
AI-AGENTS-Costumer-Support-demo/
├── main.py                        # Streamlit entry point (auth, navigation)
├── core.py                        # Warranty, CCP, claim, notification tools
├── appointment_tools.py           # Appointment scheduling utilities
├── notification_tools.py          # Email/SMS/WhatsApp notification helpers
├── conf.py                        # Embeddings, Groq LLM setup, vector retriever
├── requirements.txt               # Project dependencies
├── .env                           # Runtime configuration (not tracked)
├── .env.example                   # Template for credentials
└── Car-Warranty-System/
    ├── data/
    │   ├── users.csv              # Customers
    │   ├── claims.csv             # Warranty claims
    │   ├── warranty_policies.md   # Policy corpus for embeddings
    │   ├── vectors.json           # Cached embeddings
    │   ├── customer_vehicles.csv  # Vehicle inventory
    │   ├── warranties.csv         # Extended warranty records
    │   ├── service_centers.csv    # Service center directory
    │   └── ccp_packages.csv       # CCP package catalog
    ├── pages/
    │   └── customer_support.py    # Streamlit page loaded by main.py
    └── assets/                    # (Reserved for static assets)
```

---

## Prerequisites

- Python 3.10+
- Pip (inside the virtual environment)
- Groq API key (Dev or higher recommended)
- (Optional) Gmail account with App Password for SMTP

---

## Setup

1. **Clone the repo**

   ```powershell
   git clone <repo-url>
   cd AI-AGENTS-Costumer-Support-demo
   ```

2. **Create and activate a virtual environment**

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**

   ```powershell
   pip install -r requirements.txt
   ```

4. **Configure environment variables**

   Copy [.env.example](cci:7://file:///c:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/.env.example:0:0-0:0) to `.env` and populate:

   ```env
   # Groq
   GROQ_API_KEY=gsk_your_key_here

   # SMTP (Gmail example)
   SMTP_EMAIL=your_email@gmail.com
   SMTP_PASSWORD=your_16_char_app_password
   SMTP_SERVER=smtp.gmail.com
  SMTP_PORT=587
   ```

   > For Gmail: enable 2-Step Verification → App Passwords → “Mail” on “Other device” → paste 16-character password (no spaces).

5. **Launch Streamlit**

   ```powershell
   streamlit run main.py
   ```

6. **Login**

   - Use an email from `data/users.csv`, or register a new one from the UI.
   - After logging in you’ll land on the AI support page.

---

## How the AI Works

1. **Context retrieval**  
   [warranty_policies.md](cci:7://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/warranty_policies.md:0:0-0:0) is split into sections and converted to embeddings via HuggingFace (`jinaai/jina-embeddings-v2-base-en`). Cached in [data/vectors.json](cci:7://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/vectors.json:0:0-0:0).

2. **Tool-enabled conversation**  
   [core.py](cci:7://file:///c:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/core.py:0:0-0:0) exposes LangChain tools for claims, appointments, warranties, etc. The Groq LLM orchestrates these tools based on user messages.

3. **Claim filing flow**  
   - `file_ccp_claim` checks vehicle + CCP status.
   - Appends claim to [claims.csv](cci:7://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/claims.csv:0:0-0:0) with ID and reference (CCP000001…).
   - Sends confirmation email via [send_email_notification](cci:1://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/notification_tools.py:14:0-139:9) (real SMTP if configured).

4. **Notifications**  
   - Emails: immediate SMTP send. Falls back to mock message if credentials are missing.
   - SMS/WhatsApp: placeholders ready for Twilio integration.

---

## Data Files

- `users.csv` – registered customers
- [claims.csv](cci:7://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/claims.csv:0:0-0:0) – warranty claims
- `customer_vehicles.csv` – vehicle registry with CCP flags
- `warranties.csv` – extended/CCP warranties
- `service_centers.csv` – partner locations
- [ccp_packages.csv](cci:7://file:///c:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/ccp_packages.csv:0:0-0:0) – package descriptions
- [warranty_policies.md](cci:7://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/warranty_policies.md:0:0-0:0) / [vectors.json](cci:7://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/vectors.json:0:0-0:0) – knowledge base & embeddings

All CSVs use simple headers and can be edited for demos.

---

## Common Workflows

| Workflow                     | Code path                         | Output |
|-----------------------------|-----------------------------------|--------|
| Login/Register              | [main.py](cci:7://file:///c:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/main.py:0:0-0:0)                         | Updates `users.csv`, session state |
| Check warranty status       | `check_warranty_status` tool      | Looks up by vehicle registration |
| File CCP claim              | `file_ccp_claim` in [core.py](cci:7://file:///c:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/core.py:0:0-0:0)     | Adds entry to [claims.csv](cci:7://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/claims.csv:0:0-0:0), sends email |
| Book service appointment    | `book_service_appointment` tool   | Generates confirmation, email |
| Send QA responses           | AI chat via `customer_support.py` | Context-aware LLM replies |

---

## Testing

Manual testing is recommended:

1. Start Streamlit.
2. Register a test user.
3. Verify warranty/CCP lookup for a vehicle (e.g., `DL05YY5678`).
4. File a claim and watch the terminal for email success.
5. Check your email inbox/spam.
6. Book an appointment and confirm instructions display correctly.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| **`ModuleNotFoundError: streamlit`** | venv not activated or dependencies missing | Activate venv and run `pip install -r requirements.txt` |
| **`ModuleNotFoundError: langchain_groq`** | Groq integration missing | Ensure requirements installed |
| **Prompt tokens exceed limit (413)** | Large context sent to Groq | Switch to higher tier plan or reduce context |
| **Email reports “Mock delivery”** | SMTP env vars missing or invalid | Set `SMTP_EMAIL`, `SMTP_PASSWORD`, `SMTP_SERVER`, `SMTP_PORT`, restart app |
| **Google blocked sign-in** | App password or security alert pending | Approve in Gmail security portal and retry |
| **Vectors missing** | [vectors.json](cci:7://file:///C:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/Car-Warranty-System/data/vectors.json:0:0-0:0) deleted or invalid | On startup the system will regenerate embeddings (requires HuggingFace API key in [conf.py](cci:7://file:///c:/Users/rohini/OneDrive/Desktop/AI-AGENTS-Costumer-Support-demo/conf.py:0:0-0:0) if you change model) |

---

## Security Notes

- `.env` is gitignored; don’t commit secrets.
- Use App Passwords for Gmail; never store your actual password.
- Rotate API keys regularly.
- For production, enforce HTTPS and secure storage for user data.

---

## Roadmap Ideas

- Integrate real Twilio SMS/WhatsApp notifications.
- Add booking calendar integration.
- Deploy to Streamlit Cloud/Azure/GCP with secret management.
- Add automated tests for tools and data loaders.
- Extend knowledge base beyond warranties (service FAQs, recall information).

---

## Contributors

Built for demo purposes by Rohini Koli and enhanced with AI assistance.
