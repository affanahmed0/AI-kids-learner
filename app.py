from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from gradio_client import Client
import random

app = Flask(__name__)

# Set secret key for session management
app.secret_key = 'your_secret_key_here'

# Database configuration (using SQLite for simplicity)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    quizzes_completed = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)  # Add games_played field

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
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Game {self.title}>'

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
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['username'] = username
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            return "Invalid credentials. Please try again."
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different username.', 'danger')
            return redirect(url_for('signup'))
        
        # Create a new user
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('login'))

# ChatGPT Route using Hugging Face Spaces
@app.route('/ask_chatgpt', methods=['GET', 'POST'])
def ask_chatgpt():
    if request.method == 'POST':
        prompt = request.form['prompt']  # Get the prompt from the form input

        # Use Gradio client to send the request to Hugging Face Space
        try:
            client = Client("affanahmed011/meta-llama-Meta-Llama-3-8B-Instruct")  # Replace with your space name
            result = client.predict(
                message=prompt,  # Use 'message' instead of 'param_0'
                api_name="/chat"  # Use '/chat' instead of '/predict'
            )
            # Ensure the response is complete
            if isinstance(result, list):
                result = result[0]
            result = result.strip()
        except Exception as e:
            result = f"An error occurred: {e}"

        # Render the response back to the user
        return render_template('ask_chatgpt.html', result=result)

    # On GET request, just display the input form
    return render_template('ask_chatgpt.html')


@app.route('/profile')
def profile():
    if 'username' in session:
        user = User.query.get(session['user_id'])
        return render_template('profile.html', user=user)
    else:
        return redirect(url_for('login'))

@app.route('/progress')
def progress():
    if 'username' in session:
        user = User.query.get(session['user_id'])
        total_quizzes = Quiz.query.filter_by(student_id=user.id).count()
        completed_quizzes = Quiz.query.filter_by(student_id=user.id, score=100).count()  # Assuming 100 is the max score
        total_games = 10  # Example value, replace with actual logic if needed
        played_games = 6  # Example value, replace with actual logic if needed

        progress_data = {
            'total_quizzes': total_quizzes,
            'completed_quizzes': completed_quizzes,
            'total_games': total_games,
            'played_games': played_games
        }
        return render_template('progress.html', progress=progress_data)
    else:
        return redirect(url_for('login'))

@app.route('/quizzes')
def quizzes():
    if 'username' in session:
        user_id = session['user_id']
        quizzes = Quiz.query.filter_by(student_id=user_id).all()  # Filter by logged-in user
        return render_template('quizzes.html', quizzes=quizzes)
    return redirect(url_for('login'))


@app.route('/generate_quiz', methods=['GET', 'POST'])
def generate_quiz():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        topic = request.form['topic']
        difficulty = request.form.get('difficulty', 'medium')

        try:
            client = Client("affanahmed011/meta-llama-Meta-Llama-3-8B-Instruct")
            questions = []
            for i in range(5):  # Generate 5 questions
                prompt = f"Generate a {difficulty} difficulty quiz question on the topic: {topic}."
                result = client.predict(message=prompt, api_name="/chat")
                questions.append(result.strip())

            new_quiz = Quiz(
                title=f"{topic} Quiz",
                difficulty=difficulty,
                questions="\n".join(questions),
                answers="",  # No answers yet
                max_score=100,
                student_id=session['user_id'],
                score=0
            )
            db.session.add(new_quiz)
            db.session.commit()

            return redirect(url_for('take_quiz', quiz_id=new_quiz.id))

        except Exception as e:
            print(f"API Response: {result}")
            return f"An error occurred: {e}"

    return render_template('generate_quiz.html')

@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def take_quiz(quiz_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    questions = quiz.questions.split('\n')

    if request.method == 'POST':
        user_answers = request.form.getlist('answers')
        correct_answers = []
        correct_count = 0

        try:
            client = Client("affanahmed011/meta-llama-Meta-Llama-3-8B-Instruct")
            for question, user_answer in zip(questions, user_answers):
                prompt = f"Question: {question}\nUser Answer: {user_answer}\nWhat is the correct answer?"
                correct_answer = client.predict(message=prompt, api_name="/chat").strip()
                correct_answers.append(correct_answer)
                if user_answer.strip().lower() == correct_answer.strip().lower():
                    correct_count += 1

            quiz.answers = "\n".join(correct_answers)
            db.session.commit()

            score = (correct_count / len(questions)) * 100
            results = zip(questions, user_answers, correct_answers)

            return render_template('quiz_result.html', score=score, correct_count=correct_count, total=len(questions), results=results)

        except Exception as e:
            return f"An error occurred while evaluating the answers: {e}"

    return render_template('take_quiz.html', quiz=quiz, questions=questions)

@app.route('/games')
def games():
    if 'username' in session:
        games = Game.query.all()
        return render_template('games.html', games=games)
    return redirect(url_for('login'))

@app.route('/play_game/<int:game_id>')
def play_game(game_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    game = Game.query.get_or_404(game_id)
    user = User.query.get(session['user_id'])
    user.games_played += 1
    db.session.commit()

    return render_template('play_game.html', game=game)

@app.route('/add_game', methods=['GET', 'POST'])
def add_game():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        new_game = Game(title=title, description=description, user_id=session['user_id'])
        db.session.add(new_game)
        db.session.commit()
        return redirect(url_for('games'))

    return render_template('add_game.html')

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.username = request.form['username']
        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=user)

@app.route('/math_game', methods=['GET', 'POST'])
def math_game():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        answer = int(request.form['answer'])
        correct_answer = int(request.form['correct_answer'])
        if answer == correct_answer:
            flash('Correct! Well done.', 'success')
        else:
            flash(f'Incorrect. The correct answer was {correct_answer}.', 'danger')
        return redirect(url_for('math_game'))

    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    correct_answer = num1 + num2

    return render_template('math_game.html', num1=num1, num2=num2, correct_answer=correct_answer)

if __name__ == '__main__':
    app.run(debug=True)