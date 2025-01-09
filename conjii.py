from flask import Flask, render_template, request, url_for
from datetime import datetime
from gemini_integration import generate_content

# DATABASE CODE
import sqlite3

def initializeDB():
    connection = sqlite3.connect("conjii.db")
    cursor = connection.cursor()

    table_query = """
        CREATE TABLE IF NOT EXISTS worksheet (
            id INTEGER PRIMARY KEY NOT NULL,
            date TEXT NOT NULL,
            verb TEXT NOT NULL,
            tense TEXT NOT NULL,
            conjugation_result TEXT NOT NULL
        );
    """

    result = cursor.execute(table_query)
    connection.commit()
    cursor.close()
    connection.close()
# end of initializeDB

def add_data(verb="", tense="", result=""):
    # Get the current date
    current_date = datetime.now()

    # Format the date as YYYY/MM/DD
    formatted_date = current_date.strftime("%Y/%m/%d")

    connection = sqlite3.connect("conjii.db")
    cursor = connection.cursor()

    record_id = None

    # Check if the table has no records, then id will be 0
    if cursor.execute("SELECT COUNT(*) FROM worksheet;").fetchone()[0] == 0:
        record_id = 0
    else:
        # If the table has records, we take the last ID and increase it by one.
        record_id = cursor.execute("SELECT id FROM worksheet ORDER BY id DESC LIMIT 1;").fetchone()[0] + 1
    
    insert_query = """
        INSERT INTO worksheet (id, date, verb, tense, conjugation_result)
        VALUES (?, ?, ?, ?, ?);
    """
    print(formatted_date, record_id)

    cursor.execute(insert_query, (record_id, formatted_date, verb, tense, result))
    connection.commit()
    cursor.close()
    connection.close()
# end of add_data()

def get_data():
    # get_data() returns a list of tuples
    connection = sqlite3.connect("conjii.db")
    cursor = connection.cursor()

    get_query = """SELECT * FROM worksheet;"""
    result = cursor.execute(get_query).fetchall()

    connection.commit()
    cursor.close()
    connection.close()
    return result
# END OF DATABASE CODE

app = Flask(__name__)

@app.route('/')
def index():
    initializeDB()
    print(get_data())
    #add_data(verb="manger", tense="present", result="test")
    return render_template('index.html')

@app.route('/conjugation', methods=['POST', 'GET'])
def conjugation():
    if request.method == "POST":
        # Get verb and tense from the form
        verb = request.form.get("verb", "")
        tense = request.form.get("tense", "")

        try:
            # Generate the conjugation result using Gemini
            prompt = f"Conjugate the verb '{verb}' in the {tense} tense."
            conjugation_result = generate_content(prompt)
        except Exception as e:
            conjugation_result = f"Error generating content: {e}"

        # Save the result to the database
        add_data(verb=verb, tense=tense, result=conjugation_result)

        # Retrieve the stored data (to confirm it saved correctly or fetch it again)
        connection = sqlite3.connect("conjii.db")
        cursor = connection.cursor()
        query = """
            SELECT conjugation_result FROM worksheet
            WHERE verb = ? AND tense = ?
            ORDER BY id DESC LIMIT 1;
        """
        cursor.execute(query, (verb, tense))
        db_result = cursor.fetchone()
        cursor.close()
        connection.close()

        # Use the stored result
        stored_result = db_result[0] if db_result else conjugation_result

        # Render the output page with the stored result
        return render_template("conjugation_output.html", verb=verb, tense=tense, result=stored_result)

    # Render the input page if the method is GET
    return render_template("conjugation_input.html")

@app.route('/worksheet')
def worksheet():
    return render_template('worksheet.html')

@app.route('/practice')
def practice():
    return render_template('practice.html')

@app.route('/lessons')
def lessons():
    return render_template('lessons.html')

if __name__ == "__main__":
    app.run(debug=True)

