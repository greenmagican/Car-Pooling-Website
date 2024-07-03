from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
import os
from functools import wraps
import send_email

app = Flask(__name__)
app.secret_key = os.urandom(24) #I was searching ways to make my code more safe and I came accross "Use a secret key" suggestion. 
                                #It doesn't protect against sql injection. But makes the code safer overall. So it is a good practice to have.
                                #Further reference: 
                                # 1.) https://stackoverflow.com/questions/22463939/demystify-flask-app-secret-key
                                # 2.) https://www.reddit.com/r/flask/comments/m0z7s1/need_some_help_understanding_the_use_of_a_flask/

# Kaan Tandogan
def get_db_connection(): # !!! Needed for the initial DB connection. To connect to your database you need to make changes. !!!
    conn = psycopg2.connect(
        host="localhost",
        database="HermesDB",
        user="postgres",
        password="107610"
    )
    conn.set_client_encoding('UTF8')
    return conn



# Kaan Tandogan
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    success = request.args.get('success')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('pwd')
        
        if not username or not password: # It should give an error if the user enters nothing.
            error = 'Username and password are required'
        else:
            try:
                conn = get_db_connection() # Connects to execute commands on postgresql.
                cur = conn.cursor()
                cur.execute('SELECT email, password FROM users WHERE email = %s', (username,))
                user = cur.fetchone()
                cur.close()
                conn.close()
                
                if user is None: # At first for security reasons I thought of making it a bit abstract. 
                                 # (Like it should say "either name or password is wrong")
                                 # But later I thought it'd be better if its more user friendly
                    error = 'Invalid username'
                elif user[1] != password:
                    error = 'Invalid password'
                else:
                    session['user_email'] = user[0]
                    flash('You were successfully logged in')
                    return redirect(url_for('home'))
            except UnicodeDecodeError as e:
                error = 'An error occurred with character encoding: ' + str(e)
            except Exception as e:
                error = 'An unexpected error occurred: ' + str(e)

    return render_template('login.html', error=error, success=success)

# Kaan Tandogan
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    success = None
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        surname = request.form.get('surname')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        if not email or not name or not surname or not phone or not password: #User is expected to provide all fields.
            error = 'All fields are required'
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute('SELECT * FROM users WHERE email = %s', (email,))
                user = cur.fetchone()
                
                if user: # E-mail is the primary key, it can't be repeat.
                    error = 'A User With The Given E-mail Already Exists In Our Servers'
                else:
                    cur.execute('INSERT INTO users (email, name, surname, password) VALUES (%s, %s, %s, %s)', (email, name, surname, password))
                    cur.execute('INSERT INTO phone_numbers (phone_number, user_email) VALUES (%s, %s)', (phone, email))
                    cur.execute('INSERT INTO passengers (passenger_email) VALUES (%s)', (email,))
                    conn.commit()
                    success = 'Registration is Successful'
                
                cur.close()
                conn.close()
                
                if success:
                    return redirect(url_for('login', success=success))
            except UnicodeDecodeError as e:
                error = 'An error occurred with character encoding: ' + str(e)
            except Exception as e:
                error = 'An unexpected error occurred: ' + str(e)

    return render_template('register.html', error=error, success=success)


# Kaan Tandogan
@app.route('/logout')
def logout():
    session.pop('user_email', None)
    flash('You were successfully logged out')
    return redirect(url_for('login'))

# Kaan Tandogan
@app.route('/')
def home_redirect():
    return redirect(url_for('login'))



# Kaan Tandogan
def login_required(f): # This ensures that an unlogged user can only see login page and can go to register from there.
                       # I got this somewhere from stackoverflow but I'm unable to find it right now.
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



# Kaan Tandogan
@app.route('/home')
@login_required
def home():
    user_email = session.get('user_email')
    error = request.args.get('error')
    success = request.args.get('success')
    return render_template('home.html', user_email=user_email, error=error, success=success)



