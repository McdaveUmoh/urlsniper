import os
import unittest
from flask import Flask
from .. import app
import sqlite3
from ..config import config_dict



class AppTestCase(unittest.TestCase):

    def setUp(self):
        app.config_dict['TESTING'] = True
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome to your application', response.data)

    def test_login(self):
        response = self.app.post('/login', data=dict(username='testuser', password='password'), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Logged in successfully', response.data)
        # Add more assertions to check if the user is redirected to the dashboard or if session data is set correctly

    def test_signup(self):
        response = self.app.post('/signup', data=dict(username='testuser', email='test@example.com', password='password'), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Redirect to dashboard or any other expected response', response.data)
        # Add more assertions to check if the user is registered correctly

    # Add more test cases for other routes and functionalities

    def test_delete_url(self):
        # Create a dummy URL for testing
        with app.app_context():
            conn = get_db_connection()
            conn.execute('INSERT INTO urls (original_url, user_id) VALUES (?, ?)', ('http://example.com', 1))
            conn.commit()
            url_id = conn.lastrowid
            conn.close()

        response = self.app.post(f'/delete/{url_id}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'URL successfully deleted', response.data)
        # Add more assertions to check if the URL is deleted from the database

        # Clean up the dummy URL after testing
        with app.app_context():
            conn = get_db_connection()
            conn.execute('DELETE FROM urls WHERE id = ?', (url_id,))
            conn.commit()
            conn.close()


if __name__ == '__main__':
    unittest.main()
