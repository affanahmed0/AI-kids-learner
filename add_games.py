from app import app, db, Game

with app.app_context():
    # Create game entries
    games = [
        Game(name='Math Game', difficulty='Easy'),
        Game(name='Math Bingo', difficulty='Medium'),
        Game(name='Fraction Adventure', difficulty='Hard'),
        Game(name='Math Race', difficulty='Medium'),
        Game(name='Shape Math', difficulty='Easy')
    ]

    # Add games to the session and commit
    for game in games:
        db.session.add(game)

    db.session.commit()
    print("Games added successfully!")