# Egemen Aksöz
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user_email = session.get('user_email')
    error = None
    success = None
    user = None
    preferences = None
    is_driver = False

    try:
        conn = get_db_connection()  # DB connection
        cur = conn.cursor()

        # I got the user details here.
        cur.execute('SELECT email, name, surname, password FROM users WHERE email = %s', (user_email,))
        user = cur.fetchone()

        # I checked whether the user is driver.
        cur.execute('SELECT * FROM drivers WHERE driver_email = %s', (user_email,))
        driver = cur.fetchone()
        if driver:
            is_driver = True
            # I got user preferences if the user is a driver
            cur.execute('SELECT preference FROM preferences WHERE driver_email = %s', (user_email,))
            preferences = cur.fetchone()

        if request.method == 'POST':
            new_email = request.form.get('email')
            name = request.form.get('name')
            surname = request.form.get('surname')
            password = request.form.get('password')
            prefs = request.form.get('preferences')
            # I validated all required fields are filled out.
            if not new_email or not name or not surname or not password or (is_driver and not prefs):
                error = 'All fields are required'
            else:
                # I checked the new e-mail already taken or not. If so, error message displayed.
                cur.execute('SELECT email FROM users WHERE email = %s', (new_email,))
                if cur.fetchone() and new_email != user_email:
                    error = 'This email is already in use.'
                else:
                    try:
                       
                        cur.execute('BEGIN')

                        # If the email is changed, I create a new user and delete old.
                        if new_email != user_email:
                            # I added new user with e-mail
                            cur.execute('INSERT INTO users (email, name, surname, password) VALUES (%s, %s, %s, %s)',
                                        (new_email, name, surname, password))

                            # If the old user is a driver, I added the new user to the drivers table along with the driving lincence number.
                            if is_driver:
                                cur.execute('INSERT INTO drivers (driver_email, driver_license_no) VALUES (%s, %s)',
                                            (new_email, driver[1]))     

                            # I updated the related tables.
                            cur.execute('UPDATE phone_numbers SET user_email = %s WHERE user_email = %s', (new_email, user_email))

                            if is_driver:
                                cur.execute('UPDATE vehicles SET driver_email = %s WHERE driver_email = %s', (new_email, user_email))
                                cur.execute('UPDATE trips SET driver_email = %s WHERE driver_email = %s', (new_email, user_email))
                            else:
                                cur.execute('UPDATE passengers SET passenger_email = %s WHERE passenger_email = %s', (new_email, user_email))
                                cur.execute('UPDATE reviews SET passenger_email = %s WHERE passenger_email = %s', (new_email, user_email))
                                cur.execute('UPDATE bookings SET passenger_email = %s WHERE passenger_email = %s', (new_email, user_email))

                            # I updated preferences or insert if the user is driver
                            if is_driver:
                                if preferences:
                                    cur.execute('UPDATE preferences SET driver_email = %s WHERE driver_email = %s AND preference = %s',
                                                (new_email, user_email, preferences[0]))
                                else:
                                    cur.execute('INSERT INTO preferences (driver_email, preference) VALUES (%s, %s)',
                                                (new_email, prefs))

                            # I committed changes before deleting old user
                            conn.commit()

                            # I deleted the old user from drivers table
                            if is_driver:
                                cur.execute('DELETE FROM drivers WHERE driver_email = %s', (user_email,))

                           
                            cur.execute('DELETE FROM users WHERE email = %s', (user_email,))

                            # I commited transaction.
                            conn.commit()

                            # I update session email
                            session['user_email'] = new_email
                            success = 'Profile updated successfully'
                        else:
                            # If email is not changed, I updated other fields
                            updates = []
                            params = []

                            if name != user[1]:
                                updates.append('name = %s')
                                params.append(name)
                            if surname != user[2]:
                                updates.append('surname = %s')
                                params.append(surname)
                            if password != user[3]:
                                updates.append('password = %s')
                                params.append(password)

                            if updates:
                                query = f'UPDATE users SET {", ".join(updates)} WHERE email = %s'
                                params.append(user_email)
                                cur.execute(query, params)

                            if is_driver:
                                if preferences and prefs != preferences[0]:
                                    cur.execute('UPDATE preferences SET preference = %s WHERE driver_email = %s AND preference = %s',
                                                (prefs, user_email, preferences[0]))
                                elif not preferences:
                                    cur.execute('INSERT INTO preferences (driver_email, preference) VALUES (%s, %s)',
                                                (user_email, prefs))

                            conn.commit()
                            success = 'Profile updated successfully'

                        cur.execute('SELECT email, name, surname, password FROM users WHERE email = %s', (new_email if new_email != user_email else user_email,))
                        user = cur.fetchone()

                        if is_driver:
                        # I fetched updated user details and preferences after committing the changes
                            cur.execute('SELECT preference FROM preferences WHERE driver_email = %s', (new_email if new_email != user_email else user_email,))
                            preferences = cur.fetchone()
                    # If error occurs ROLL-BACK the transaction and sets an error message.
                    except Exception as e:
                        conn.rollback()
                        error = 'An error occurred while updating your profile: ' + str(e)

        cur.close()
        conn.close()
    except Exception as e:
        error = 'An error occurred: ' + str(e)

    if preferences:
        preferences = preferences[0]  # I extract the preferences string from the tuple
    return render_template('edit_profile.html', user=user, preferences=preferences, is_driver=is_driver, error=error, success=success)



