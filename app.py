from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from gradio_client import Client

app = Flask(__name__)

# Set secret key for session management
app.secret_key = 'your_secret_key_here'

# Database configuration (using SQLite for simplicity)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///yourdatabase.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    quizzes_completed = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)

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
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
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
        progress_data = {
            'total_quizzes': 20,
            'completed_quizzes': 15,
            'total_games': 10,
            'played_games': 6
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
            # Use Gradio Client to call the API
            client = Client("affanahmed011/meta-llama-Meta-Llama-3-8B-Instruct")
            prompt = f"Generate a {difficulty} difficulty quiz on the topic: {topic}. Include exactly 5 multiple-choice questions with 4 options each and mark the correct answer."
            result = client.predict(message=prompt, api_name="/chat")

            # Parse the API response
            questions = []
            answers = []
            options_list = []
            current_question = None
            current_options = []

            for line in result.splitlines():
                line = line.strip()
                if line.startswith("Q:"):
                    # Save the previous question if it exists
                    if current_question:
                        if len(current_options) == 4:
                            questions.append(current_question)
                            options_list.append(current_options)
                        else:
                            print(f"Error: Incomplete options for question: {current_question}")

                    # Start a new question
                    current_question = line[2:].strip()
                    current_options = []
                elif line.startswith("A:"):
                    answers.append(line[2:].strip())
                elif line.startswith("- "):  # Assuming options start with '- '
                    current_options.append(line[2:].strip())

            # Add the last question
            if current_question and len(current_options) == 4:
                questions.append(current_question)
                options_list.append(current_options)

            # Validate the data
            if len(questions) != 5 or len(answers) != 5 or len(options_list) != 5:
                raise ValueError(f"Expected 5 questions, options, and answers, but got: {len(questions)}, {len(options_list)}, {len(answers)}")

            # Save to the database
            formatted_questions = "\n".join(
                f"{q}\nOptions: {', '.join(opts)}" for q, opts in zip(questions, options_list)
            )
            formatted_answers = "\n".join(answers)

            new_quiz = Quiz(
                title=f"{topic} Quiz",
                difficulty=difficulty,
                questions=formatted_questions,
                answers=formatted_answers,
                max_score=100,
                student_id=session['user_id'],
                score=0
            )
            db.session.add(new_quiz)
            db.session.commit()

            return redirect(url_for('quizzes'))

        except Exception as e:
            # Log error details for debugging
            print(f"API Response: {result}")
            return f"An error occurred: {e}"

    return render_template('generate_quiz.html')


@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def take_quiz(quiz_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    questions = quiz.questions.split("\n")
    correct_answers = quiz.answers.split("\n")

    if len(questions) != len(correct_answers):
        return "Error: Questions and answers do not match!"

    if request.method == 'POST':
        answers = request.form.getlist('answers')
        correct_count = 0

        try:
            client = Client("affanahmed011/meta-llama-Meta-Llama-3-8B-Instruct")
            evaluation_prompts = []

            for question, correct_answer, user_answer in zip(questions, correct_answers, answers):
                evaluation_prompts.append(
                    f"Question: {question}\nUser Answer: {user_answer}\nCorrect Answer: {correct_answer}\nIs the user's answer correct?"
                )

            results = [client.predict(message=prompt, api_name="/chat") for prompt in evaluation_prompts]

            for result in results:
                if "correct" in result.lower():
                    correct_count += 1

            quiz.score = (correct_count / len(questions)) * 100
            db.session.commit()

            return render_template('quiz_result.html', score=quiz.score, correct_count=correct_count, total=len(questions))

        except Exception as e:
            return f"An error occurred while evaluating answers: {e}"

    return render_template('take_quiz.html', quiz=quiz, questions=questions)







@app.route('/games')
def games():
    if 'username' in session:
        games = [
            {'title': 'Math Puzzle', 'description': 'Solve puzzles to unlock levels'},
            {'title': 'Abacus Game', 'description': 'Use abacus to solve arithmetic problems'}
        ]
        return render_template('games.html', games=games)
    return redirect(url_for('login'))

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables

        # Check if test user already exists
        if not User.query.filter_by(username='testuser').first():
            # Create a test user
            test_user = User(username='testuser', password='password123')
            db.session.add(test_user)
            db.session.commit()
            print("Test user 'testuser' has been created.")
        else:
            print("Test user already exists.")

    app.run(debug=True)