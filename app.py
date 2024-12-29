from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from gradio_client import Client
import random
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps  # Add this import at the top
from quiz_bank import quiz_bank
import logging

app = Flask(__name__)

# Set secret key for session management
app.secret_key = 'your_secret_key_here'

# Database configuration (using SQLite for simplicity)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

logging.basicConfig(level=logging.INFO) 

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    quizzes_completed = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)  # Add games_played field
    math_game_score = db.Column(db.Integer, default=0)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    questions = db.Column(db.Text)  # Store questions as text
    answers = db.Column(db.Text)    # Store answers as text
    max_score = db.Column(db.Integer, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    score = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Quiz {self.title}>'

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    

    def __repr__(self):
        return f'<Game {self.name}>'

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = username
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if the username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists. Please choose a different one.', 'danger')
            return redirect(url_for('signup'))
        
        # Create a new user with hashed password using pbkdf2:sha256
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

# ChatGPT Route using Hugging Face Spaces
@app.route('/ask_Galaxy', methods=['GET', 'POST'])
def ask_Galaxy():
    if request.method == 'POST':
        prompt = request.form['prompt']  # Get the user's input question

        structured_prompt = (
            f"You are a friendly AI tutor for kids. Please answer clearly and fully:\n{prompt}"
        )

        try:
            client = Client("affanahmed011/meta-llama-Meta-Llama-3-8B-Instruct")
            result = client.predict(
                message=structured_prompt,
                api_name="/chat"
            )

            # Log raw response to ensure completeness
            logging.info(f"Raw response: {result}")

            # Ensure response is a clean string
            if isinstance(result, list):
                result = " ".join(result).strip()
            result = result.strip()

            if not result:
                result = "I'm sorry, I couldn't generate a complete answer. Please try rephrasing your question."

        except Exception as e:
            logging.error(f"Error during API call: {e}")
            result = "We encountered an issue processing your request. Please try again later."

        # Render the result to the user
        return render_template('ask_Galaxy.html', result=result)

    return render_template('ask_Galaxy.html')


# Add login_required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session['username'])

@app.route('/profile')
@login_required
def profile():
    user = db.session.get(User, session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/progress')
@login_required
def progress():
    user = db.session.get(User, session['user_id'])

    # Fetch quizzes and their scores
    quizzes = Quiz.query.filter_by(student_id=user.id).all()
    quiz_scores = [{'title': quiz.title, 'score': quiz.score} for quiz in quizzes]

    # Fetch games and their scores
    games_played = user.games_played if user.games_played is not None else 0
    math_game_score = user.math_game_score if user.math_game_score is not None else 0

    progress_data = {
        'total_quizzes': len(quizzes),
        'completed_quizzes': sum(1 for quiz in quizzes if quiz.score == 100),
        'quiz_scores': quiz_scores,
        'total_games': games_played,
        'math_game_score': math_game_score
    }

    return render_template('progress.html', progress=progress_data)

def get_quiz_data(topic):
    topic = topic.lower()

    if topic not in quiz_bank:
        return None  # Return None if topic doesn't exist
    
    quizzes = quiz_bank[topic]
    if not quizzes:
        return None  # Return None if no quizzes are available for the topic
    
    # Randomly select a quiz
    quiz = random.choice(quizzes)
    if not quiz['questions'] or not quiz['answers']:
        return None  # Return None if questions or answers are missing
    
    return quiz

@app.route('/quizzes')
@login_required
def quizzes():
    user_id = session['user_id']
    quizzes = Quiz.query.filter_by(student_id=user_id).all()  # Filter by logged-in user
    return render_template('quizzes.html', quizzes=quizzes)

@app.route('/generate_quiz', methods=['GET', 'POST'])
@login_required
def generate_quiz():
    if request.method == 'POST':
        topic = request.form['topic']
        difficulty = request.form.get('difficulty', 'medium')

        # Fetch quiz data using helper function
        quiz_data = get_quiz_data(topic)

        if not quiz_data:
            flash(f"No quizzes available for the topic '{topic}'. Please try another topic.", "danger")
            return redirect(url_for('generate_quiz'))

        # Extract questions and answers
        questions = quiz_data['questions']
        answers = quiz_data['answers']

        try:
            # Save quiz to the database
            new_quiz = Quiz(
                title=f"{topic} Quiz",
                difficulty=difficulty,
                questions="\n\n".join(questions),
                answers="\n".join(answers),
                max_score=100,
                student_id=session['user_id'],
                score=0
            )
            db.session.add(new_quiz)
            db.session.commit()

            flash("Quiz generated successfully!", "success")
            return redirect(url_for('take_quiz', quiz_id=new_quiz.id))

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while saving the quiz: {e}", "danger")
            return redirect(url_for('generate_quiz'))

    return render_template('generate_quiz.html')


@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def take_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id) or abort(404)
    questions = quiz.questions.split('\n\n')  # Split questions by double newlines for multiple-choice format

    if request.method == 'POST':
        user_answers = []
        for i in range(1, len(questions) + 1):
            user_answers.append(request.form.get(f'answers_{i}').strip().lower())  # Collect answers from the form

        correct_answers = [answer.strip().lower() for answer in quiz.answers.split('\n')]
        correct_count = 0

        # Validate user answers
        for user_answer, correct_answer in zip(user_answers, correct_answers):
            if user_answer == correct_answer:
                correct_count += 1

        # Calculate the score
        score = (correct_count / len(questions)) * 100
        quiz.score = score
        db.session.commit()

        # Update user's quizzes_completed
        user = db.session.get(User, session['user_id'])
        user.quizzes_completed = (user.quizzes_completed or 0) + 1
        db.session.commit()

        results = zip(questions, user_answers, correct_answers)  # Pair questions, user answers, and correct answers

        return render_template(
            'quiz_result.html',
            score=score,
            correct_count=correct_count,
            total=len(questions),
            results=results
        )

    return render_template('take_quiz.html', quiz=quiz, questions=questions)


# START OF GAME ROUTE
@app.route('/games')
@login_required
def games():
    games = Game.query.all()
    print(games)
    return render_template('games.html', games=games)

# Math Game Route
@app.route('/play_math_game', methods=['GET', 'POST'])
@login_required
def play_math_game():
    if 'math_game' not in session:
        session['math_game'] = {
            'score': 0,
            'questions_asked': 0,
            'question_limit': 5
        }

    game_data = session['math_game']

    if request.method == 'POST':
        question = session.get('math_question')
        correct_answer = session.get('math_answer')
        user_answer = request.form.get('answer', type=int)

        game_data['questions_asked'] += 1

        if user_answer == correct_answer:
            game_data['score'] += 1
            flash('Correct! Well done!', 'success')
        else:
            flash(f'Incorrect. The correct answer was {correct_answer}.', 'danger')

        session['math_game'] = game_data

        if game_data['questions_asked'] >= game_data['question_limit']:
            return redirect(url_for('math_game_results'))

        return redirect(url_for('play_math_game'))

    num1 = random.randint(1, 20)
    num2 = random.randint(1, 20)
    operators = ['+', '-', '*']
    operator = random.choice(operators)
    question = f"{num1} {operator} {num2}"
    correct_answer = eval(question)

    session['math_question'] = question
    session['math_answer'] = correct_answer

    return render_template('play_math_game.html', question=question)


# Math Bingo Game
@app.route('/play_math_bingo', methods=['GET', 'POST'])
@login_required
def play_math_bingo():
    if 'bingo_game' not in session:
        session['bingo_game'] = {
            'score': 0,
            'questions_asked': 0,
            'bingo_card': random.sample(range(1, 50), 25),  # Generate a random bingo card
            'question_limit': 5,
            'answered': []
        }

    game_data = session['bingo_game']
    bingo_card = game_data['bingo_card']
    bingo_row = [
        bingo_card[i:i+5] for i in range(0, 25, 5)
    ]  # Creating a 5x5 bingo grid

    if request.method == 'POST':
        question = session.get('bingo_question')
        correct_answer = session.get('bingo_answer')
        user_answer = request.form.get('answer', type=int)

        game_data['questions_asked'] += 1

        if user_answer == correct_answer:
            game_data['score'] += 1
            game_data['answered'].append(user_answer)  # Mark the number as answered
            flash('Correct! Well done!', 'success')
        else:
            flash(f'Incorrect. The correct answer was {correct_answer}.', 'danger')

        session['bingo_game'] = game_data

        if game_data['questions_asked'] >= game_data['question_limit']:
            return redirect(url_for('bingo_game_results'))

        return redirect(url_for('play_math_bingo'))

    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    question = f"What is {num1} + {num2}?"
    correct_answer = num1 + num2

    session['bingo_question'] = question
    session['bingo_answer'] = correct_answer

    return render_template('play_math_bingo.html', bingo_card=bingo_row, question=question)


# Fraction Adventure Game
@app.route('/play_fraction_adventure', methods=['GET', 'POST'])
@login_required
def play_fraction_adventure():
    if 'fraction_game' not in session:
        session['fraction_game'] = {
            'score': 0,
            'questions_asked': 0,
            'question_limit': 5
        }

    game_data = session['fraction_game']

    if request.method == 'POST':
        question = session.get('fraction_question')
        correct_answer = session.get('fraction_answer')
        user_answer = request.form.get('answer', type=float)

        game_data['questions_asked'] += 1

        if user_answer == correct_answer:
            game_data['score'] += 1
            flash('Correct! Well done!', 'success')
        else:
            flash(f'Incorrect. The correct answer was {correct_answer}.', 'danger')

        session['fraction_game'] = game_data

        if game_data['questions_asked'] >= game_data['question_limit']:
            return redirect(url_for('fraction_game_results'))

        return redirect(url_for('play_fraction_adventure'))

    num1 = random.randint(1, 10)
    num2 = random.randint(2, 10)
    question = f"What is {num1} / {num2}?"
    correct_answer = round(num1 / num2, 2)

    session['fraction_question'] = question
    session['fraction_answer'] = correct_answer

    return render_template('play_fraction_adventure.html', question=question)


# Math Race Game
@app.route('/play_math_race', methods=['GET', 'POST'])
@login_required
def play_math_race():
    if 'race_game' not in session:
        session['race_game'] = {
            'score': 0,
            'questions_asked': 0,
            'question_limit': 5,
            'position': 0  # Starting position in the race
        }

    game_data = session['race_game']

    if request.method == 'POST':
        question = session.get('race_question')
        correct_answer = session.get('race_answer')
        user_answer = request.form.get('answer', type=int)

        game_data['questions_asked'] += 1

        if user_answer == correct_answer:
            game_data['score'] += 1
            game_data['position'] += 1  # Move forward in the race
            flash('Correct! Keep going!', 'success')
        else:
            flash(f'Incorrect. The correct answer was {correct_answer}.', 'danger')

        session['race_game'] = game_data

        if game_data['questions_asked'] >= game_data['question_limit']:
            return redirect(url_for('race_game_results'))

        return redirect(url_for('play_math_race'))

    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    question = f"What is {num1} + {num2}?"
    correct_answer = num1 + num2

    session['race_question'] = question
    session['race_answer'] = correct_answer

    return render_template('play_math_race.html', question=question, position=game_data['position'])


# Shape Math Game
@app.route('/play_shape_math', methods=['GET', 'POST'])
@login_required
def play_shape_math():
    if 'shape_game' not in session:
        session['shape_game'] = {
            'score': 0,
            'questions_asked': 0,
            'question_limit': 5
        }

    game_data = session['shape_game']

    if request.method == 'POST':
        question = session.get('shape_question')
        correct_answer = session.get('shape_answer')
        user_answer = request.form.get('answer', type=int)

        game_data['questions_asked'] += 1

        if user_answer == correct_answer:
            game_data['score'] += 1
            flash('Correct! Well done!', 'success')
        else:
            flash(f'Incorrect. The correct answer was {correct_answer}.', 'danger')

        session['shape_game'] = game_data

        if game_data['questions_asked'] >= game_data['question_limit']:
            return redirect(url_for('shape_game_results'))

        return redirect(url_for('play_shape_math'))

    # Generate random shape problems
    shape = random.choice(['square', 'rectangle', 'triangle'])
    if shape == 'square':
        side = random.randint(1, 10)
        question = f"What is the area of a square with side length {side}?"
        correct_answer = side ** 2
    elif shape == 'rectangle':
        length = random.randint(1, 10)
        width = random.randint(1, 10)
        question = f"What is the area of a rectangle with length {length} and width {width}?"
        correct_answer = length * width
    else:
        base = random.randint(1, 10)
        height = random.randint(1, 10)
        question = f"What is the area of a triangle with base {base} and height {height}?"
        correct_answer = 0.5 * base * height

    session['shape_question'] = question
    session['shape_answer'] = correct_answer

    return render_template('play_shape_math.html', question=question)


# Math Bingo Results
@app.route('/bingo_game_results')
@login_required
def bingo_game_results():
    game_data = session.get('bingo_game', {})
    score = game_data.get('score', 0)
    question_limit = game_data.get('question_limit', 5)

    user = db.session.get(User, session['user_id'])
    user.games_played = (user.games_played or 0) + 1
    user.math_game_score = max(user.math_game_score, score)

    db.session.commit()

    session.pop('bingo_game', None)

    return render_template('bingo_game_results.html', score=score, total=question_limit)






# END OF GAME 

# EDIT PROFILE ROUTE START
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = db.session.get(User, session['user_id'])

    if request.method == 'POST':
        user.username = request.form['username']
        user.email = request.form['email']
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=user)
# EDIT PROFILE END



if __name__ == '__main__':
    app.run(debug=True)
