from flask import Flask, jsonify, render_template_string
import mysql.connector
import pandas as pd

app = Flask(__name__)

# Database connection parameters
DB_USER = "dbadmin"
DB_PASSWORD = "Admin0123"
DB_HOST = "centraln.mysql.database.azure.com"
DB_PORT = 3306
DB_NAME = "mco2"
TABLE_NAME = "imdb"

@app.route('/')
def hello_world():
    homepage_html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Homepage</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                margin-top: 50px;
            }
            button {
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
                margin: 20px;
                border-radius: 5px;
                border: 1px solid #ccc;
            }
            button:hover {
                background-color: #f0f0f0;
            }
        </style>
    </head>
    <body>
        <h1>MCO2 Transaction Management</h1>
        <p>Choose an option below:</p>
        <button onclick="window.location.href='/check_connection'">Check Database Connection</button><br>
        <button onclick="window.location.href='/load_data'">Load Data into Database</button><br>
        <button onclick="window.location.href='/'">Create Record</button><br>
        <button onclick="window.location.href='/read_data'">Read Records</button><br>
        <button onclick="window.location.href='/'">Update Record</button><br>
        <button onclick="window.location.href='/'">Delete Record</button><br>
    </body>
    </html>
    '''
    return render_template_string(homepage_html)

@app.route('/check_connection')
def check_connection():
    try:
        cnx = mysql.connector.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
        )

        if cnx.is_connected():
            cnx.close()
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
        df = df.head(1500)

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

        insert_data = []
        for _, row in df.iterrows():
            insert_data.append((
                row['names'], row['date_x'], row['score'], row['genre'],
                row['overview'], row['crew'], row['orig_title'],
                row['status'], row['orig_lang'], row['budget_x'], row['revenue'], row['country']
            ))

        # batch insert
        cursor.executemany(f"""
            INSERT INTO {TABLE_NAME} (names, date_x, score, genre, overview, crew, orig_title, status, orig_lang, budget_x, revenue, country)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, insert_data)

        cnx.commit()
        cursor.close()
        cnx.close()

        return jsonify(message="Data loaded successfully")
    except Exception as e:
        return jsonify(message="Failed to load data", error=str(e))

def set_isolation_level(cnx, level):
    try:
        cursor = cnx.cursor()
        cursor.execute(f"SET SESSION TRANSACTION ISOLATION LEVEL {level}")
        cursor.close()
    except Exception as e:
        print(f"Error setting isolation level: {e}")

@app.route('/read_data')
def read_data():
    try:
        # RECOVERY IMPLEMENTATION
        # if 1 host is down, other hosts pick up workload
        available_nodes = []
        db_hosts = {1: None, 2: None, 3: None}

        hosts = [
            "dadada.mysql.database.azure.com",
            "dsds.mysql.database.azure.com",
            "node3.mysql.database.azure.com"
        ]

        # test connection to each host and add available nodes to the list
        for host in hosts:
            try:
                cnx = mysql.connector.connect(
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=host,
                    port=DB_PORT,
                    database=DB_NAME,
                )
                cnx.close()
                available_nodes.append(host)
            except mysql.connector.Error as err:
                pass

        if not available_nodes:
            return jsonify(message="Failed to connect to any nodes", error="All connection attempts failed.")

        for i in range(1, 4):
            if i <= len(available_nodes):
                db_hosts[i] = available_nodes[i - 1]
            else:
                db_hosts[i] = available_nodes[-1]

        # FRAGMENTATION IMPLEMENTATION
        # centraln = main node
        # node2 = replica node
        # node3 = replica node
        result = ""
        for i in range(1, 4):
            if db_hosts[i] is not None:
                cnx = mysql.connector.connect(
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=db_hosts[i],
                    port=DB_PORT,
                    database=DB_NAME,
                )
                set_isolation_level(cnx, "READ COMMITTED")  # Set isolation level again for each connection
                cursor = cnx.cursor()

                cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE id BETWEEN {(i-1)*500 + 1} AND {i*500}")
                rows = cursor.fetchall()

                for row in rows:
                    result += f"ID: {row[0]}, Name: {row[1]}, Date: {row[2]}, Score: {row[3]}, Genre: {row[4]}, Overview: {row[5]}, Crew: {row[6]}, Orig Title: {row[7]}, Status: {row[8]}, Orig Lang: {row[9]}, Budget: {row[10]}, Revenue: {row[11]}, Country: {row[12]}\n"

                cursor.close()
                cnx.close()

        return result

    except mysql.connector.Error as err:
        return jsonify(message="Failed to read data", error=str(err))


if __name__ == '__main__':
    app.run(debug=True)