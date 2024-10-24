from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector  # MariaDB connector

app = Flask(__name__)

# Configuration for MariaDB
db_config = {
    'host': 'localhost',    # Update with your host
    'user': 'root',     # Update with your username
    'password': 'poopnugs69?',  # Update with your password
    'database': 'putt_tracker_db', # Update with your database name
    'charset': 'utf8mb4',    # Use utf8mb4 for wide Unicode support
    'collation': 'utf8mb4_general_ci'  # A compatible collation for MariaDB
}

# Function to initialize the database
def init_db():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rounds (
            id INT PRIMARY KEY AUTO_INCREMENT,
            makes INT NOT NULL,
            misses INT NOT NULL,
            distance INT NOT NULL,
            timestamp DATETIME
        )
    ''')
    conn.commit()
    cursor.close()
    conn.close()

# Route for the homepage
@app.route('/')
def index():
    distances = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70]  # Predefined distances
    return render_template('index.html', distances=distances)

# Route to add a make
@app.route('/add_make', methods=['POST'])
def add_make():
    current_round = request.json['current_round']
    current_round['makes'] += 1
    return jsonify(current_round)

# Route to add a miss
@app.route('/add_miss', methods=['POST'])
def add_miss():
    current_round = request.json['current_round']
    current_round['misses'] += 1
    return jsonify(current_round)

# Route to end a round and save it to the database
@app.route('/end_round', methods=['POST'])
def end_round():
    data = request.json
    distance = data['distance']
    makes = data['makes']
    misses = data['misses']

    # Get the current timestamp using Python's datetime module
    current_timestamp = datetime.now()

    # Save to the database
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO rounds (makes, misses, distance, timestamp) 
        VALUES (%s, %s, %s, %s)
    ''', (makes, misses, distance, current_timestamp))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'status': 'Round saved!'})

@app.route('/rounds')
def show_rounds():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Fetch the id, makes, misses, distance, and timestamp from the database
    cursor.execute('SELECT id, makes, misses, distance, timestamp FROM rounds ORDER BY timestamp DESC')
    rounds = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('rounds.html', rounds=rounds)

@app.route('/round/<int:round_id>')
def round_detail(round_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Fetch the specific round using its ID
    cursor.execute('SELECT makes, misses, distance, timestamp FROM rounds WHERE id = %s', (round_id,))
    round_data = cursor.fetchone()
    cursor.close()
    conn.close()

    if round_data:
        makes = round_data[0]
        misses = round_data[1]
        distance = round_data[2]
        timestamp = round_data[3]

        # Calculate total putts, percentage made, and percentage missed
        total_putts = makes + misses
        percentage_made = (makes / total_putts) * 100 if total_putts > 0 else 0
        percentage_missed = (misses / total_putts) * 100 if total_putts > 0 else 0

        return render_template('round_detail.html',
                               makes=makes,
                               misses=misses,
                               distance=distance,
                               timestamp=timestamp,
                               total_putts=total_putts,
                               percentage_made=percentage_made,
                               percentage_missed=percentage_missed)
    else:
        return "Round not found", 404

@app.route('/stats')
def stats():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Query to group rounds by distance and calculate total putts, makes, and misses
    cursor.execute('''
        SELECT distance, SUM(makes) AS total_makes, SUM(misses) AS total_misses
        FROM rounds
        GROUP BY distance
        ORDER BY distance ASC
    ''')
    stats_data = cursor.fetchall()
    cursor.close()
    conn.close()

    # Process the data and calculate percentages
    stats_summary = []
    for data in stats_data:
        distance = data[0]
        total_makes = data[1]
        total_misses = data[2]
        total_putts = total_makes + total_misses
        percentage_made = (total_makes / total_putts) * 100 if total_putts > 0 else 0
        percentage_missed = (total_misses / total_putts) * 100 if total_putts > 0 else 0

        stats_summary.append({
            'distance': distance,
            'total_putts': total_putts,
            'percentage_made': round(percentage_made, 2),
            'percentage_missed': round(percentage_missed, 2)
        })

    # Pass the accumulated statistics to the stats.html template
    return render_template('stats.html', stats=stats_summary)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
