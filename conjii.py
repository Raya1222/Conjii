from flask import Flask, render_template, url_for 
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

from flask import Flask
from config import GEMINI_API_KEY, GEMINI_API_URL
import requests

GEMINI_API_KEY = "AIzaSyCq2ayJ_paj3pxngOTTFLVWViL_frkzJ2Q"
GEMINI_API_URL = "https://generativelanguage.googleapis.com"

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

@app.route('/conjugation')
def conjugation():
    return render_template('conjugation.html')

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


