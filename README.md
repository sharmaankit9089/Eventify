# Eventify 🎉
**A Modern Event Management System**

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.0%2B-green)
![MySQL](https://img.shields.io/badge/Database-MySQL-orange)
![Tailwind](https://img.shields.io/badge/UI-TailwindCSS-06B6D4)

Eventify is a full-stack web application designed to streamline college event management. It offers role-based access for students to register for events and administrators to manage capacity and attendees in real-time.

---

## 🚀 Features

* **User Module:** Secure login, live event search (AJAX), capacity-based registration, and personal dashboard.
* **Admin Module:** Event CRUD operations, real-time attendee tracking, and capacity management.
* **Tech Stack:** Python (Flask), MySQL, Jinja2, Tailwind CSS, JavaScript.

---

## ⚙️ Quick Setup

1.  **Clone & Install**
    ```bash
    git clone https://github.com/sharmaankit9089/Eventify.git
    cd Eventify
    python -m venv venv
    # Windows: venv\Scripts\activate | Mac/Linux: source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Database**
    * Create a MySQL database named `eventify_db`.
    * Update `db.py` with your MySQL credentials.

3.  **Run**
    ```bash
    python app.py
    ```
    Access the app at `http://127.0.0.1:5000`

---

## 🔑 Admin Login
* **Username:** `admin`
* **Password:** `admin123` *(Ensure this user exists in your DB)*