# Kaan Tandogan
@app.route('/add_trips', methods=['GET', 'POST'])
@login_required
def add_trips():
    user_email = session.get('user_email')

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM drivers WHERE driver_email = %s', (user_email,))
        driver = cur.fetchone()

        if not driver: # Only drivers can add trips. Passengers can only book. So if it is a passenger that tries to add a trip s/he should get an error.
            error = 'Only Drivers (who registered a car) Can Add Trips'
            return redirect(url_for('home', error=error))

        cur.execute('SELECT plate_no, model FROM vehicles WHERE driver_email = %s', (user_email,)) #We will show the available cars to our drivers.
        available_cars = cur.fetchall()
        cur.close()
        conn.close()

        if request.method == 'POST':
            if 'trip_data' not in session:
                from_city = request.form.get('from')
                to_city = request.form.get('to')
                car = request.form.get('car')
                capacity = request.form.get('capacity')

                session['trip_data'] ={ # Stored the trip data in session.
                    'from_city': from_city,
                    'to_city': to_city,
                    'car': car,
                    'capacity': capacity,
                    'user_email': user_email
                }

                city_distances ={ # We took Güzelyurt as the center and give other cities numbers with respect to how far they are from Güzelyurt.
                    "Lefkoşa": 4,
                    "Gazimağusa": 5,
                    "Girne": 3,
                    "Güzelyurt": 1,
                    "İskele": 5
                }

                distance_from_center = abs(city_distances[from_city] - city_distances[to_city])
                min_price = 200
                max_price = min_price + distance_from_center * 50

                session['price_range'] = {
                    'min_price': min_price,
                    'max_price': max_price
                }

                return render_template('selected_price.html', min_price=min_price, max_price=max_price) # Redirected to the selected_price.html with price range.

            else:
                price = request.form.get('price')
                trip_data = session.pop('trip_data', None)

                if trip_data:
                    conn = get_db_connection()
                    cur = conn.cursor() # Inserted into the trips.
                    cur.execute('INSERT INTO trips (from_location, to_location, passenger_capacity, payment, driver_email, vehicle_plate_no) VALUES (%s, %s, %s, %s, %s, %s)',
                                (trip_data['from_city'], trip_data['to_city'], trip_data['capacity'], price, trip_data['user_email'], trip_data['car']))
                    conn.commit()
                    cur.close()
                    conn.close()
                    success = 'Trip successfully added'
                    return redirect(url_for('home', success=success))

    except Exception as e:
        error = 'An unexpected error occurred: ' + str(e)
        available_cars = []
        return redirect(url_for('home', error=error))

    return render_template('addtrip.html', available_cars=available_cars, user_email=user_email)



