from flask import Flask, render_template, url_for 
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

from flask import Flask, render_template, request, jsonify
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

@app.route('/conjugation', methods=["POST"])
def conjugation():
    data = request.get_json()
    verb = data["verb"]
    tense = data["tense"]

    # Get conjugation help from Gemini integration
    conjugation_help = get_conjugation_help(verb, tense)

    # Return the result as JSON
    return jsonify({"result": conjugation_help})

def get_conjugation_help(verb: str, tense: str):
    """
    Get conjugation help for a verb in a specific tense using Gemini API.
    """
    prompt = f"Conjugate the verb '{verb}' in the {tense} tense in French. Provide examples."
    conjugation_help = generate_content(prompt)
    
    if conjugation_help:
        return conjugation_help
    else:
        return "Sorry, we couldn't generate conjugation help at this time."

@app.route('/worksheet')
def worksheet():
    return render_template('conjugation.html')

@app.route('/practice')
def practice():
    return render_template('conjugation.html')

@app.route('/lessons')
def lessons():
    return render_template('conjugation.html')

if __name__ == "__main__":
    app.run(debug= True)


