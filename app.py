from flask import Flask, request, render_template, redirect, session
import sqlite3
app= Flask(__name__)
app.secret_key = "mysecretkey"

@app.route("/")
def home():

    

    conn = sqlite3.connect("bus_booking.db")
    conn.row_factory = sqlite3.Row

    buses = conn.execute("""
    SELECT * FROM buses
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        buses=buses
    )
def init_db():
    conn=sqlite3.connect("bus_booking.db")
    cur=conn.cursor()
    conn.commit()
    # user table
    cur.execute("""
                CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                email TEXT,
                password TEXT)""")    
    
    #Bus details
    cur.execute("""CREATE TABLE IF NOT EXISTS buses(id INTEGER PRIMARY KEY AUTOINCREMENT,
                bus_name TEXT,
                source TEXT,
                destination TEXT,
                departure_time TEXT,
                available_seats  INTEGER
                )""")
    #Booking table
    cur.execute("""CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bus_id INTEGER,
                seats_booked  INTEGER)""")

    # Check if buses already exist
    existing_buses = cur.execute(
    "SELECT * FROM buses").fetchall()

    if len(existing_buses) == 0:
    
     cur.execute("""
    INSERT INTO buses
    (bus_name, source, destination, departure_time, available_seats)
    VALUES
    ('GreenLine Express', 'Kochi', 'Bengaluru', '10:00 PM', 30)
     """)

     cur.execute("""
    INSERT INTO buses
    (bus_name, source, destination, departure_time, available_seats)
    VALUES
    ('Swift Travels', 'Bengaluru', 'Mysuru', '7:00 AM', 20)
    """)   
    conn.commit()
    conn.close()
def get_connection():

    conn = sqlite3.connect("bus_booking.db")

    conn.row_factory = sqlite3.Row

    return conn    
@app.route("/buses")
def get_buses():
    conn=sqlite3.connect("bus_booking.db")
    conn.row_factory=sqlite3.Row
    buses=conn.execute("SELECT * FROM buses").fetchall()
    conn.close()
    bus_list=[]
    for bus in buses:
        bus_list.append({
            "id": bus["id"],
            "bus_name": bus["bus_name"],
            "source": bus["source"],
            "destination": bus["destination"],
            "departure_time": bus["departure_time"],
            "available_seats": bus["available_seats"]
        })

    return bus_list
@app.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    username = data["username"]
    email = data["email"]
    password = data["password"]

    conn = sqlite3.connect("bus_booking.db")
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO users (username, email, password)
    VALUES (?, ?, ?)
    """, (username, email, password))

    conn.commit()
    conn.close()

    return {
        "message": "User registered successfully"
    }
@app.route("/login-page", methods=["GET", "POST"])
def login_page():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("bus_booking.db")
        conn.row_factory = sqlite3.Row

        user = conn.execute("""
        SELECT * FROM users
        WHERE email=? AND password=?
        """, (email, password)).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect("/")

        else:

            return render_template(
                "login.html",
                error="Invalid Email or Password"
            )

    return render_template(
        "login.html",
        error=None
    )
@app.route("/book-ticket", methods=["POST"])
def book_ticket():
    data= request.get_json()
    user_id=data["user_id"]
    bus_id=data["bus_id"]
    seats_booked=data["seats_booked"]
    conn=sqlite3.connect("bus_booking.db")
    conn.row_factory=sqlite3.Row
    #check bus
    bus=conn.execute("""SELECT * FROM buses WHERE id=?""",(bus_id,)).fetchone()
    if not bus:
        conn.close()
        return{"message":"bus not found"} 
    if bus["available_seats"] <seats_booked:
        conn.close()
        return{"message":"seats not available"}
#reduce seats    
    conn.execute("""INSERT INTO bookings
                 (user_id, bus_id, seats_booked)
    VALUES (?, ?, ?)
    """, (user_id, bus_id, seats_booked))
    new_seats= bus["available_seats"]-seats_booked
    conn.execute("""UPDATE buses SET available_seats=? WHERE id=?""",(new_seats,bus_id))
    conn.commit()
    conn.close()
    return {
        "message": "Ticket booked successfully"
    }
