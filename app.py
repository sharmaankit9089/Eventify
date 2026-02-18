from flask import Flask, render_template, request, redirect, session
from db import get_db_connection
from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "eventify_secret_key_123"


# 1) FIRST PAGE: Role Select
@app.route("/")
def role_select():
    if session.get("admin_logged_in"):
        return redirect("/admin/dashboard")

    if session.get("user_logged_in"):
        return redirect("/events")

    return render_template("role_select.html")


# 2) USER AUTH
@app.route("/user/register", methods=["GET", "POST"])
def user_register():
    if session.get("user_logged_in"):
        return redirect("/events")

    error = ""
    success = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Validation
        if not name or not email or not password or not confirm_password:
            error = "All fields are required."

        elif password != confirm_password:
            error = "Passwords do not match."

        else:
            hashed_password = generate_password_hash(password)

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            try:
                cursor.execute("""
                    INSERT INTO users (name, email, password)
                    VALUES (%s, %s, %s)
                """, (name, email, hashed_password))

                conn.commit()
                success = "Account created successfully! Now login."

            except Exception:
                error = "Email already registered."

            cursor.close()
            conn.close()

    return render_template("user/register.html", error=error, success=success)



@app.route("/user/login", methods=["GET", "POST"])
def user_login():
    if session.get("user_logged_in"):
        return redirect("/events")

    error = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM users
            WHERE email = %s AND password = %s
        """, (email, password))

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user:
            session["user_logged_in"] = True
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect("/events")
        else:
            error = "Invalid email or password."

    return render_template("user/login.html", error=error)


@app.route("/user/logout")
def user_logout():
    session.clear()
    return redirect("/")


# 3) EVENTS PAGE (Only after user login)
@app.route("/events")
def index():
    if not session.get("user_logged_in"):
        return redirect("/user/login")

    q = request.args.get("q", "").strip()
    filter_option = request.args.get("filter", "upcoming")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    base_query = """
        SELECT 
            e.*,
            COUNT(r.id) AS registered_count
        FROM events e
        LEFT JOIN registrations r ON e.id = r.event_id
    """

    conditions = []
    params = []

    if filter_option == "upcoming":
        conditions.append("e.event_date >= CURDATE()")

    if q:
        conditions.append("e.title LIKE %s")
        params.append(f"%{q}%")

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += """
        GROUP BY e.id
        ORDER BY e.event_date ASC
    """

    cursor.execute(base_query, params)
    events = cursor.fetchall()

    cursor.close()
    conn.close()

    for e in events:
        e["event_date"] = str(e["event_date"])
        e["event_time"] = str(e["event_time"])
        e["registered_count"] = int(e["registered_count"])
        e["seats_left"] = int(e["capacity"]) - e["registered_count"]

    return render_template(
        "index.html",
        events=events,
        q=q,
        filter_option=filter_option
    )


# 4) EVENT DETAILS PAGE
@app.route("/event/<int:event_id>")
def event_details(event_id):
    if not session.get("user_logged_in"):
        return redirect("/user/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            e.*,
            COUNT(r.id) AS registered_count
        FROM events e
        LEFT JOIN registrations r ON e.id = r.event_id
        WHERE e.id = %s
        GROUP BY e.id
    """, (event_id,))

    event = cursor.fetchone()

    cursor.close()
    conn.close()

    if not event:
        return "<h1>Event not found</h1>", 404

    event["event_date"] = str(event["event_date"])
    event["event_time"] = str(event["event_time"])
    event["registered_count"] = int(event["registered_count"])
    event["seats_left"] = int(event["capacity"]) - event["registered_count"]

    return render_template("event_details.html", event=event)


# 5) EVENT REGISTRATION (Capacity limit + duplicate email)
@app.route("/event/<int:event_id>/register", methods=["GET", "POST"])
def register_page(event_id):
    if not session.get("user_logged_in"):
        return redirect("/user/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get event + registered count
    cursor.execute("""
        SELECT 
            e.*,
            COUNT(r.id) AS registered_count
        FROM events e
        LEFT JOIN registrations r ON e.id = r.event_id
        WHERE e.id = %s
        GROUP BY e.id
    """, (event_id,))

    event = cursor.fetchone()

    if not event:
        cursor.close()
        conn.close()
        return "<h1>Event not found</h1>", 404

    event["event_date"] = str(event["event_date"])
    event["event_time"] = str(event["event_time"])
    event["registered_count"] = int(event["registered_count"])
    event["seats_left"] = int(event["capacity"]) - event["registered_count"]

    error = ""
    success = ""

    if request.method == "POST":
        # Capacity check
        if event["seats_left"] <= 0:
            error = "Event is full. Registration closed."
        else:
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip()
            branch = request.form.get("branch", "").strip()
            year = request.form.get("year", "").strip()

            if not name or not email or not branch or not year:
                error = "All fields are required."
            else:
                try:
                    cursor.execute("""
                        INSERT INTO registrations (event_id, name, email, branch, year)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (event_id, name, email, branch, year))

                    conn.commit()
                    success = "Registration successful! 🎉"

                except Exception:
                    error = "You have already registered with this email for this event."

                # Refresh counts
                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM registrations
                    WHERE event_id = %s
                """, (event_id,))
                total = cursor.fetchone()["total"]

                event["registered_count"] = int(total)
                event["seats_left"] = int(event["capacity"]) - event["registered_count"]

    cursor.close()
    conn.close()

    return render_template("register.html", event=event, error=error, success=success)


# 6) ADMIN AUTH
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect("/admin/dashboard")

    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT * FROM admins
            WHERE username = %s
        """, (username,))

        admin = cursor.fetchone()

        cursor.close()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin_logged_in"] = True
            session["admin_username"] = admin["username"]
            return redirect("/admin/dashboard")
        else:
            error = "Invalid username or password."

    return render_template("admin/login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")



# 7) ADMIN DASHBOARD
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            e.*,
            COUNT(r.id) AS registered_count
        FROM events e
        LEFT JOIN registrations r ON e.id = r.event_id
        GROUP BY e.id
        ORDER BY e.event_date ASC
    """)
    events = cursor.fetchall()

    cursor.close()
    conn.close()

    for e in events:
        e["event_date"] = str(e["event_date"])
        e["event_time"] = str(e["event_time"])
        e["registered_count"] = int(e["registered_count"])

    return render_template("admin/dashboard.html", events=events)