# Kaan Tandogan
@app.route('/remove_trips', methods=['GET', 'POST'])
@login_required
def remove_trips():
    user_email = session.get('user_email')
    error = None
    success = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('SELECT * FROM drivers WHERE driver_email = %s', (user_email,)) # Checked if the user is a driver or a passenger
        driver = cur.fetchone()
        is_driver = bool(driver)

        # Fetched the trips the user has added or booked.
        cur.execute(""" 
            SELECT t.trip_id, t.from_location, t.to_location, t.payment, t.driver_email, t.vehicle_plate_no
            FROM trips t
            WHERE t.driver_email = %s OR t.trip_id IN (
                SELECT b.trip_id FROM bookings b WHERE b.passenger_email = %s
            )
        """, (user_email, user_email))
        trips = cur.fetchall()

        if request.method == 'POST':
            selected_trips = request.form.getlist('trips')
            if selected_trips:
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    
                    for trip_id in selected_trips:
                        trip_id = int(trip_id)  # Ensured the trip_id is an integer.
                        if is_driver:
                            print("\n\nDriver cancels a trip\n\n")
                            # Fetched the passengers emails before deleting bookings.
                            cur.execute('SELECT passenger_email FROM bookings WHERE trip_id = %s', (trip_id,))
                            passengers = cur.fetchall()
                            
                            for passenger_email in passengers: # Emailed to passengers about the trip cancellation.
                                cur.execute('SELECT name, surname, from_location, to_location FROM users u JOIN trips t ON u.email = t.driver_email WHERE t.trip_id = %s', (trip_id,))
                                driver_info = cur.fetchone()
                                print("passenger_email is: " + passenger_email[0])
                                send_email.send_email(driver_info[0], driver_info[1], driver_info[2], driver_info[3], None, passenger_email[0], 3)
                            
                            # Deleted the reviews and bookings.
                            cur.execute('DELETE FROM reviews WHERE trip_id = %s', (trip_id,))
                            cur.execute('DELETE FROM bookings WHERE trip_id = %s', (trip_id,))
                            # Deleted the trip.
                            cur.execute('DELETE FROM trips WHERE trip_id = %s', (trip_id,))
                        else:
                            # If its passenger that cancelled then notified the driver about the trip cancellation via email.
                            cur.execute('SELECT name, surname, from_location, to_location, driver_email FROM users u JOIN trips t ON u.email = t.driver_email WHERE t.trip_id = %s', (trip_id,))
                            driver_info = cur.fetchone()
                            cur.execute('SELECT name, surname FROM users WHERE email = %s', (user_email,))
                            passenger_info = cur.fetchone()
                            send_email.send_email(passenger_info[0], passenger_info[1], driver_info[2], driver_info[3], None, driver_info[4], 2)
                            
                            # Deleted the passengers review and booking.
                            cur.execute('DELETE FROM reviews WHERE trip_id = %s AND passenger_email = %s', (trip_id, user_email))
                            cur.execute('DELETE FROM bookings WHERE trip_id = %s AND passenger_email = %s', (trip_id, user_email))
                            
                            # Increase the number of seats available in the trip.
                            cur.execute('UPDATE trips SET passenger_capacity = passenger_capacity + 1 WHERE trip_id = %s', (trip_id,))

                    conn.commit()
                    success = 'Selected trip/s successfully removed'
                    return redirect(url_for('home', success=success))
                except Exception as e:
                    conn.rollback()
                    error = 'An error occurred: ' + str(e)
                finally:
                    cur.close()
                    conn.close()
    except Exception as e:
        error = 'An error occurred: ' + str(e)
        trips = []

    return render_template('remove_trips.html', trips=trips, error=error, success=success)



