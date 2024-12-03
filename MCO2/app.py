from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_

app = Flask(__name__)

# Database setup - SQLite for simplicity, replace with your distributed DB in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///central_db.sqlite3'  # Update for production use
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# Define the model for a record
class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Record {self.name}>"


# Initialize the database
@app.before_first_request
def init_db():
    # Ensure the database is created before the first request
    db.create_all()


# Route for reading all records
@app.route('/')
def index():
    records = Record.query.all()  # Fetch all records from the central node
    return render_template('index.html', records=records)


# Route to insert a record (Create)
@app.route('/insert', methods=['POST'])
def insert():
    name = request.form['name']
    age = request.form['age']

    # Create a new record in the central node (Node 1)
    new_record = Record(name=name, age=age)
    db.session.add(new_record)
    db.session.commit()

    # Simulate replication by inserting into Node 2 and Node 3
    print(f"Inserted record into central node: {new_record}")
    # In a production scenario, you might push this data to Node 2 and Node 3

    return redirect(url_for('index'))


# Route to update a record (Update)
@app.route('/update/<int:id>', methods=['POST'])
def update(id):
    record = Record.query.get(id)
    if record:
        record.name = request.form['name']
        record.age = request.form['age']
        db.session.commit()

        # Simulate updating data in Node 2 and Node 3
        print(f"Updated record in central node: {record}")
        # Update logic to replicate on Node 2 and Node 3 would go here

    return redirect(url_for('index'))


# Route to delete a record (Delete)
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    record = Record.query.get(id)
    if record:
        db.session.delete(record)
        db.session.commit()

        # Simulate deletion in Node 2 and Node 3
        print(f"Deleted record from central node: {record}")
        # Deletion logic to propagate to Node 2 and Node 3 would go here

    return redirect(url_for('index'))


# Simulating distributed nodes for CRUD operations
# (In a real scenario, these would be separate instances communicating with each other)
@app.route('/node1')
def node1():
    return "Node 1 (Central Node) CRUD operations"


@app.route('/node2')
def node2():
    return "Node 2 (Replica Node) CRUD operations"


@app.route('/node3')
def node3():
    return "Node 3 (Replica Node) CRUD operations"


if __name__ == '__main__':
    app.run(debug=True)
