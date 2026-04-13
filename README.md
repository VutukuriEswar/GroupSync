## What is GroupSync?

GroupSync is an intelligent web application designed to end the "what should we do today?" debate. It transforms group planning into a seamless, data-driven experience where users can coordinate schedules, share preferences anonymously, and receive AI-curated recommendations that make everyone happy—not just the loudest voice in the room.

## Key Features

👥 **Dynamic Group Management**
- Create groups with specific dates, start times, and end times.
- **Lobby System:** Creators can see who has joined in real-time and proceed only when ready.
- **Invite Codes:** Easy sharing with no account requirements for guests.
- **Member Control:** Creators can remove members; members can quit groups; sessions can be restarted.

🤖 **Hybrid AI & RL Recommendations**
- **Contextual Thompson Sampling:** 22-dimensional feature vectors power a Multi-Armed Bandit that adapts to time-of-day, budget, weather, and group size.
- **Live Data Injection:** Fetches real venues from OpenStreetMap (Overpass API), Google Maps (Selenium), and BookMyShow (movie showtimes with exact timing locks).
- **100% Live Itineraries:** When live data is available, sample data is discarded entirely—every venue is real.
- **Adaptive Learning:** The RL model learns from group feedback and per-user preference memory across sessions.

🛡️ **Guardian AI System**
- **Semantic Adjuster:** Natural language requests like "add a movie" are parsed into structured category biases.
- **AI Critic:** A closed-loop auditor scores itineraries (0-10) and rejects "non-human-passable" plans, triggering automatic replanning with explicit fixes.
- **Energy Curve Planner:** Matches activities to natural human flow—low energy mornings, peak afternoons, wind-down evenings.
- **Breather Logic:** Prevents back-to-back high-intensity activities.
- **Strict Meal Windows:** Penalizes non-dining during core lunch (12:30-13:30) and dinner (19:50-21:00) hours.

📍 **Location Intelligence**
- **Fair Meeting Points:** Calculates the geographical centroid of all group members using spherical math.
- **Meeting Place Override:** Creators can specify an exact meeting location with coordinate geocoding via Nominatim.
- **Individual Location Capture:** Location is requested individually upon joining, ensuring privacy during setup.
- **Travel Time Estimation:** Real driving time calculations at 15 km/h urban speed with 5-min parking buffer.

🎬 **Real-Time Movie Integration**
- **BookMyShow Deep Scraping:** Extracts actual movie names, genres, ratings, theatre names, and exact showtimes.
- **Showtime Locking:** Itineraries snap to real movie slots—not arbitrary times.
- **Overpass Fallback:** Queries OSM for cinema nodes when web scraping is unavailable.

🎯 **20+ Activity Categories**
- **Dining:** Restaurants, Cafes, Street Food, Mandi, Biryani, Irani Cafés, Desserts (23 cuisine types)
- **Entertainment:** Arcades, Bowling, Go-Kart, Escape Rooms, Karaoke, Gaming Cafés, Trampoline Parks, Laser Tag, VR Hubs, Billiards, Rock Climbing
- **Outdoor:** Parks, Gardens, Trekking, Kayaking, Cycling, Paintball
- **Cultural:** Museums, Art Galleries, Theatre Plays
- **Movies:** Live showtimes with 2D/3D format detection

📝 **Comprehensive Preference Survey**
- **14+ Guest Questions:** Covers energy, budget (in ₹), travel radius, and entertainment types.
- **23+ Registered Questions:** Deep dives into diet, accessibility, competition levels, and learning styles.
- **Veto System:** Users can specify hard dislikes (genres, cuisines, categories) that are strictly excluded.
- **Dynamic Logic:** Questions adapt based on whether the user is a guest or logged in.

🧠 **User Preference Memory**
- **Cross-Session Learning:** Registered users accumulate liked/disliked categories over time.
- **Memory Bias:** Past preferences automatically boost or suppress categories in future plans.
- **Merged with AI Adjustments:** Memory acts as a soft prior that combines with real-time Guardian AI biases.

🌤️ **Weather-Aware Planning**
- **Open-Meteo Integration:** Real-time weather scores from WMO codes.
- **Automatic Deprioritization:** Outdoor activities are suppressed when weather score drops below 0.4.

🏖️ **Vacation Multi-Day Support**
- **Multi-Day Itineraries:** Specify vacation days and receive sequenced daily plans.
- **Exclusion Carryover:** Venues used on Day 1 won't repeat on Day 2.

👤 **Solo Mode**
- **Solo Scoring:** Each venue has a `solo_score` attribute (e.g., cafes: 0.95, escape rooms: 0.3).
- **Threshold Filtering:** Venues with solo score < 0.4 are blocked for solo users.

