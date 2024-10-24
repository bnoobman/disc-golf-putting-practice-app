from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
import mysql.connector  # MariaDB connector
from config import DevelopmentConfig, ProductionConfig, TestingConfig
import os
import matplotlib.pyplot as plt
import io
import base64

from dotenv import load_dotenv
load_dotenv()  # Automatically loads environment variables from .env

app = Flask(__name__)

# Choose the configuration based on the environment
environment = os.environ.get('FLASK_ENV', 'development')

if environment == 'development':
    app.config.from_object(DevelopmentConfig())
elif environment == 'production':
    app.config.from_object(ProductionConfig())
elif environment == 'testing':
    app.config.from_object(TestingConfig())
else:
    app.config.from_object(DevelopmentConfig())  # Default to development

# Function to initialize the database using the app's configuration
def init_db():
    conn = mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        charset=app.config['DB_CHARSET'],
        collation=app.config['DB_COLLATION']
    )
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
    conn = mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        charset='utf8mb4',  # Set charset to utf8mb4
        collation='utf8mb4_general_ci'  # Explicitly set the collation
    )
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
    conn = mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        charset='utf8mb4',  # Set charset to utf8mb4
        collation='utf8mb4_general_ci'  # Explicitly set the collation
    )
    cursor = conn.cursor()

    # Fetch the id, makes, misses, distance, and timestamp from the database
    cursor.execute('SELECT id, makes, misses, distance, timestamp FROM rounds ORDER BY timestamp DESC')
    rounds = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('rounds.html', rounds=rounds)

@app.route('/round/<int:round_id>')
def round_detail(round_id):
    conn = mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        charset='utf8mb4',  # Set charset to utf8mb4
        collation='utf8mb4_general_ci'  # Explicitly set the collation
    )
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


@app.route('/delete_round/<int:round_id>', methods=['POST'])
def delete_round(round_id):
    # Connect to the database
    conn = mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        charset='utf8mb4',  # Set charset to utf8mb4
        collation='utf8mb4_general_ci'  # Explicitly set the collation
    )
    cursor = conn.cursor()

    # Execute the DELETE SQL statement
    cursor.execute('DELETE FROM rounds WHERE id = %s', (round_id,))
    conn.commit()

    # Close the connection
    cursor.close()
    conn.close()

    return 'Round deleted!'

@app.route('/stats')
def stats():
    conn = mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        charset='utf8mb4',  # Set charset to utf8mb4
        collation='utf8mb4_general_ci'  # Explicitly set the collation
    )
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


@app.route('/distance/<int:distance>')
def distance_detail(distance):
    conn = mysql.connector.connect(
        host=app.config['DB_HOST'],
        user=app.config['DB_USER'],
        password=app.config['DB_PASSWORD'],
        database=app.config['DB_NAME'],
        charset='utf8mb4',
        collation='utf8mb4_general_ci'
    )
    cursor = conn.cursor()

    # Query to fetch rounds for the specified distance
    cursor.execute('''
        SELECT makes, misses, timestamp FROM rounds
        WHERE distance = %s
        ORDER BY timestamp ASC
    ''', (distance,))
    rounds = cursor.fetchall()

    cursor.close()
    conn.close()

    # Prepare data for the two line charts
    timestamps = [row[2] for row in rounds]
    makes = [row[0] for row in rounds]
    misses = [row[1] for row in rounds]

    total_makes = sum(makes)
    total_misses = sum(misses)

    # --- First Line Chart for Makes per Round over Time ---
    fig, ax = plt.subplots()
    ax.plot(timestamps, makes, label='Makes', color='green', marker='o')
    ax.set_xlabel('Time')
    ax.set_ylabel('Makes per Round')
    ax.set_title(f'Makes Over Time at {distance}ft')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Convert first line chart (Makes) to base64 string
    makes_line_chart_img = io.BytesIO()
    plt.savefig(makes_line_chart_img, format='png')
    plt.close(fig)
    makes_line_chart_img.seek(0)
    makes_line_chart_data = base64.b64encode(makes_line_chart_img.getvalue()).decode('utf-8')

    # --- Second Line Chart for Misses per Round over Time ---
    fig, ax = plt.subplots()
    ax.plot(timestamps, misses, label='Misses', color='red', marker='o')
    ax.set_xlabel('Time')
    ax.set_ylabel('Misses per Round')
    ax.set_title(f'Misses Over Time at {distance}ft')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Convert second line chart (Misses) to base64 string
    misses_line_chart_img = io.BytesIO()
    plt.savefig(misses_line_chart_img, format='png')
    plt.close(fig)
    misses_line_chart_img.seek(0)
    misses_line_chart_data = base64.b64encode(misses_line_chart_img.getvalue()).decode('utf-8')

    # --- Pie Chart for Total Makes vs Misses ---
    fig, ax = plt.subplots()
    ax.pie([total_makes, total_misses], labels=['Makes', 'Misses'], autopct='%1.1f%%', startangle=90, colors=['green', 'red'])
    ax.set_title(f'Makes vs Misses at {distance}ft')

    # Convert pie chart to base64 string
    pie_chart_img = io.BytesIO()
    plt.tight_layout()
    plt.savefig(pie_chart_img, format='png')
    plt.close(fig)
    pie_chart_img.seek(0)
    pie_chart_data = base64.b64encode(pie_chart_img.getvalue()).decode('utf-8')

    # Render the template with both line charts and the pie chart
    return render_template('distance_detail.html',
                           distance=distance,
                           total_makes=total_makes,
                           total_misses=total_misses,
                           makes_line_chart_data=makes_line_chart_data,
                           misses_line_chart_data=misses_line_chart_data,
                           pie_chart_data=pie_chart_data)




if __name__ == '__main__':
    init_db()
    app.run()
