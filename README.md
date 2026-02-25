## What is GroupSync?

GroupSync is an intelligent web application designed to end the "what should we do today?" debate. It transforms group planning into a seamless, data-driven experience where users can coordinate schedules, share preferences anonymously, and receive AI-curated recommendations that make everyone happy—not just the loudest voice in the room.

## Key Features

👥 **Dynamic Group Management**
- Create groups with specific dates, start times, and end times.
- **Lobby System:** Creators can see who has joined in real-time and proceed only when ready.
- **Invite Codes:** Easy sharing with no account requirements for guests.

🤖 **Hybrid AI & RL Recommendations**
- **Smart Scoring:** Combines Content-Based Filtering (Preferences), Collaborative Filtering (Bandit RL), and Geospatial Logic.
- **Live Data Injection:** Simulates fetching real-time events like "New Movies" and "Carnivals" near the group's centroid.
- **Adaptive Learning:** The Multi-Armed Bandit model learns from group feedback to improve future suggestions.

📍 **Location Intelligence**
- **Fair Meeting Points:** Calculates the geographical centroid of all group members.
- **Outlier Detection:** Identifies members far away and suggests central meeting spots.
- **Individual Location Capture:** Location is requested individually upon joining, ensuring privacy during setup.

📝 **Comprehensive Preference Survey**
- **14+ Guest Questions:** Covers energy, budget (in ₹), travel radius, and entertainment types.
- **23+ Registered Questions:** Deep dives into diet, accessibility, competition levels, and learning styles.
- **Dynamic Logic:** Questions adapt based on whether the user is a guest or logged in.

⚡ **Real-Time Constraints**
- **Date/Time Logic:** Automatically disables past time slots if the event is "Today".
- **Budget Logic:** Supports "Free (₹0)" up to "High (₹2000+)" in Rupees.

🔐 **Flexible Authentication**
- **Guest Mode:** Join and plan activities without logging in.
- **User Mode:** Save groups to your account, access history, and keep track of long-term preferences.
- **Privacy First:** Guests can participate fully without providing personal emails.

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- MongoDB with Motor for async database operations
- NumPy for statistical calculations (Bandit Algorithm)
- OpenRouter API (z-ai/glm-4.5-air:free) for natural language reasoning
- Haversine formula for geospatial distance calculation

**Frontend:**
- React for UI components
- Framer Motion for smooth animations
- Tailwind CSS & Shadcn UI for modern styling
- Axios for API communication
- Sonner for toast notifications

## Quick Start Guide

### Prerequisites
- Python 3.8+
- Node.js & npm/yarn
- MongoDB (local or cloud)
- OpenRouter API Key (for AI reasoning features)

### Installation Steps

1. **Clone the repository**

2. **Set up virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # On Linux: source venv/bin/activate
```

3. **Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

4. **Configure Environment**
Create a `.env` file in the backend folder using `.env.example`.

5. **Run backend server**
```bash
uvicorn server:app --reload
```

6. **Open a new terminal and install frontend dependencies**
```bash
cd frontend
yarn install
yarn start
```

## API Endpoints

**Authentication:**
- POST /api/auth/register - Create new account
- POST /api/auth/login - User login
- GET /api/groups/my - Fetch groups for logged-in user

**Group Management:**
- POST /api/groups - Create a new group (Set Date, Start/End Time, Budget)
- GET /api/groups/{id} - View group details
- POST /api/groups/join/{code} - Join via invite code (Captures Location)

**Preferences:**
- POST /api/preferences - Submit user/group preferences (Energy, Budget, etc.)

**Recommendations:**
- POST /api/recommendations - Generate AI-powered schedule
- POST /api/recommendations/replan - Adjust plan with specific feedback

**Feedback:**
- POST /api/feedback - Submit post-event satisfaction (Trains RL Model)

## Configuration Details

**MongoDB Setup:**
- Local: Install MongoDB Community Server.
- Cloud: Use MongoDB Atlas (free tier available).
- Database initializes automatically.

**OpenRouter API:**
1. Sign up at openrouter.ai.
2. Get your API key.
3. Add to `.env` file as `OPENROUTER_API_KEY`.
4. Used for generating human-readable reasoning behind AI choices.

**RL Model:**
- The Multi-Armed Bandit state is stored in the `rl_model_state` collection in MongoDB.
- It learns continuously as users submit feedback (1-5 stars).

## License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

© 2026 Eswar Vutukuri, Kanneganti Lohitha, Meghana Panidapu, Yasasri Bandreddi

## Acknowledgments

Thanks to OpenRouter for providing accessible AI reasoning models, MongoDB for the database, FastAPI for the high-performance web framework, and the React community for the UI ecosystem. We thank you from the bottom of our hearts for helping us complete this project.
