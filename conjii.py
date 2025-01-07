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
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
# db = SQLAlchemy(app)

# class Conjugations(db.Model):
    # id = db.Column(db.Integer, primary_key=True)
    # verb = db.Column(db.String(100), nullable=False)
    # tense = db.Column(db.String(50), nullable=False)
    # conjugation_result = db.Column(db.Text, nullable=False)
    # data_created = db.Column(db.DateTime, default=datetime.utcnow)

    # def __repr__(self):
    #     return f'<Conjugation {self.id}>'

# with app.app_context():
#     db.create_all()

@app.route('/')
def index():
    initializeDB()
    print(get_data())
    #add_data(verb="manger", tense="present", result="test")
    return render_template('index.html')

@app.route('/conjugation', methods=['POST','GET'])
#def conjugation_result():
def conjugation():
    if request.method == "POST":
        # Get verb and tense from the form
        verb1 = request.form.get("verb", "")
        tense1 = request.form.get("tense", "")

        #print(db)

        try:
            prompt = f"Conjugate the verb '{verb1}' in the {tense1} tense."
            conjugation_help = repr(generate_content(prompt))
        except Exception as e:
            conjugation_help = f"Error generating content: {e}"
        
        print(conjugation_help)

        # new_conjugation = Conjugations(verb=verb1, tense=tense1, conjugation_result=conjugation_help)
        # db.session.add(new_conjugation)
        # db.session.commit()

        # Placeholder: Add logic to conjugate the verb based on the tense
        # For now, let's assume we have a function `conjugate_verb`
        #result = conjugate_verb(verb1, tense1)

        #Example result for demonstration purposes
        result = f"Conjugated form of '{verb1}' in '{tense1}' tense."

        # Render the output page with the result
        return render_template("conjugation_output.html", verb=verb1, tense=tense1, result=result)

    # Render the input page if the method is GET
    return render_template("conjugation_input.html")

    # if request.method == "POST":
    #     verb = request.form.get("verb", "")
    #     tense = request.form.get("tense", "")
    #     print(verb, tense)
    #     return render_template()
    # return render_template("conjugation_input.html")


    # if request.method == "POST":
    #     verb = request.form.get("verb", "")
    #     tense = request.form.get("tense", "")

    #     try:
    #         prompt = f"Conjugate the verb '{verb}' in the {tense} tense."
    #         conjugation_help = generate_content(prompt)
    #     except Exception as e:
    #         conjugation_help = f"Error generating content: {e}"

    #     new_conjugation = Conjugations(verb=verb, tense=tense, conjugation_result=conjugation_help)
    #     db.session.add(new_conjugation)
    #     db.session.commit()

    #     return render_template("conjugation_output.html", verb=verb, tense=tense, conjugation_result=conjugation_help)
    #else:
    #    return render_template("conjugation_output.html", verb=verb, tense=tense, conjugation_result=conjugation_help)

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

