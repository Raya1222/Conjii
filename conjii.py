from flask import Flask, render_template, url_for 
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

from flask import Flask, render_template, request
from gemini_integration import generate_content

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db=SQLAlchemy(app)

class Conjugations(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Integer, default=0)
    data_created = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Task {self.id}>'

with app.app_context():
    db.create_all()
        
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/conjugation', methods=["GET", "POST"])
def conjugation():
    if request.method == "POST":
        # Get the verb and tense from the form
        verb = request.form["verb"]
        tense = request.form["tense"]

        # Call the function to get conjugation help
        conjugation_help = get_conjugation_help(verb, tense)

        # Return the conjugation help to be displayed
        return render_template("index.html", conjugation_result=conjugation_help)

    # GET request, just render the form without result
    return render_template("index.html")

def get_conjugation_help(verb: str, tense: str):
    # This function should generate conjugation help using your logic or API
    # For demonstration purposes, we're returning a dummy string
    return f"The verb '{verb}' in {tense} tense is conjugated as: [Example Conjugation]."

@app.route('/worksheet', methods=["POST"])
def worksheet():
    return render_template('conjugation.html')

@app.route('/practice', methods=["POST"])
def practice():
    return render_template('conjugation.html')

@app.route('/lessons', methods=["POST"])
def lessons():
    return render_template('conjugation.html')

if __name__ == "__main__":
    app.run(debug= True)


