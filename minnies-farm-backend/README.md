# 🌿 Minnie's Farm Resort — Flask Backend

A RESTful API built with **Flask + MySQL** powering the resort's room booking system.

---

## 📁 Project Structure

```
minnies-farm-backend/
├── app.py              ← App factory, extensions, blueprint registration
├── seed.py             ← Populate DB with sample data
├── requirements.txt    ← Python dependencies
├── .env.example        ← Copy this to .env and fill in your values
├── models/
│   └── __init__.py     ← All database models (User, Room, Booking, Service)
└── routes/
    ├── auth.py         ← /api/auth  (register, login, logout, me)
    ├── rooms.py        ← /api/rooms (CRUD + availability)
    ├── bookings.py     ← /api/bookings (CRUD + double-booking prevention)
    └── services.py     ← /api/services (entrance fee, karaoke, availing)
```

---

## ⚙️ Setup Instructions

### 1. Create & activate a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create your `.env` file
```bash
cp .env.example .env
```
Then open `.env` and fill in your MySQL credentials:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=minnies_farm_db
JWT_SECRET_KEY=some-random-secret-string
```

### 4. Create the MySQL database
Open MySQL Workbench or your terminal and run:
```sql
CREATE DATABASE minnies_farm_db;
```

### 5. Seed the database
```bash
python seed.py
```
This creates all tables and adds sample rooms, users, and services.

### 6. Run the server
```bash
python app.py
```
Server runs at: **http://localhost:5000**

Test it: open your browser and go to `http://localhost:5000/api/health`

---

## 🔑 Demo Accounts

| Role  | Email               | Password  |
|-------|---------------------|-----------|
| Staff | staff@resort.com    | staff123  |
| Guest | guest@resort.com    | guest123  |

---

## 📡 API Endpoints

### Auth  `/api/auth`
| Method | Endpoint      | Description              | Auth Required |
|--------|---------------|--------------------------|---------------|
| POST   | /register     | Create a new account     | No            |
| POST   | /login        | Login & get JWT token    | No            |
| POST   | /logout       | Invalidate token         | Yes           |
| GET    | /me           | Get current user info    | Yes           |

### Rooms  `/api/rooms`
| Method | Endpoint                  | Description                  | Auth Required  |
|--------|---------------------------|------------------------------|----------------|
| GET    | /                         | List all rooms (+ filters)   | No             |
| GET    | /:id                      | Get room details             | No             |
| POST   | /                         | Add new room                 | Staff only     |
| PUT    | /:id                      | Update room                  | Staff only     |
| DELETE | /:id                      | Delete room                  | Staff only     |
| POST   | /:id/availability         | Check date availability      | No             |

**Room filter query params:** `type`, `max_price`, `capacity`, `check_in`, `check_out`

Example: `GET /api/rooms?type=Suite&max_price=10000&check_in=2026-04-01&check_out=2026-04-05`

### Bookings  `/api/bookings`
| Method | Endpoint  | Description               | Auth Required   |
|--------|-----------|---------------------------|-----------------|
| GET    | /         | Get bookings              | Yes (own/all)   |
| GET    | /:id      | Get single booking        | Yes             |
| POST   | /         | Create booking            | Guest only      |
| PUT    | /:id      | Modify booking dates      | Guest (owner)   |
| DELETE | /:id      | Cancel booking            | Guest/Staff     |

**Create booking body:**
```json
{
  "room_id": 1,
  "check_in_date": "2026-04-01",
  "check_out_date": "2026-04-05",
  "num_guests": 2
}
```

### Services  `/api/services`
| Method | Endpoint         | Description              | Auth Required |
|--------|------------------|--------------------------|---------------|
| GET    | /                | List all services        | No            |
| GET    | /:id             | Get service details      | No            |
| POST   | /                | Create service           | Staff only    |
| PUT    | /:id             | Update service           | Staff only    |
| DELETE | /:id             | Deactivate service       | Staff only    |
| POST   | /:id/avail       | Avail a service          | Optional      |
| GET    | /avails          | View avail records       | Yes           |

---

## 🔒 How Authentication Works

1. Call `POST /api/auth/login` → you get a **JWT token**
2. For protected routes, send the token in the request header:
   ```
   Authorization: Bearer <your_token_here>
   ```
3. In Vue.js, store the token in a variable and attach it to every API call using `axios` or `fetch`.

---

## 🔗 Connecting to Vue.js Frontend

In your Vue frontend, replace the dummy data with real API calls like this:

```javascript
// Example: Login
const response = await fetch("http://localhost:5000/api/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "guest@resort.com", password: "guest123" })
});
const data = await response.json();
// data.token → save this!
// data.user  → currentUser

// Example: Get rooms
const rooms = await fetch("http://localhost:5000/api/rooms");
const data  = await rooms.json();
// data.rooms → your rooms array
```

---

## ⚠️ Double Booking Prevention

When a guest tries to book a room, the API checks for **overlapping bookings** using this logic:

```
existing.check_in  < new.check_out
AND
existing.check_out > new.check_in
```

If a conflict is found, the API returns `409 Conflict` and the booking is rejected.

---

*Built for Minnie's Farm Resort — Flask + Vue.js school project* 🌿
