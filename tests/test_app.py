import unittest
import sqlite3
from app import app, init_db
from datetime import datetime


class FlaskTestCase(unittest.TestCase):

    def setUp(self):
        """Setup a new test database and Flask test client before each test."""
        app.config['TESTING'] = True
        app.config['DATABASE'] = ':memory:'  # Use in-memory database for tests
        self.client = app.test_client()

        # Set up an in-memory database for testing
        self.conn = sqlite3.connect(':memory:', detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row  # Enable fetching rows as dictionaries
        self.cursor = self.conn.cursor()

        # Create the 'rounds' table in the in-memory database
        self.cursor.execute('''
            CREATE TABLE rounds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                makes INTEGER NOT NULL,
                misses INTEGER NOT NULL,
                distance INTEGER NOT NULL,
                timestamp DATETIME 
            )
        ''')
        self.conn.commit()

        # Overwrite the get_db function in the app to return this connection
        app.config['TEST_DB_CONN'] = self.conn

    def tearDown(self):
        """Clean up after each test."""
        self.conn.close()

    def test_add_make(self):
        """Test the add_make route to ensure makes are updated correctly."""
        round_data = {'current_round': {'makes': 0, 'misses': 0, 'distance': 20}}
        response = self.client.post('/add_make', json=round_data)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['makes'], 1)

    def test_add_miss(self):
        """Test the add_miss route to ensure misses are updated correctly."""
        round_data = {'current_round': {'makes': 0, 'misses': 0, 'distance': 20}}
        response = self.client.post('/add_miss', json=round_data)
        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['misses'], 1)

    def test_end_round(self):
        """Test the end_round route to ensure a round is saved correctly."""
        round_data = {
            'makes': 5,
            'misses': 2,
            'distance': 20
        }
        response = self.client.post('/end_round', json=round_data)
        self.assertEqual(response.status_code, 200)
        self.cursor.execute("SELECT * FROM rounds WHERE distance = 20")
        round_record = self.cursor.fetchone()
        self.assertIsNotNone(round_record)
        self.assertEqual(round_record[1], 5)  # Check makes
        self.assertEqual(round_record[2], 2)  # Check misses
        self.assertEqual(round_record[3], 20)  # Check distance

    def test_show_rounds(self):
        """Test the 'rounds' route to display rounds correctly."""
        self.cursor.execute('INSERT INTO rounds (makes, misses, distance, timestamp) VALUES (4, 1, 20, ?)',
                            (datetime.now(),))
        self.conn.commit()

        response = self.client.get('/rounds')
        self.assertEqual(response.status_code, 200)

        # Check if the round data is correctly included in the response
        data = response.get_data(as_text=True)
        self.assertIn('4', data)  # Makes
        self.assertIn('1', data)  # Misses
        self.assertIn('20', data)  # Distance

    def test_round_detail(self):
        """Test the round_detail route for displaying round details."""
        self.cursor.execute('INSERT INTO rounds (makes, misses, distance, timestamp) VALUES (8, 2, 25, ?)',
                            (datetime.now(),))
        self.conn.commit()

        # Get the round detail page for the inserted round
        response = self.client.get('/round/1')
        self.assertEqual(response.status_code, 200)

        # Check if the detailed view shows correct data
        data = response.get_data(as_text=True)
        self.assertIn('8', data)  # Makes
        self.assertIn('2', data)  # Misses
        self.assertIn('25', data)  # Distance

    def test_stats(self):
        """Test the stats route for correct statistics calculation."""
        self.cursor.execute('INSERT INTO rounds (makes, misses, distance) VALUES (10, 5, 20)')
        self.cursor.execute('INSERT INTO rounds (makes, misses, distance) VALUES (6, 4, 20)')
        self.cursor.execute('INSERT INTO rounds (makes, misses, distance) VALUES (8, 2, 25)')
        self.conn.commit()

        response = self.client.get('/stats')
        self.assertEqual(response.status_code, 200)

        # Check if the stats page contains correct statistics
        data = response.get_data(as_text=True)
        self.assertIn('20', data)  # Distance 20 ft
        self.assertIn('25', data)  # Distance 25 ft
        self.assertIn('16', data)  # Total putts for 20 ft should be 16 (10+5 + 6+4)
        self.assertIn('80.0%', data)  # Percentage made for 25 ft should be 80%


if __name__ == '__main__':
    unittest.main()
