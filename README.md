# 🚚 AI WhatsApp Logistics System

A production-ready, AI-powered logistics dispatcher that runs entirely over **WhatsApp** using **Twilio**. Users can book cabs, schedule cargo deliveries, and track drivers in real-time — all through natural conversation.

🌐 **Live Dashboard:** [https://frontend-iota-eight-34.vercel.app](https://frontend-iota-eight-34.vercel.app)

Built with **FastAPI**, **PostgreSQL**, **Redis**, and a custom **regex-based NLP engine** — no paid OpenAI/LLM APIs required.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Quick Start](#-quick-start)
- [Environment Variables](#-environment-variables)
- [API Endpoints](#-api-endpoints)
- [WhatsApp Testing](#-whatsapp-testing-twilio-sandbox)
- [How It Works](#-how-it-works)
- [Cloud Deployment (Render)](#-cloud-deployment-render)
- [Tech Stack](#-tech-stack)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🚕 **Cab Booking** | Book passenger rides via WhatsApp with real-time pricing |
| 📦 **Cargo Delivery** | Schedule freight shipments with weight-based pricing |
| 🔐 **OTP Verification** | Secure booking completion with OTP verification (in-chat fallback for Sandbox) |
| 📍 **Smart Location Parsing** | Robust location extraction handling Google Maps JS redirects, protobuffers, text addresses, and pins |
| 🤖 **NLP Engine** | Rule-based intent classifier (no paid AI APIs needed) |
| 🗺️ **Live Driver Tracking** | Redis-powered driver location tracking with Maps links |
| 💰 **Distance-Based Pricing** | Haversine formula calculates real-world distances for accurate quotes |
| 🔁 **State Machine** | 8-state conversation flow with Redis persistence |
| 🛡️ **Idempotency** | Duplicate message detection prevents double-bookings |
| 👤 **Remote Booking** | Book rides for others with passenger phone validation |
| ⚖️ **Weight Verification** | Declared vs verified weight comparison with recalculation |

---

## 🏗️ Architecture

```
WhatsApp User
     │
     ▼
Twilio Sandbox (webhook)
     │
     ▼
┌─────────────────────────────┐
│   FastAPI Server             │
│                              │
│  ┌─────────┐  ┌───────────┐ │
│  │ Webhook  │─▶│ NLP Engine│ │
│  │ Router   │  │ (Regex)   │ │
│  └────┬─────┘  └─────┬─────┘ │
│       │               │       │
│  ┌────▼───────────────▼────┐ │
│  │   Conversation Agent     │ │
│  │   (State Machine)        │ │
│  └────┬──────────┬─────────┘ │
│       │          │            │
│  ┌────▼────┐ ┌──▼─────────┐ │
│  │ Location│ │  Booking    │ │
│  │ Resolver│ │  Service    │ │
│  └─────────┘ └────────────┘ │
└──────┬──────────────┬────────┘
       │              │
  ┌────▼────┐   ┌────▼──────┐
  │  Redis   │   │ PostgreSQL│
  │ (State)  │   │ (Bookings)│
  └──────────┘   └───────────┘
```

---

## 📁 Project Structure

```
AI_LOGISTICS/
├── app/
│   ├── main.py                  # FastAPI application entry point
│   ├── config/
│   │   └── settings.py          # Pydantic settings (env variables)
│   ├── api/
│   │   └── routes/
│   │       ├── webhook.py       # Twilio WhatsApp webhook handler
│   │       ├── driver.py        # Driver management endpoints
│   │       └── admin.py         # Admin dashboard API
│   ├── ai/
│   │   ├── agent.py             # Main conversation agent (state machine)
│   │   ├── nlp_engine.py        # Regex-based intent classifier
│   │   ├── state_machine.py     # Redis-backed state management
│   │   └── chat_formatter.py    # Response formatting middleware
│   ├── services/
│   │   ├── location_resolver.py # Google Maps, coordinates, geocoding
│   │   ├── booking_service.py   # Booking CRUD operations
│   │   ├── driver_service.py    # Driver assignment logic
│   │   ├── pricing_service.py   # Haversine distance + pricing
│   │   └── tracking_service.py  # Real-time driver tracking
│   ├── models/
│   │   ├── booking.py           # SQLAlchemy booking model
│   │   └── driver.py            # SQLAlchemy driver model
│   ├── db/
│   │   ├── base.py              # SQLAlchemy base
│   │   └── session.py           # Async database session
│   ├── utils/
│   │   └── chat_formatter.py    # AI response formatting
│   └── workers/
│       └── tasks.py             # Celery background tasks
├── frontend/                    # React admin dashboard
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Python container build
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
├── .gitignore
└── README.md
```

---

## 🔧 Prerequisites

- **Docker & Docker Compose** (recommended)
- **Python 3.11+** (if running without Docker)
- **Twilio Account** ([sign up free](https://www.twilio.com/try-twilio))
- **ngrok** (for local webhook tunneling)

---

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Dheeraj-reddy-palle/AI-Logistics-WhatsApp.git
cd AI-Logistics-WhatsApp
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This spins up:
- **app** — FastAPI server on port `8000`
- **db** — PostgreSQL on port `5432`
- **redis** — Redis on port `6379`

### 4. Verify It's Running

```bash
curl http://localhost:8000/health
# → {"status":"ok","app":"Logistics AI Agent","version":"2.0.0"}
```

### 5. Expose via ngrok (for WhatsApp)

```bash
ngrok http 8000
```

Copy the `https://...ngrok-free.dev` URL for the Twilio webhook configuration.

---

## 🔐 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `REDIS_URL` | ✅ | Redis connection string |
| `TWILIO_ACCOUNT_SID` | ✅ | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | ✅ | Twilio Auth Token |
| `TWILIO_WHATSAPP_NUMBER` | ✅ | Twilio Sandbox number (default: `+14155238886`) |
| `ENV` | ❌ | `dev` or `production` (default: `dev`) |
| `AI_PROVIDER` | ❌ | `disabled`, `ollama`, or `huggingface` (default: `disabled`) |
| `OLLAMA_BASE_URL` | ❌ | Ollama server URL (default: `http://localhost:11434`) |

---

## 📡 API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health probe (returns `"API running"`) |
| `GET` | `/health` | Detailed health check |
| `POST` | `/api/v1/webhook` | Twilio WhatsApp webhook (TwiML) |
| `GET` | `/api/v1/webhook` | WhatsApp webhook verification |
| `POST` | `/api/v1/driver/{driver_id}/accept` | Driver accepts a booking |
| `POST` | `/api/v1/driver/{driver_id}/location` | Driver updates location |
| `GET` | `/api/v1/admin/bookings` | List all bookings |
| `GET` | `/api/v1/admin/drivers` | List all drivers |
| `GET` | `/api/v1/admin/state/{phone}` | Get user conversation state |

---

## 📱 WhatsApp Testing (Twilio Sandbox)

### Step 1: Join the Sandbox
1. Go to [Twilio Console → WhatsApp Sandbox](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
2. Send the join code (e.g., `join <keyword>`) to **+1 415 523 8886** on WhatsApp

### Step 2: Configure the Webhook
1. In the Sandbox Settings tab, set **"When a message comes in"** to:
   ```
   https://your-ngrok-url.ngrok-free.dev/api/v1/webhook
   ```
2. Set method to **POST**
3. Click **Save**

### Step 3: Start Chatting!

Try these messages:

| Message | What Happens |
|---|---|
| `Book a cab from RGIA to Kondapur` | Starts cab booking flow |
| `Send 200kg from Hyderabad to Secunderabad` | Starts cargo booking |
| `17.2403,78.4294` | Sends exact coordinates |
| *(Share a location pin)* | Auto-detects WhatsApp location |
| *(Paste Google Maps link)* | Extracts coordinates from link |
| `123456` | Example OTP code entered to verify a booking |
| `track` | Shows driver live location |
| `cancel` | Resets the conversation |

---

## ⚙️ How It Works

### Conversation Flow (State Machine)

```
idle → collecting_pickup → collecting_drop → collecting_weight → booking_confirmed
                                                    │
                                              (cab? skip weight)
                                                    │
                                              collecting_passenger (remote booking)
```

### Location Resolution Priority

1. **WhatsApp Location Pin** — Native `Latitude`/`Longitude` from Twilio
2. **Google Maps Short Link** — Expands `maps.app.goo.gl` via HTTP redirect and raw HTML/Protobuf parsing for robust link extraction
3. **Google Maps URL** — Parses `?q=`, `@lat,lng`, `/lat,lng` patterns
4. **Raw Coordinates** — Matches `17.24,78.43` format
5. **Known Locations DB** — Hardcoded places (RGIA, Kondapur, etc.)
6. **Nominatim Geocoding** — OpenStreetMap API for text addresses

### Pricing Formula

```
distance = haversine(pickup_lat, pickup_lng, drop_lat, drop_lng)

Cab:   ₹50 base + ₹12/km
Cargo: ₹100 base + ₹15/km + ₹2/kg
```

---

## ☁️ Cloud Deployment (Render)

### 1. Push to GitHub

```bash
git push origin main
```

### 2. Create Render Web Service

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port 10000`
- Add all environment variables from `.env.example`
- Add **PostgreSQL** and **Redis** as Render services

### 3. Update Twilio Webhook

Set the webhook URL to:
```
https://your-app.onrender.com/api/v1/webhook
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.11) |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 |
| Cache/State | Redis 7 |
| Messaging | Twilio WhatsApp Sandbox |
| Location | Nominatim (OpenStreetMap) + Google Maps URL parsing |
| NLP | Custom regex-based intent classifier |
| Containerization | Docker + Docker Compose |
| Frontend | React + Vite + TailwindCSS |

---

## 📄 License

This project is for educational and demonstration purposes.

---

Built with ❤️ by [Dheeraj Reddy Palle](https://github.com/Dheeraj-reddy-palle)