# 8) ADMIN: ADD EVENT
@app.route("/admin/events/add", methods=["GET", "POST"])
def admin_add_event():
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    error = ""

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        event_date = request.form.get("event_date", "").strip()
        event_time = request.form.get("event_time", "").strip()
        venue = request.form.get("venue", "").strip()
        capacity = request.form.get("capacity", "").strip()

        if not title or not description or not event_date or not event_time or not venue or not capacity:
            error = "All fields are required."
        else:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                INSERT INTO events (title, description, event_date, event_time, venue, capacity)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (title, description, event_date, event_time, venue, capacity))

            conn.commit()
            cursor.close()
            conn.close()

            return redirect("/admin/dashboard")

    return render_template("admin/add_event.html", error=error)


# 9) ADMIN: EDIT EVENT
@app.route("/admin/events/edit/<int:event_id>", methods=["GET", "POST"])
def admin_edit_event(event_id):
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()

    if not event:
        cursor.close()
        conn.close()
        return "<h1>Event not found</h1>", 404

    event["event_date"] = str(event["event_date"])
    event["event_time"] = str(event["event_time"])

    error = ""

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        event_date = request.form.get("event_date", "").strip()
        event_time = request.form.get("event_time", "").strip()
        venue = request.form.get("venue", "").strip()
        capacity = request.form.get("capacity", "").strip()

        if not title or not description or not event_date or not event_time or not venue or not capacity:
            error = "All fields are required."
        else:
            cursor.execute("""
                UPDATE events
                SET title=%s, description=%s, event_date=%s, event_time=%s, venue=%s, capacity=%s
                WHERE id=%s
            """, (title, description, event_date, event_time, venue, capacity, event_id))

            conn.commit()
            cursor.close()
            conn.close()
            return redirect("/admin/dashboard")

    cursor.close()
    conn.close()
    return render_template("admin/edit_event.html", event=event, error=error)


# 10) ADMIN: DELETE EVENT
@app.route("/admin/events/delete/<int:event_id>")
def admin_delete_event(event_id):
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect("/admin/dashboard")


# 11) ADMIN: VIEW REGISTRATIONS
@app.route("/admin/events/<int:event_id>/registrations")
def admin_event_registrations(event_id):
    if not session.get("admin_logged_in"):
        return redirect("/admin/login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM events WHERE id = %s", (event_id,))
    event = cursor.fetchone()

    if not event:
        cursor.close()
        conn.close()
        return "<h1>Event not found</h1>", 404

    cursor.execute("""
        SELECT * FROM registrations
        WHERE event_id = %s
        ORDER BY created_at DESC
    """, (event_id,))
    registrations = cursor.fetchall()

    cursor.close()
    conn.close()

    event["event_date"] = str(event["event_date"])
    event["event_time"] = str(event["event_time"])

    for r in registrations:
        r["created_at"] = str(r["created_at"])

    return render_template("admin/registrations.html", event=event, registrations=registrations)



@app.route("/api/events")
def api_events():
    if not session.get("user_logged_in"):
        return jsonify([])

    q = request.args.get("q", "").strip()
    filter_option = request.args.get("filter", "upcoming")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    base_query = """
        SELECT 
            e.*,
            COUNT(r.id) AS registered_count
        FROM events e
        LEFT JOIN registrations r ON e.id = r.event_id
    """

    conditions = []
    params = []

    if filter_option == "upcoming":
        conditions.append("e.event_date >= CURDATE()")

    if q:
        conditions.append("e.title LIKE %s")
        params.append(f"%{q}%")

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += """
        GROUP BY e.id
        ORDER BY e.event_date ASC
    """

    cursor.execute(base_query, params)
    events = cursor.fetchall()

    cursor.close()
    conn.close()

    for e in events:
        e["event_date"] = str(e["event_date"])
        e["event_time"] = str(e["event_time"])
        e["registered_count"] = int(e["registered_count"])
        e["seats_left"] = int(e["capacity"]) - e["registered_count"]

    return jsonify(events)


@app.route("/user/profile")
def user_profile():
    if not session.get("user_logged_in"):
        return redirect("/user/login")

    user_id = session.get("user_id")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get logged in user's email
    cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        conn.close()
        return redirect("/user/logout")

    user_email = user["email"]

    cursor.execute("""
        SELECT 
            r.created_at,
            e.title,
            e.event_date,
            e.event_time,
            e.venue
        FROM registrations r
        INNER JOIN events e ON r.event_id = e.id
        WHERE r.email = %s
        ORDER BY r.created_at DESC
    """, (user_email,))

    registrations = cursor.fetchall()

    cursor.close()
    conn.close()

    for r in registrations:
        r["created_at"] = str(r["created_at"])
        r["event_date"] = str(r["event_date"])
        r["event_time"] = str(r["event_time"])

    return render_template("user/profile.html", registrations=registrations)





# MAIN
if __name__ == "__main__":
    app.run(debug=True)