@app.route("/my-bookings/<int:user_id>")
def my_bookings(user_id):

    conn = sqlite3.connect("bus_booking.db")
    conn.row_factory = sqlite3.Row

    bookings = conn.execute("""
    SELECT
        bookings.id,
        buses.bus_name,
        buses.source,
        buses.destination,
        buses.departure_time,
        bookings.seats_booked

    FROM bookings

    JOIN buses
    ON bookings.bus_id = buses.id

    WHERE bookings.user_id = ?
    """, (user_id,)).fetchall()

    conn.close()

    booking_list = []

    for booking in bookings:

        booking_list.append({
            "booking_id": booking["id"],
            "bus_name": booking["bus_name"],
            "source": booking["source"],
            "destination": booking["destination"],
            "departure_time": booking["departure_time"],
            "seats_booked": booking["seats_booked"]
        })

    return booking_list
@app.route("/cancel-booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):

    conn = sqlite3.connect("bus_booking.db")
    conn.row_factory = sqlite3.Row

    # Find booking
    booking = conn.execute("""
    SELECT * FROM bookings
    WHERE id = ?
    """, (booking_id,)).fetchone()

    # Booking not found
    if not booking:
        conn.close()

        return {
            "message": "Booking not found"
        }

    # Find bus
    bus = conn.execute("""
    SELECT * FROM buses
    WHERE id = ?
    """, (booking["bus_id"],)).fetchone()

    # Restore seats
    restored_seats = bus["available_seats"] + booking["seats_booked"]

    conn.execute("""
    UPDATE buses
    SET available_seats = ?
    WHERE id = ?
    """, (restored_seats, booking["bus_id"]))

    # Delete booking
    conn.execute("""
    DELETE FROM bookings
    WHERE id = ?
    """, (booking_id,))

    conn.commit()
    

    bookings = conn.execute("""
    SELECT
    bookings.id,
    buses.bus_name,
    buses.source,
    buses.destination,
    buses.departure_time,
    bookings.seats_booked

FROM bookings

JOIN buses
ON bookings.bus_id = buses.id

WHERE bookings.user_id = ?
""", (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
    "my_bookings.html",
    bookings=bookings,
    success="Booking Cancelled Successfully"
)
@app.route("/register-page", methods=["GET", "POST"])
def register_page():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("bus_booking.db")

        conn.execute("""
        INSERT INTO users
        (username, email, password)
        VALUES (?, ?, ?)
        """, (username, email, password))

        conn.commit()
        conn.close()

        return "User Registered Successfully"

    return render_template("register.html")

@app.route("/book-page/<int:bus_id>")
def book_page(bus_id):

    if "user_id" not in session:
        return redirect("/login-page")

    conn = sqlite3.connect("bus_booking.db")
    conn.row_factory = sqlite3.Row

    bus = conn.execute("""
    SELECT * FROM buses
    WHERE id = ?
    """, (bus_id,)).fetchone()

    conn.close()

    return render_template(
        "book_ticket.html",
        bus=bus
    )  
@app.route("/confirm-booking/<int:bus_id>", methods=["POST"])
def confirm_booking(bus_id):

    user_id = session["user_id"]
    seats_booked = int(request.form["seats_booked"])

    conn = sqlite3.connect("bus_booking.db")
    conn.row_factory = sqlite3.Row

    bus = conn.execute("""
    SELECT * FROM buses
    WHERE id = ?
    """, (bus_id,)).fetchone()

    if bus["available_seats"] < seats_booked:

        conn.close()

        return render_template(
            "book_ticket.html",
            bus=bus,
            error="Seats not available"
        )

    conn.execute("""
    INSERT INTO bookings
    (user_id, bus_id, seats_booked)
    VALUES (?, ?, ?)
    """, (user_id, bus_id, seats_booked))

    new_seats = bus["available_seats"] - seats_booked

    conn.execute("""
    UPDATE buses
    SET available_seats = ?
    WHERE id = ?
    """, (new_seats, bus_id))

    conn.commit()

    bus = conn.execute("""
    SELECT * FROM buses
    WHERE id = ?
    """, (bus_id,)).fetchone()

    conn.close()

    return render_template(
        "book_ticket.html",
        bus=bus,
        success="Ticket Booked Successfully"
    )
@app.route("/my-bookings-page/<int:user_id>")
def my_bookings_page(user_id):

    conn = sqlite3.connect("bus_booking.db")
    conn.row_factory = sqlite3.Row

    bookings = conn.execute("""
    SELECT
        bookings.id,
        buses.bus_name,
        buses.source,
        buses.destination,
        buses.departure_time,
        bookings.seats_booked

    FROM bookings

    JOIN buses
    ON bookings.bus_id = buses.id

    WHERE bookings.user_id = ?
    """, (user_id,)).fetchall()

    conn.close()

    return render_template(
        "my_bookings.html",
        bookings=bookings
    )
    
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/") 
# -----------------------------
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # Simple admin login
        if username == "admin" and password == "1234":

            session["admin"] = True

            return redirect("/admin")

        return "Invalid username or password"

    return render_template("admin_login.html")


# -----------------------------
# ADMIN LOGOUT
# -----------------------------
@app.route("/admin-logout")
def admin_logout():

    session.pop("admin", None)

    return redirect("/")


# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
@app.route("/admin")
def admin():

    if "admin" not in session:

        return redirect("/admin-login")

    conn = get_connection()

    buses = conn.execute("""
    SELECT * FROM buses
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        buses=buses
    )


# -----------------------------
# ADD BUS
# -----------------------------
@app.route("/add-bus", methods=["GET", "POST"])
def add_bus():

    if "admin" not in session:

        return redirect("/admin-login")

    if request.method == "POST":

        bus_name = request.form["bus_name"]
        source = request.form["source"]
        destination = request.form["destination"]
        available_seats = request.form["available_seats"]

        conn = get_connection()

        conn.execute("""
INSERT INTO buses
(bus_name, source, destination, available_seats)
VALUES (?, ?, ?, ?)
""", (
    bus_name,
    source,
    destination,
    available_seats
))

        conn.commit()
        conn.close()

        return redirect("/admin")

    return render_template("add_bus.html")


# -----------------------------
# UPDATE BUS
# -----------------------------
@app.route("/update-bus/<int:bus_id>", methods=["GET", "POST"])
def update_bus(bus_id):

    if "admin" not in session:

        return redirect("/admin-login")

    conn = get_connection()

    bus = conn.execute("""
    SELECT * FROM buses
    WHERE id = ?
    """, (bus_id,)).fetchone()

    if not bus:

        conn.close()

        return "Bus not found"

    if request.method == "POST":

        bus_name = request.form["bus_name"]
        source = request.form["source"]
        destination = request.form["destination"]
        available_seats = request.form["available_seats"]

        conn.execute("""
UPDATE buses
SET bus_name = ?,
    source = ?,
    destination = ?,
    available_seats = ?
WHERE id = ?
""", (
    bus_name,
    source,
    destination,
    available_seats,
    bus_id
))

        conn.commit()
        conn.close()

        return redirect("/admin")

    conn.close()

    return render_template(
        "update_bus.html",
        bus=bus
    )


# -----------------------------
# DELETE BUS
# -----------------------------
@app.route("/delete-bus/<int:bus_id>", methods=["POST"])
def delete_bus(bus_id):

    if "admin" not in session:

        return redirect("/admin-login")

    conn = get_connection()

    conn.execute("""
    DELETE FROM buses
    WHERE id = ?
    """, (bus_id,))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/search")
def search():

    source = request.args.get("source")
    destination = request.args.get("destination")

    conn = get_connection()

    buses = conn.execute("""
    SELECT * FROM buses
    WHERE source LIKE ?
    AND destination LIKE ?
    """, (
        f"%{source}%",
        f"%{destination}%"
    )).fetchall()

    conn.close()

    return render_template(
        "index.html",
        buses=buses
    )
# -----------------------------
# RUN APP
# -----------------------------


if __name__== "__main__":
        init_db()
        app.run (debug=True)