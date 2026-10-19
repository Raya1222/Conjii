from flask import Flask, render_template, request, url_for, jsonify, Response
from datetime import datetime
from gemini_integration import generate_content, generate_json, generate_speech, extract_text_from_pdf
import sqlite3
import json
import random

# DATABASE CODE

def get_db_connection():
    conn = sqlite3.connect("conjii.db")
    # Using Row factory allows us to access columns by name later
    conn.row_factory = sqlite3.Row
    return conn

def initializeDB():
    connection = get_db_connection()
    cursor = connection.cursor()

    # 1. Conjugation Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS worksheet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            verb TEXT NOT NULL,
            tense TEXT NOT NULL,
            conjugation_result TEXT NOT NULL
        );
    """)

    # 2. Worksheets Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS generated_worksheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            syllabus_text TEXT NOT NULL,
            generated_content TEXT NOT NULL,
            is_public BOOLEAN DEFAULT 0
        );
    """)
    
    # 3. Practice Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS practice_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            topic TEXT NOT NULL,
            score INTEGER
        );
    """)

    # 4. Roleplay Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roleplay_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            scenario TEXT NOT NULL,
            chat_history TEXT NOT NULL
        );
    """)

    # 5. Dictée Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dictee_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            topic TEXT NOT NULL,
            level TEXT NOT NULL,
            target_text TEXT NOT NULL,
            student_text TEXT,
            score INTEGER
        );
    """)

    connection.commit()
    connection.close()
# end of initializeDB

def add_data(verb="", tense="", result=""):
    # Get the current date
    current_date = datetime.now()

    # Format the date as YYYY/MM/DD
    formatted_date = current_date.strftime("%Y/%m/%d")

    connection = sqlite3.connect("conjii.db")
    cursor = connection.cursor()

    insert_query = """
        INSERT INTO worksheet (date, verb, tense, conjugation_result)
        VALUES (?, ?, ?, ?);
    """

    cursor.execute(insert_query, (formatted_date, verb, tense, result))
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
initializeDB()  # make sure tables exist even if the first visit isn't the home page

@app.route('/')
def index():
    initializeDB()
    return render_template('index.html')

@app.route('/conjugation', methods=['POST', 'GET'])
def conjugation():
    if request.method == "POST":
        # Get verb and tense from the form
        verb = request.form.get("verb", "")
        tense = request.form.get("tense", "")

        try:
            # Generate the conjugation result using Gemini
            prompt = (
                f"Conjugate the French verb '{verb}' in the {tense} tense. "
                "Output ONLY a two-column Markdown table with the header row "
                "'| Pronoun | Conjugation |' covering je, tu, il/elle/on, nous, vous, ils/elles "
                "(or the single form if the tense has only one). "
                "After the table, add one short line in English noting anything irregular. No other text."
            )
            conjugation_result = generate_content(prompt)
            
            # THE FIX: Safety net in case the AI returns an empty/None value
            if conjugation_result is None:
                conjugation_result = "Error: The AI failed to return a response. Check your API key setup."
                
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

@app.route('/worksheet', methods=['GET', 'POST'])
def worksheet():
    if request.method == 'POST':
        level = request.form.get('level', 'intermediate')
        custom_topics = request.form.get('custom_topics', '')
        pdf_file = request.files.get('syllabus_pdf')
        
        pdf_text = ""
        if pdf_file and pdf_file.filename != '':
            pdf_text = extract_text_from_pdf(pdf_file)
            
        combined_context = f"{custom_topics}\n\n{pdf_text}".strip()
        
        prompt = (
            f"Create a comprehensive {level}-level French worksheet. "
            "Format the output entirely in Markdown so it is easy to read and print. "
            "Include the following sections using Markdown headers (##):\n"
            "1. 📖 Vocabulary (A short list of relevant terms)\n"
            "2. 🧠 Grammar Rule (A brief explanation of a relevant concept)\n"
            "3. ✍️ Exercises (Fill-in-the-blank or translation questions)\n"
            "4. 🔑 Answer Key (At the bottom, separated by a horizontal line ---)"
        )
        
        ai_response = generate_content(prompt, syllabus_context=combined_context)
        
        # Save to Database
        formatted_date = datetime.now().strftime("%Y/%m/%d")
        connection = get_db_connection()
        cursor = connection.cursor()
        insert_query = """
            INSERT INTO generated_worksheets (date, syllabus_text, generated_content, is_public)
            VALUES (?, ?, ?, ?);
        """
        cursor.execute(insert_query, (formatted_date, combined_context, ai_response, 0))
        connection.commit()
        connection.close()
        
        return render_template('worksheet_output.html', response=ai_response)
        
    return render_template('worksheet_input.html')



# ---------------------------------------------------------------------------
# PRACTICE
# ---------------------------------------------------------------------------

# (value, label) — the order here is the order shown on the setup page
QUESTION_TYPES = [
    ("fill_blank", "Fill in the blank"),
    ("multiple_choice", "Multiple choice"),
    ("true_false", "True / False"),
    ("short_answer", "Short answer"),
    ("translation", "Translation"),
]
QUESTION_TYPE_RULES = {
    "fill_blank": 'a French sentence containing exactly one blank written as "___", with the base verb/hint in parentheses if helpful. "answer" is the exact word(s) that fill the blank.',
    "multiple_choice": 'a question (in French or English) with exactly 4 options in "options". "answer" must be copied EXACTLY from one of the options.',
    "true_false": 'a statement in French about grammar, vocabulary or meaning that is clearly true or false. "answer" is exactly "Vrai" or "Faux".',
    "short_answer": 'an open question in French that the student answers with a short French sentence. "answer" is one model answer.',
    "translation": 'an English sentence to translate into French (write the instruction in the question, e.g. "Translate: ..."). "answer" is a model French translation.',
}
MAX_QUESTIONS = 30


def split_counts(total, types):
    """Spread `total` questions as evenly as possible across the chosen types."""
    base, extra = divmod(total, len(types))
    shuffled = random.sample(types, len(types))
    return {t: base + (1 if i < extra else 0) for i, t in enumerate(shuffled)}


def clean_questions(raw, allowed_types):
    """Validate the AI output so the quiz page never breaks on a malformed item."""
    items = raw.get("questions", raw) if isinstance(raw, dict) else raw
    cleaned = []
    for q in items if isinstance(items, list) else []:
        if not isinstance(q, dict):
            continue
        qtype = q.get("type")
        question = str(q.get("question", "")).strip()
        answer = str(q.get("answer", "")).strip()
        if qtype not in allowed_types or not question or not answer:
            continue
        item = {"type": qtype, "question": question, "answer": answer,
                "explanation": str(q.get("explanation", "")).strip()}
        if qtype == "multiple_choice":
            options = [str(o).strip() for o in q.get("options", []) if str(o).strip()]
            if answer not in options:
                if len(options) < 2:
                    continue
                options[0] = answer  # make sure the right answer is selectable
            random.shuffle(options)
            item["options"] = options
        if qtype == "true_false":
            item["answer"] = "Vrai" if answer.lower() in ("vrai", "true") else "Faux"
        cleaned.append(item)
    return cleaned


@app.route('/practice', methods=['GET', 'POST'])
def practice():
    if request.method == 'POST':
        practice_focus = request.form.get('practice_focus', 'General French').strip() or 'General French'
        custom_topics = request.form.get('custom_topics', '')
        level = request.form.get('level', 'intermediate')
        pdf_file = request.files.get('syllabus_pdf')

        # How many questions, and which kinds
        try:
            num_questions = int(request.form.get('num_questions', 10))
        except ValueError:
            num_questions = 10
        num_questions = max(1, min(num_questions, MAX_QUESTIONS))

        valid = [t for t, _ in QUESTION_TYPES]
        chosen_types = [t for t in request.form.getlist('question_types') if t in valid] or ["fill_blank"]

        # Timer: minutes -> seconds (0 = no timer)
        timer_minutes = request.form.get('timer_minutes', '').strip()
        timer_seconds = int(timer_minutes) * 60 if timer_minutes.isdigit() else 0

        pdf_text = ""
        if pdf_file and pdf_file.filename != '':
            pdf_text = extract_text_from_pdf(pdf_file)
        combined_context = f"{custom_topics}\n\n{pdf_text}".strip()

        counts = split_counts(num_questions, chosen_types)
        breakdown = "\n".join(f"- {n} x {t}: {QUESTION_TYPE_RULES[t]}" for t, n in counts.items() if n)

        prompt = (
            f"You are a French teacher. Write exactly {num_questions} {level}-level practice questions "
            f"focused on: {practice_focus}.\n\n"
            f"Use exactly this mix of question types:\n{breakdown}\n\n"
            "Mix the types together in a natural order (don't group them all). Make every question distinct.\n"
            "Return JSON of this shape:\n"
            '{"questions": [{"type": "<one of the types above>", "question": "...", '
            '"options": ["..."] (multiple_choice only), "answer": "...", '
            '"explanation": "one short sentence in English explaining the answer"}]}'
        )

        questions, error = [], None
        try:
            questions = clean_questions(generate_json(prompt, syllabus_context=combined_context), chosen_types)
            questions = questions[:num_questions]
            if not questions:
                error = "The AI didn't return any usable questions. Please try again."
        except Exception as e:
            print(f"Practice generation failed: {e}")
            error = "Something went wrong generating your questions. Check your API key and try again."

        # Save to Database
        session_id = None
        if questions:
            formatted_date = datetime.now().strftime("%Y/%m/%d")
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO practice_sessions (date, topic, score) VALUES (?, ?, ?);",
                (formatted_date, practice_focus, 0),
            )
            session_id = cursor.lastrowid
            connection.commit()
            connection.close()

        return render_template('practice_interactive.html', questions=questions, timer=timer_seconds,
                               topic=practice_focus, session_id=session_id, error=error)

    return render_template('practice_input.html', question_types=QUESTION_TYPES, max_questions=MAX_QUESTIONS)


@app.route('/api/practice/grade', methods=['POST'])
def practice_grade():
    """Grades open-ended answers (short answer / translation) with the AI."""
    items = (request.get_json(silent=True) or {}).get("items", [])
    if not items:
        return jsonify(results=[])

    listing = "\n".join(
        f"{i + 1}. [{it.get('type')}] Question: {it.get('question')}\n"
        f"   Model answer: {it.get('expected')}\n"
        f"   Student answer: {it.get('answer') or '(blank)'}"
        for i, it in enumerate(items)
    )
    prompt = (
        "You are a kind but accurate French teacher grading a student's answers.\n"
        "Mark an answer correct if it is a valid, grammatical French answer with the right meaning — "
        "it does NOT need to match the model answer word for word. Small accent slips are OK but mention them.\n\n"
        f"{listing}\n\n"
        'Return JSON: {"results": [{"correct": true/false, "feedback": "one short sentence in English"}]} '
        f"with exactly {len(items)} results in the same order."
    )
    try:
        data = generate_json(prompt, temperature=0.2)
        results = data.get("results", []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"Grading failed: {e}")
        results = []
    return jsonify(results=results)


@app.route('/api/practice/score', methods=['POST'])
def practice_score():
    data = request.get_json(silent=True) or {}
    try:
        connection = get_db_connection()
        connection.execute("UPDATE practice_sessions SET score = ? WHERE id = ?;",
                           (int(data.get("score", 0)), int(data.get("session_id"))))
        connection.commit()
        connection.close()
    except (TypeError, ValueError):
        pass
    return jsonify(ok=True)


# ---------------------------------------------------------------------------
# ROLEPLAY
# ---------------------------------------------------------------------------

LEVEL_GUIDANCE = {
    "beginner": "Use very simple, short sentences (A1–A2), common vocabulary and the present tense.",
    "intermediate": "Use natural everyday French (B1), with a mix of tenses.",
    "advanced": "Use rich, idiomatic French (B2–C1), as a native speaker would.",
}


@app.route('/roleplay', methods=['GET', 'POST'])
def roleplay():
    if request.method == 'POST':
        scenario = request.form.get('scenario', '').strip() or 'Ordering food at a Parisian café'
        mode = 'unscripted' if request.form.get('mode') == 'unscripted' else 'scripted'
        level = request.form.get('level', 'intermediate')
        custom_topics = request.form.get('custom_topics', '')
        pdf_file = request.files.get('syllabus_pdf')

        pdf_text = ""
        if pdf_file and pdf_file.filename != '':
            pdf_text = extract_text_from_pdf(pdf_file)
        # Keep context compact: it's sent back with every conversation turn
        combined_context = f"{custom_topics}\n\n{pdf_text}".strip()[:6000]
        guidance = LEVEL_GUIDANCE.get(level, LEVEL_GUIDANCE["intermediate"])

        scene_shape = ('"setting": "one or two sentences in English setting the scene", '
                       '"ai_role": "short role name in English, e.g. the waiter", '
                       '"user_role": "short role name in English, e.g. a customer"')

        if mode == 'scripted':
            prompt = (
                f"Write a French role-play dialogue for pronunciation practice. Scenario: '{scenario}'. {guidance}\n"
                "The dialogue has 10 to 14 lines, alternating between the AI character (speaker \"ai\") and the "
                "student (speaker \"user\"). The AI speaks first. Keep each line to one or two sentences.\n"
                "Return JSON: {" + scene_shape + ', "lines": [{"speaker": "ai" or "user", '
                '"fr": "the line in French", "en": "English translation"}]}'
            )
        else:
            prompt = (
                f"Set up an improvised French role-play. Scenario: '{scenario}'. {guidance}\n"
                "You will play a character; the student plays the other. Write only YOUR opening line "
                "(one or two sentences in French) that invites the student to respond.\n"
                "Return JSON: {" + scene_shape + ', "opening": {"fr": "your opening line in French", '
                '"en": "English translation"}}'
            )

        ctx = dict(mode=mode, scenario=scenario, level=level, context=combined_context,
                   scene={}, script=[], opening={}, session_id=None, error=None)
        try:
            data = generate_json(prompt, syllabus_context=combined_context)
            ctx["scene"] = {
                "setting": data.get("setting", ""),
                "ai_role": data.get("ai_role") or "Your partner",
                "user_role": data.get("user_role") or "Yourself",
            }
            if mode == 'scripted':
                ctx["script"] = [
                    {"speaker": "user" if l.get("speaker") == "user" else "ai",
                     "fr": str(l.get("fr", "")).strip(), "en": str(l.get("en", "")).strip()}
                    for l in data.get("lines", []) if isinstance(l, dict) and l.get("fr")
                ]
                if not ctx["script"]:
                    raise ValueError("empty script")
            else:
                opening = data.get("opening") or {}
                if not opening.get("fr"):
                    raise ValueError("missing opening line")
                ctx["opening"] = {"fr": opening["fr"], "en": opening.get("en", "")}
        except Exception as e:
            print(f"Roleplay setup failed: {e}")
            ctx["error"] = "Something went wrong setting up the scene. Check your API key and try again."
            return render_template('roleplay_output.html', **ctx)

        # Save to Database (chat history is filled in when the user presses Stop)
        formatted_date = datetime.now().strftime("%Y/%m/%d")
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO roleplay_sessions (date, scenario, chat_history) VALUES (?, ?, ?);",
            (formatted_date, f"[{mode}] {scenario}", json.dumps([])),
        )
        ctx["session_id"] = cursor.lastrowid
        connection.commit()
        connection.close()

        return render_template('roleplay_output.html', **ctx)

    return render_template('roleplay_input.html')


def format_history(history, ai_role, user_role):
    lines = []
    for turn in history[-30:]:  # last 30 turns is plenty of memory
        who = f"YOU ({ai_role})" if turn.get("role") == "ai" else f"STUDENT ({user_role})"
        lines.append(f"{who}: {turn.get('text', '')}")
    return "\n".join(lines)


@app.route('/api/roleplay/chat', methods=['POST'])
def roleplay_chat():
    """One turn of the unscripted conversation: reply to what the student just said."""
    data = request.get_json(silent=True) or {}
    ai_role = data.get("ai_role", "your character")
    user_role = data.get("user_role", "the student")
    level = data.get("level", "intermediate")
    history = data.get("history", [])

    prompt = (
        f"You are role-playing in French as {ai_role}. The student is {user_role}. "
        f"Scenario: '{data.get('scenario', '')}'. {LEVEL_GUIDANCE.get(level, LEVEL_GUIDANCE['intermediate'])}\n\n"
        "Conversation so far (the student's lines come from speech recognition, so ignore missing "
        "punctuation/capitalisation and gracefully interpret small recognition errors):\n"
        f"{format_history(history, ai_role, user_role)}\n\n"
        "Now reply IN CHARACTER to what the student just said. Respond specifically to their words — "
        "react, answer their questions and move the scene forward, usually ending with a question or prompt "
        "so the conversation keeps going. Keep it to 1–2 sentences. If the student speaks English or is "
        "off-topic, gently steer them back in simple French. Never end the conversation yourself.\n"
        "Also, if the student's last line has a clear French grammar or vocabulary mistake, give a brief, "
        "friendly correction in English (e.g. 'Say \"je voudrais\" instead of \"je veux\" — more polite.'). "
        "Otherwise leave it empty.\n"
        'Return JSON: {"reply_fr": "...", "reply_en": "English translation", "correction": "..."}'
    )
    try:
        reply = generate_json(prompt, syllabus_context=data.get("context", ""), temperature=0.9)
        return jsonify(
            reply_fr=reply.get("reply_fr") or "Pardon, vous pouvez répéter ?",
            reply_en=reply.get("reply_en", ""),
            correction=reply.get("correction", "") or "",
        )
    except Exception as e:
        print(f"Roleplay chat failed: {e}")
        return jsonify(reply_fr="Pardon, je n'ai pas bien compris. Vous pouvez répéter ?",
                       reply_en="Sorry, I didn't quite catch that. Could you repeat?", correction="")


@app.route('/api/roleplay/save', methods=['POST'])
def roleplay_save():
    """Called when the user presses Stop: saves the transcript and (optionally) returns feedback."""
    data = request.get_json(silent=True) or {}
    history = data.get("history", [])

    try:
        connection = get_db_connection()
        connection.execute("UPDATE roleplay_sessions SET chat_history = ? WHERE id = ?;",
                           (json.dumps(history, ensure_ascii=False), int(data.get("session_id"))))
        connection.commit()
        connection.close()
    except (TypeError, ValueError):
        pass

    feedback = ""
    student_lines = [t for t in history if t.get("role") == "user"]
    if data.get("want_feedback") and student_lines:
        prompt = (
            f"A {data.get('level', 'intermediate')} French student just finished a spoken role-play "
            f"('{data.get('scenario', '')}'). Here is the transcript (student lines come from speech recognition):\n"
            f"{format_history(history, 'AI', 'student')}\n\n"
            "Write brief, encouraging feedback in English, in Markdown, with three short sections:\n"
            "**What went well** (1–2 bullets), **To polish** (up to 3 bullets, each quoting what they said and "
            "the better French), and **Try next time** (one useful phrase in French with translation). "
            "Keep it under 120 words."
        )
        feedback = generate_content(prompt)
        if feedback.startswith("Error"):
            feedback = ""

    return jsonify(ok=True, feedback=feedback)


# ---------------------------------------------------------------------------
# HUMAN-LIKE AI SPEECH ENDPOINT (/api/tts)
# ---------------------------------------------------------------------------

@app.route('/api/tts', methods=['POST'])
def tts_endpoint():
    """Returns human-like French WAV audio synthesized by Gemini TTS."""
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(error="Missing text"), 400
    voice = data.get("voice") or "Aoede"
    slow = bool(data.get("slow"))
    style = data.get("style") or ""
    try:
        wav_bytes = generate_speech(text, voice=voice, style=style, slow=slow)
        return Response(wav_bytes, mimetype="audio/wav")
    except Exception as e:
        print(f"TTS endpoint fallback triggered: {e}")
        return jsonify(error=str(e)), 502


# ---------------------------------------------------------------------------
# DICTÉE
# ---------------------------------------------------------------------------

DICTEE_LENGTHS = {
    "short": "1 to 2 sentences (around 20–30 words total)",
    "medium": "3 to 4 sentences (around 45–65 words total)",
    "long": "5 to 6 sentences (around 80–110 words total)",
}


@app.route('/dictee', methods=['GET', 'POST'])
def dictee():
    if request.method == 'POST':
        topic = request.form.get('topic', '').strip() or 'Un matin à Paris'
        level = request.form.get('level', 'intermediate')
        length_key = request.form.get('length', 'medium')
        custom_topics = request.form.get('custom_topics', '')
        pdf_file = request.files.get('syllabus_pdf')

        pdf_text = ""
        if pdf_file and pdf_file.filename != '':
            pdf_text = extract_text_from_pdf(pdf_file)
        combined_context = f"{custom_topics}\n\n{pdf_text}".strip()

        guidance = LEVEL_GUIDANCE.get(level, LEVEL_GUIDANCE["intermediate"])
        length_desc = DICTEE_LENGTHS.get(length_key, DICTEE_LENGTHS["medium"])

        prompt = (
            f"Write a cohesive French dictée (dictation passage) on the theme: '{topic}'.\n"
            f"Level: {level} ({guidance}). Length: {length_desc}.\n"
            "Make the passage rich in authentic French spelling, accents, and agreements appropriate for the level.\n"
            "Return JSON of this exact shape:\n"
            '{"title": "Short French title", '
            '"sentences": [{"fr": "Sentence in French.", "en": "English translation."}], '
            '"full_text": "All French sentences joined together", '
            '"english_translation": "All English sentences joined together"}'
        )

        ctx = dict(topic=topic, level=level, title=topic, sentences=[], full_text="",
                   english_translation="", session_id=None, error=None)
        try:
            data = generate_json(prompt, syllabus_context=combined_context)
            sentences = [
                {"fr": str(s.get("fr", "")).strip(), "en": str(s.get("en", "")).strip()}
                for s in (data.get("sentences") or [])
                if isinstance(s, dict) and str(s.get("fr", "")).strip()
            ]
            full_text = str(data.get("full_text") or " ".join(s["fr"] for s in sentences)).strip()
            if not sentences and full_text:
                sentences = [{"fr": full_text, "en": str(data.get("english_translation", "")).strip()}]
            if not full_text:
                raise ValueError("Empty dictée generated")

            ctx["title"] = str(data.get("title") or topic).strip()
            ctx["sentences"] = sentences
            ctx["full_text"] = full_text
            ctx["english_translation"] = str(
                data.get("english_translation") or " ".join(s["en"] for s in sentences if s["en"])
            ).strip()
        except Exception as e:
            print(f"Dictée generation failed: {e}")
            ctx["error"] = "Something went wrong composing your dictée. Check your API key and try again."
            return render_template('dictee_output.html', **ctx)

        formatted_date = datetime.now().strftime("%Y/%m/%d")
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO dictee_sessions (date, topic, level, target_text, student_text, score) VALUES (?, ?, ?, ?, ?, ?);",
            (formatted_date, topic, level, ctx["full_text"], "", 0),
        )
        ctx["session_id"] = cursor.lastrowid
        connection.commit()
        connection.close()

        return render_template('dictee_output.html', **ctx)

    return render_template('dictee_input.html')


@app.route('/api/dictee/grade', methods=['POST'])
def dictee_grade():
    """Grades a French dictée from either typed text or a photo of handwritten paper."""
    target_text = (request.form.get("target_text") or "").strip()
    level = (request.form.get("level") or "intermediate").strip()
    mode = (request.form.get("mode") or "type").strip()
    session_id = request.form.get("session_id")

    if not target_text:
        return jsonify(error="Missing target dictée text."), 400

    image_part = None
    student_text = (request.form.get("student_text") or "").strip()

    if mode == "upload":
        img_file = request.files.get("handwriting_image")
        if not img_file or img_file.filename == "":
            return jsonify(error="Please upload a photo of your handwritten page."), 400
        img_bytes = img_file.read()
        if not img_bytes:
            return jsonify(error="The uploaded image file was empty."), 400
        mime = img_file.mimetype or "image/jpeg"
        image_part = {"mime_type": mime, "data": img_bytes}

        prompt = (
            "You are a French teacher grading a student's handwritten French dictée (dictation).\n"
            f"Original dictée passage read aloud:\n\"\"\"{target_text}\"\"\"\n\n"
            "Step 1: Look carefully at the attached photo of the student's handwritten page and transcribe "
            "EXACTLY what the student wrote in French into `transcribed_text`. Do NOT auto-correct their "
            "spelling, accents, or agreements during transcription — preserve their exact mistakes so we can grade fairly.\n"
            "Step 2: Compare their writing against the original passage and grade it on a 0–100 scale (`score`), "
            "accounting for spelling (orthographe), accents, silent letters, verb endings, and gender/number agreements (accords).\n"
            "Step 3: List each specific mistake in `mistakes` with `category` (e.g. 'Accent', 'Orthographe', 'Accord', 'Conjugaison', 'Mot manquant'), "
            "`student` (what they wrote), `correct` (the expected word/phrase), and a short `explanation` in English.\n"
            "Step 4: Write a warm, constructive `feedback` paragraph in English (2–3 sentences).\n"
            'Return JSON: {"score": 0-100, "transcribed_text": "...", '
            '"mistakes": [{"category": "...", "student": "...", "correct": "...", "explanation": "..."}], '
            '"feedback": "..."}'
        )
    else:
        if not student_text:
            return jsonify(error="Please type what you heard before grading."), 400
        prompt = (
            "You are a French teacher grading a student's typed French dictée (dictation).\n"
            f"Original dictée passage read aloud:\n\"\"\"{target_text}\"\"\"\n\n"
            f"Student's transcription:\n\"\"\"{student_text}\"\"\"\n\n"
            "Compare the student's transcription against the original passage and grade it on a 0–100 scale (`score`), "
            "evaluating spelling (orthographe), accents, verb endings, and gender/number agreements (accords).\n"
            "List each specific mistake in `mistakes` with `category` (e.g. 'Accent', 'Orthographe', 'Accord', 'Conjugaison', 'Mot manquant'), "
            "`student` (what they wrote), `correct` (the expected word/phrase), and a short `explanation` in English.\n"
            "Write a warm, constructive `feedback` paragraph in English (2–3 sentences).\n"
            'Return JSON: {"score": 0-100, "transcribed_text": "...", '
            '"mistakes": [{"category": "...", "student": "...", "correct": "...", "explanation": "..."}], '
            '"feedback": "..."}'
        )

    try:
        result = generate_json(prompt, temperature=0.2, image_part=image_part)
        score = int(max(0, min(100, round(float(result.get("score", 0))))))
        transcribed = str(result.get("transcribed_text") or student_text).strip()
        mistakes = result.get("mistakes") if isinstance(result.get("mistakes"), list) else []
        feedback = str(result.get("feedback") or "").strip()
    except Exception as e:
        print(f"Dictée grading failed: {e}")
        return jsonify(error="Could not grade your dictée right now. Please try again."), 500

    try:
        if session_id:
            connection = get_db_connection()
            connection.execute(
                "UPDATE dictee_sessions SET student_text = ?, score = ? WHERE id = ?;",
                (transcribed, score, int(session_id)),
            )
            connection.commit()
            connection.close()
    except (TypeError, ValueError):
        pass

    return jsonify(
        score=score,
        transcribed_text=transcribed,
        mistakes=mistakes,
        feedback=feedback,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)

