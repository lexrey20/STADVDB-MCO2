from flask import Flask, jsonify
import mysql.connector
from sqlalchemy import create_engine

app = Flask(__name__)

# Database connection parameters
DB_USER = "dbadmin"
DB_PASSWORD = "Admin0123"  # Replace with your actual password
DB_HOST = "centraln.mysql.database.azure.com"
DB_PORT = 3306
DB_NAME = "mco2"  # Replace with your actual database name

@app.route('/')
def hello_world():
    return 'lex utot'


@app.route('/check_connection')
def check_connection():
    try:
        # Try to connect to the database using mysql.connector
        cnx = mysql.connector.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
        )

        # Check if the connection is successful
        if cnx.is_connected():
            cnx.close()  # Close the connection after checking
            return jsonify(message="Connection successful")
        else:
            return jsonify(message="Connection failed")

    except mysql.connector.Error as err:
        return jsonify(message="Connection failed", error=str(err))


if __name__ == '__main__':
    app.run(debug=True)