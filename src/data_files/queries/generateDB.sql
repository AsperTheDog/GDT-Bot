CREATE TABLE IF NOT EXISTS boardgames (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    play_difficulty INTEGER,
    learn_difficulty INTEGER,
    min_players INTEGER,
    max_players INTEGER,
    copies INTEGER DEFAULT 1,
    length INTEGER
);

CREATE TABLE IF NOT EXISTS videogames (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    difficulty INTEGER,
    platform INTEGER,
    min_players INTEGER,
    max_players INTEGER,
    copies INTEGER DEFAULT 1,
    length INTEGER
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR NOT NULL,
    author VARCHAR,
    pages INTEGER,
    genre VARCHAR,
    abstract VARCHAR,
    copies INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS borrows (
    user INTEGER NOT NULL,
    item INTEGER NOT NULL,
    type VARCHAR NOT NULL,
    amount INTEGER NOT NULL,
    retrieval_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    register_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    planned_return DATETIME,
    returned DATETIME,
    PRIMARY KEY(user, item, type)
);

CREATE TABLE IF NOT EXISTS suggestions (
    name VARCHAR NOT NULL PRIMARY KEY,
    type VARCHAR NOT NULL,
    likes INTEGER DEFAULT 1,
    message INTEGER NOT NULL
);