⚡ **Real-Time Constraints**
- **Date/Time Logic:** Automatically disables past time slots if the event is "Today".
- **Budget Logic:** Supports "Free (₹0)" up to "High (₹5000+)" per person in Rupees.
- **Strict Budget Enforcement:** 0% tolerance—plans never exceed the specified budget.

🔐 **Flexible Authentication**
- **Guest Mode:** Join and plan activities without logging in.
- **User Mode:** Save groups to your account, access history, and keep track of long-term preferences.
- **Privacy First:** Guests can participate fully without providing personal emails.

## Tech Stack

**Backend:**
- FastAPI (Python web framework)
- MongoDB with Motor for async database operations
- NumPy for statistical calculations (Thompson Sampling Bandit)
- Selenium + selenium-stealth for anti-detection web scraping
- webdriver-manager for automated ChromeDriver management
- OpenStreetMap Overpass API for live venue data (with mirror fallbacks)
- BookMyShow Scraper for real-time Indian movie showtimes
- Google Maps Scraper for POI discovery
- Open-Meteo API for weather scoring
- Nominatim for geocoding/reverse geocoding
- OpenRouter API (z-ai/glm-4.5-air:free) for natural language reasoning
- Haversine formula for geospatial distance calculation
- Beam Search algorithm for optimal itinerary construction
- httpx for async HTTP requests with retry logic

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
- Google Chrome (for Selenium web scraping)

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
- GET /api/users/me - Get current user profile
- PUT /api/users/me - Update user profile
- GET /api/groups/my - Fetch groups for logged-in user

**Group Management:**
- POST /api/groups - Create a new group (Set Date, Start/End Time, Budget)
- GET /api/groups/{id} - View group details
- PUT /api/groups/{id} - Update group constraints (creator only)
- DELETE /api/groups/{id} - Delete group (creator only)
- POST /api/groups/join/{code} - Join via invite code (Captures Location)
- POST /api/groups/{id}/location - Update member location
- GET /api/groups/{id}/members - View members with preference submission status
- POST /api/groups/{id}/start - Start preference collection (creator only)
- POST /api/groups/{id}/restart - Reset group to lobby state
- DELETE /api/groups/{id}/members/{member_id} - Remove member (creator only)
- POST /api/groups/{id}/quit - Leave group

**Preferences:**
- POST /api/preferences - Submit user/group preferences (Energy, Budget, Vetoes, etc.)

**Recommendations:**
- POST /api/recommendations - Generate AI-powered schedule
- GET /api/recommendations/{id} - Fetch generated recommendation
- GET /api/recommendations/{id}/diagnostics - View engine diagnostics (data source, weather, coverage %)
- POST /api/recommendations/replan - Adjust plan with natural language feedback

**Feedback:**
- POST /api/feedback - Submit post-event satisfaction (Trains RL Model + User Memory)

## Configuration Details

**MongoDB Setup:**
- Local: Install MongoDB Community Server.
- Cloud: Use MongoDB Atlas (free tier available).
- Database initializes automatically.
- Collections: `users`, `group_sessions`, `preferences`, `recommendations`, `feedback`, `rl_model_state`, `user_preference_memory`

**OpenRouter API:**
1. Sign up at openrouter.ai.
2. Get your API key.
3. Add to `.env` file as `OPENROUTER_API_KEY`.
4. Used for: itinerary summaries, reasoning generation, semantic adjustment parsing, AI critic auditing.

**Web Scraping (Optional - Graceful Fallback):**
- If Selenium/Chrome is not installed, the system falls back to Overpass API.
- If Overpass fails, it falls back to sample data.
- BookMyShow scraping requires Chrome and may hit rate limits—throttled automatically.

**RL Model:**
- The Thompson Sampling state (22-dim per arm × 6 categories) is stored in `rl_model_state`.
- Arms update on: user feedback (weighted 70% activity + 30% overall) and AI replan signals.
- Exploration factor is controlled per-group via preferences.

**Data Source Priority:**
1. BookMyShow Deep Scrape (movies with exact showtimes)
2. Overpass API (restaurants, parks, entertainment venues)
3. Google Maps Selenium Scrape (fallback POI discovery)
4. Sample Data (only when all live sources fail)

## License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

© 2026 Eswar Vutukuri, Kanneganti Lohitha, Meghana Panidapu, Yasasri Bandreddi

## Acknowledgments

Thanks to OpenRouter for providing accessible AI reasoning models, MongoDB for the database, FastAPI for the high-performance web framework, OpenStreetMap for open geospatial data, BookMyShow for movie data access, and the React community for the UI ecosystem. We thank you from the bottom of our hearts for helping us complete this project.