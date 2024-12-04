from flask import Flask, jsonify
import mysql.connector
import pandas as pd

app = Flask(__name__)

# Database connection parameters
DB_USER = "dbadmin"
DB_PASSWORD = "Admin0123"  # Replace with your actual password
DB_HOST = "centraln.mysql.database.azure.com"
DB_PORT = 3306
DB_NAME = "mco2"  # Replace with your actual database name
TABLE_NAME = "imdb"  # Target table name

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


@app.route('/load_data')
def load_data():
    try:
        file_path = "imdb.csv"
        df = pd.read_csv(file_path)
        df = df.head(1000)

        df['date_x'] = pd.to_datetime(df['date_x'], errors='coerce').dt.strftime('%Y-%m-%d')
        df.fillna("N/A", inplace=True)

        cnx = mysql.connector.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
        )
        cursor = cnx.cursor()

        cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME};")

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                names VARCHAR(255),
                date_x DATE,
                score INT,
                genre VARCHAR(255),
                overview TEXT,
                crew TEXT,
                orig_title VARCHAR(255),
                status VARCHAR(255),
                orig_lang VARCHAR(255),
                budget_x INT,
                revenue VARCHAR(255),
                country VARCHAR(2)
            );
        """)

        for _, row in df.iterrows():
            cursor.execute(f"""
                INSERT INTO {TABLE_NAME} (names, date_x, score, genre, overview, crew, orig_title, status, orig_lang, budget_x, revenue, country)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row['names'], row['date_x'], row['score'], row['genre'],
                row['overview'], row['crew'], row['orig_title'],
                row['status'], row['orig_lang'], row['budget_x'], row['revenue'], row['country']
            ))

        cnx.commit()
        cursor.close()
        cnx.close()

        return jsonify(message="Data loaded successfully")
    except Exception as e:
        return jsonify(message="Failed to load data", error=str(e))

@app.route('/read_data')
def read_data():
    try:
        cnx = mysql.connector.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
        )
        cursor = cnx.cursor()

        cursor.execute(f"SELECT * FROM {TABLE_NAME}")

        rows = cursor.fetchall()

        result = ""
        for row in rows:
            result += f"ID: {row[0]}, Name: {row[1]}, Date: {row[2]}, Score: {row[3]}, Genre: {row[4]}, Overview: {row[5]}, Crew: {row[6]}, Orig Title: {row[7]}, Status: {row[8]}, Orig Lang: {row[9]}, Budget: {row[10]}, Revenue: {row[11]}, Country: {row[12]}\n"

        cursor.close()
        cnx.close()

        return result

    except mysql.connector.Error as err:
        return jsonify(message="Failed to read data", error=str(err))


if __name__ == '__main__':
    app.run(debug=True)