from flask import Flask, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from gemini_integration import generate_content

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

