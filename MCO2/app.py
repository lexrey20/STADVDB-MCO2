from flask import Flask, jsonify, session, request, render_template, redirect
import mysql.connector
import pandas as pd
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = '$K2ToHJP8BK5y4TEZYK@*9JKrMZqY4ZR'  # key for signing session cookies

@app.before_first_request
def clear_session():
    session.clear()  # Clear session data on app startup

# DB conn
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

@app.route('/update_hosts', methods=['POST'])
def update_hosts():
    node_status = request.json.get('nodeStatus')
    if node_status is None:
        return jsonify(message="Node status not provided", error="Bad request"), 400

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
        hosts = session.get('hosts', [])

        if not hosts:
            return jsonify(message="No hosts available in session", error="Hosts list is empty")

        host = next((h for h in hosts if h), None)

        if not host:
            return jsonify(message="No valid hosts found", error="No non-empty host in the list")

        file_path = "imdb.csv"
        df = pd.read_csv(file_path)

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
        hosts = session.get('hosts', [None, None, None])

        for host in hosts:
            if host is None:
                continue
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
            except mysql.connector.Error:
                pass

        if not available_nodes:
            return jsonify(message="No nodes available", error="All connection attempts failed.")

        db_hosts = {i + 1: available_nodes[i] for i in range(len(available_nodes))}

        primary_host = available_nodes[0]
        cnx = mysql.connector.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=primary_host,
            port=DB_PORT,
            database=DB_NAME,
        )
        cursor = cnx.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        total_rows = cursor.fetchone()[0]
        cursor.close()
        cnx.close()

        result = []
        num_hosts = len(available_nodes)
        rows_per_host = total_rows // num_hosts
        remainder = total_rows % num_hosts

        for i, host in enumerate(db_hosts.values()):
            start_id = i * rows_per_host + 1
            end_id = start_id + rows_per_host - 1

            if i < remainder:
                end_id += 1

            print(f"Host: {host}, Query: SELECT * FROM {TABLE_NAME} WHERE id BETWEEN {start_id} AND {end_id}")

            try:
                cnx = mysql.connector.connect(
                    user=DB_USER,
                    password=DB_PASSWORD,
                    host=host,
                    port=DB_PORT,
                    database=DB_NAME,
                )
                set_isolation_level(cnx, "READ COMMITTED")
                cursor = cnx.cursor()

                cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE id BETWEEN {start_id} AND {end_id}")
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

            except mysql.connector.Error as err:
                return jsonify(message=f"Failed to fetch data from host {i+1}", error=str(err))

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
            # RECOVERY IMPLEMENTATION
            available_nodes = []
            hosts = session.get('hosts', [None, None, None])

            # Check available hosts
            for host in hosts:
                if host is None:
                    continue
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
                except mysql.connector.Error:
                    pass

            if not available_nodes:
                return jsonify(message="No nodes available", error="All connection attempts failed.")

            # Insert into all available nodes for redundancy
            for host in available_nodes:
                try:
                    cnx = mysql.connector.connect(
                        user=DB_USER,
                        password=DB_PASSWORD,
                        host=host,
                        port=DB_PORT,
                        database=DB_NAME,
                    )
                    cursor = cnx.cursor()
                    cursor.execute(f"""
                        INSERT INTO {TABLE_NAME} (names, date_x, score, genre, overview, crew, orig_title, status, orig_lang, budget_x, revenue, country)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (names, date_x, score, genre, overview, crew, orig_title, status, orig_lang, budget_x, revenue, country))
                    cnx.commit()
                    cursor.close()
                    cnx.close()
                except mysql.connector.Error as err:
                    return jsonify(message=f"Failed to add data to host {host}", error=str(err))

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