# Kaan Tandogan
@app.route('/vehicle_operations', methods=['GET', 'POST'])  # User can either add a new vehicle or drop an existing vehicle.
@login_required
def vehicle_operations():
    user_email = session.get('user_email')
    error = None
    success = None

    if request.method == 'POST':
        if 'add_vehicle' in request.form:
            return redirect(url_for('add_vehicle'))  # Redirected to the vehicle addition form.

        if 'delete_vehicle' in request.form:
            selected_vehicles = request.form.getlist('vehicles')
            if selected_vehicles:
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()

                    vehicles_with_trips = []
                    for plate_no in selected_vehicles:
                        cur.execute('SELECT * FROM trips WHERE vehicle_plate_no = %s', (plate_no,)) # We check if the vehicle has a trip under its plate no. If yes it should give an error.
                        trips = cur.fetchall()
                        if trips:
                            vehicles_with_trips.append(plate_no)
                        else:
                            cur.execute('DELETE FROM vehicles WHERE plate_no = %s', (plate_no,))

                    # If a user has no vehicles left s/he should be moved into passenger. So here I check whether s/he has a vehicle after deletion.
                    cur.execute('SELECT * FROM vehicles WHERE driver_email = %s', (user_email,))
                    remaining_vehicles = cur.fetchall()

                    if not remaining_vehicles:  # Removed from the drivers and add to the passengers if no vehicles left.
                        cur.execute('DELETE FROM drivers WHERE driver_email = %s', (user_email,))
                        cur.execute('INSERT INTO passengers (passenger_email) VALUES (%s)', (user_email,))

                    conn.commit()
                    cur.close()
                    conn.close()

                    if vehicles_with_trips:
                        error = 'To drop a Car, that car shouldn\'t have any trips under its name. Please remove trips first for the following vehicles: ' + ', '.join(vehicles_with_trips)
                    else:
                        success = 'Selected vehicles were successfully deleted'
                except Exception as e:
                    error = 'An error occurred: ' + str(e)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT plate_no, color, year, model FROM vehicles WHERE driver_email = %s', (user_email,))
        vehicles = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        error = 'An error occurred: ' + str(e)
        vehicles = []

    return render_template('vehicle_operations.html', vehicles=vehicles, error=error, success=success)



