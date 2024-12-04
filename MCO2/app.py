from flask import Flask, jsonify, session, request, render_template, redirect
import mysql.connector
import pandas as pd
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # key for signing session cookies

# Database connection parameters
DB_USER = "dbadmin"
DB_PASSWORD = "Admin0123"
DB_HOST = "centraln.mysql.database.azure.com"
DB_PORT = 3306
DB_NAME = "mco2"
TABLE_NAME = "imdb"

app.config['MYSQL_HOST'] = DB_HOST
app.config['MYSQL_PORT'] = DB_PORT
app.config['MYSQL_USER'] = DB_USER
app.config['MYSQL_PASSWORD'] = DB_PASSWORD
app.config['MYSQL_DB'] = DB_NAME

db = MySQL(app)

db_hosts = {1: None, 2: None, 3: None}
@app.route('/')
def hello_world():
    return render_template('index.html')


# Dummy address to replace when nodes are turned off
dummy_address = "dummy.address.com"


@app.route('/update_hosts', methods=['POST'])
def update_hosts():
    node_status = request.json.get('nodeStatus')
    if node_status is None:
        return jsonify(message="Node status not provided", error="Bad request"), 400

    # Set the session data based on the node status
    session['hosts'] = [
        "centraln.mysql.database.azure.com" if node_status['centraln'] else None,
        "node2.mysql.database.azure.com" if node_status['node2'] else None,
        "node3.mysql.database.azure.com" if node_status['node3'] else None
    ]

    return jsonify(message="Hosts updated successfully", hosts=session['hosts'])

@app.route('/get_hosts', methods=['GET'])
def get_hosts():
    # Access the session data
    hosts = session.get('hosts', [])
    return jsonify(hosts=hosts)

@app.route('/configure_nodes')
def check_connection():
    return render_template('manage_nodes.html')

@app.route('/load_data')
def load_data():
    try:
        # Retrieve the list of hosts from the session
        hosts = session.get('hosts', [])

        # Check if there are any available hosts
        if not hosts:
            return jsonify(message="No hosts available in session", error="Hosts list is empty")

        # Use the first available host (ensure it's not empty)
        host = next((h for h in hosts if h), None)

        # If no valid host is found, return an error message
        if not host:
            return jsonify(message="No valid hosts found", error="No non-empty host in the list")

        file_path = "imdb.csv"
        df = pd.read_csv(file_path)
        df = df.head(1500)

        df['date_x'] = pd.to_datetime(df['date_x'], errors='coerce').dt.strftime('%Y-%m-%d')
        df.fillna("N/A", inplace=True)

        cnx = mysql.connector.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=host,
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
        available_nodes = []
        hosts = session.get('hosts', [None, None, None])  # Default to None if hosts not in session

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

        # Assign available nodes to db_hosts
        db_hosts = {}
        for i in range(1, 4):
            if i <= len(available_nodes):
                db_hosts[i] = available_nodes[i - 1]
            else:
                db_hosts[i] = available_nodes[-1]

        # FRAGMENTATION IMPLEMENTATION
        result = []
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
                    result.append({
                        'ID': row[0],
                        'Name': row[1],
                        'Date': row[2],
                        'Score': row[3],
                        'Genre': row[4],
                        'Overview': row[5],
                        'Crew': row[6],
                        'Orig Title': row[7],
                        'Status': row[8],
                        'Orig Lang': row[9],
                        'Budget': row[10],
                        'Revenue': row[11],
                        'Country': row[12]
                    })

                cursor.close()
                cnx.close()

        return render_template('data_display.html', data=result)

    except mysql.connector.Error as err:
        return jsonify(message="Failed to read data", error=str(err))

@app.route('/add_data', methods=['POST', 'GET'])
def add():
    if request.method == 'POST':
        names = request.form['names']
        date_x = request.form['date_x']
        score = request.form['score']
        genre = request.form['genre']
        overview = request.form['overview']
        crew = request.form['crew']
        orig_title = request.form['orig_title']
        status = request.form['status']
        orig_lang = request.form['orig_lang']
        budget_x = request.form['budget_x']
        revenue = request.form['revenue']
        country = request.form['country']

        try:
            cur = db.connection.cursor()
            cur.execute(f"""
                INSERT INTO movies (names, date_x, score, genre, overview, crew, orig_title, status, orig_lang, budget_x, revenue, country)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (names, date_x, score, genre, overview, crew, orig_title, status, orig_lang, budget_x, revenue, country))
            db.connection.commit()
            cur.close()

            return redirect('/')
        except Exception as e:
            return f"Error occurred while adding: {str(e)}"
    else:
        return render_template('add.html')


@app.route('/delete/<string:movie_id>')
def delete(movie_id):
    try:
        cur = db.connection.cursor()
        cur.execute(f"DELETE FROM movies WHERE id = %s", (movie_id,))
        db.connection.commit()
        cur.close()

        return redirect('/')
    except Exception as e:
        return f"Error occurred while deleting: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)