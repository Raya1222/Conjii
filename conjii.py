import requests

def query_gemini(prompt):
    url = "https://generativelanguage.googleapis.com"  
    headers = {
        "Authorization": "Bearer AIzaSyCq2ayJ_paj3pxngOTTFLVWViL_frkzJ2Q",  
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "max_tokens": 100,  # Adjust based on your needs
        "temperature": 0.7  # Adjust for creativity
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("text", "").strip()
    else:
        return f"Error: {response.status_code} - {response.text}"

from gemini_helper import query_gemini

@app.route('/conjugation', methods=['GET', 'POST'])
def conjugation():
    if request.method == 'POST':
        sentence = request.form['sentence']
        tense = request.form['tense']
        
        prompt = f"Conjugate the sentence '{sentence}' into the {tense} tense in French."
        conjugated_sentence = query_gemini(prompt)
        
        return render_template('conjugation.html', result=conjugated_sentence)
    return render_template('conjugation.html')