# Kaan Tandogan
@app.route('/add_vehicle', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    user_email = session.get('user_email')
    error = None
    success = None

    if request.method == 'POST':
        plate_no = request.form.get('plate_no')
        color = request.form.get('color')
        year = request.form.get('year')
        model = request.form.get('model')
        number_of_seats = request.form.get('number_of_seats')
        # All fields are expected to be filled.
        if not plate_no or not color or not year or not model or not number_of_seats:
            error = 'All fields are required'
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()

                cur.execute('BEGIN')

                # Checked if the user is a passenger. If yes, then we need to make him a driver.
                cur.execute('SELECT * FROM passengers WHERE passenger_email = %s', (user_email,))
                passenger = cur.fetchone()

                if passenger: #Made the passenger a driver.
                    cur.execute('DELETE FROM passengers WHERE passenger_email = %s', (user_email,))
                    cur.execute('INSERT INTO drivers (driver_email) VALUES (%s)', (user_email,))

                conn.commit()

                # Added the vehicle.
                cur.execute('INSERT INTO vehicles (plate_no, color, year, model, number_of_seats, driver_email) VALUES (%s, %s, %s, %s, %s, %s)',
                            (plate_no, color, year, model, number_of_seats, user_email))
                conn.commit()

                cur.close()
                conn.close()
                success = 'Vehicle successfully added'
                return redirect(url_for('vehicle_operations', success=success))
            except Exception as e:
                error = 'An error occurred: ' + str(e)
                conn.rollback()

    return render_template('add_vehicle.html', error=error, success=success)



@app.route('/get_trips', methods=['GET', 'POST'])
@login_required
def get_trips():
    user_email = session.get('user_email')
    available_trips = []
    booked_trips = []
    error = None
    from_city = ""
    to_city = ""

    if request.method == 'POST':
        from_city = request.form.get('from')
        to_city = request.form.get('to')

        if not from_city or not to_city:
            error = 'All fields are required'
        else:
            try:
                conn = get_db_connection()
                cur = conn.cursor()

                cur.execute('''
                    SELECT t.trip_id, t.from_location, t.to_location, t.passenger_capacity, t.payment, t.driver_email, t.vehicle_plate_no,
                           v.color, v.year, v.model, STRING_AGG(p.preference, ', ') as preferences
                    FROM trips t
                    JOIN vehicles v ON t.vehicle_plate_no = v.plate_no
                    JOIN drivers d ON t.driver_email = d.driver_email
                    LEFT JOIN preferences p ON t.driver_email = p.driver_email
                    WHERE t.from_location = %s AND t.to_location = %s AND t.passenger_capacity > 0
                    GROUP BY t.trip_id, t.from_location, t.to_location, t.passenger_capacity, t.payment, t.driver_email, t.vehicle_plate_no,
                             v.color, v.year, v.model
                ''', (from_city, to_city))
                available_trips = cur.fetchall()

                # Fetch booked trips for the user
                cur.execute('''
                    SELECT trip_id
                    FROM bookings
                    WHERE passenger_email = %s
                ''', (user_email,))
                booked_trips = [trip[0] for trip in cur.fetchall()]

                cur.close()
                conn.close()
            except Exception as e:
                error = 'An error occurred: ' + str(e)
                available_trips = []

    return render_template('get_trips.html', user_email=user_email, available_trips=available_trips, booked_trips=booked_trips, error=error, from_city=from_city, to_city=to_city)

# Egemen Aksöz
@app.route('/book_trip', methods=['POST'])
@login_required
def book_trip():
    user_email = session.get('user_email')
    trip_id = request.form.get('trip_id')
    error = None

    try:
        conn = get_db_connection() # For establish connection.
        cur = conn.cursor()

        # I checked current capacity of the trip and I get trip-details.
        cur.execute('SELECT passenger_capacity, driver_email, from_location, to_location FROM trips WHERE trip_id = %s', (trip_id,))
        trip = cur.fetchone()

        if trip and trip[0] > 0:
            # I checked if the trip exists, and available seats 
            # then insert a new booking into the bookings table.
            cur.execute('INSERT INTO bookings (trip_id, passenger_email) VALUES (%s, %s)', (trip_id, user_email))

            # I updated the passenger capacity in the trips table
            cur.execute('UPDATE trips SET passenger_capacity = passenger_capacity - 1 WHERE trip_id = %s', (trip_id,))

            # I got passenger details
            cur.execute('SELECT name, surname, phone_number FROM users u JOIN phone_numbers p ON u.email = p.user_email WHERE u.email = %s', (user_email,))
            passenger = cur.fetchone()

            # I got driver e-mails from the trip details.
            driver_email = trip[1]

            # I committed the transaction and save changes to database.
            conn.commit()

            # Send email to the driver
            send_email.send_email(
                name=passenger[0], 
                surname=passenger[1], 
                from_place=trip[2], 
                to_place=trip[3], 
                phone_number=passenger[2], 
                e_mail_receiver=driver_email,
                case=1  # Case 1 for booking a trip
            )

            flash('Trip booked successfully', 'success')
        else:
            error = 'Not enough seats available'
            flash(error, 'error')

        cur.close()
        conn.close()
    except Exception as e:
        error = 'An error occurred: ' + str(e)
        flash(error, 'error')

    return redirect(url_for('get_trips'))

if __name__ == '__main__':
    app.run(debug=True)
