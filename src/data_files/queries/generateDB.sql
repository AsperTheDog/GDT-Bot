CREATE TABLE IF NOT EXISTS items (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    type VARCHAR CHECK( type IN ('videogame','boardgame','book') ) NOT NULL,
    copies INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS boardgames (
    id INTEGER NOT NULL PRIMARY KEY,
    bgg_id INTEGER,
    play_difficulty INTEGER,
    learn_difficulty INTEGER,
    min_players INTEGER,
    max_players INTEGER,
    length INTEGER,
    FOREIGN KEY (id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS videogames (
    id INTEGER NOT NULL PRIMARY KEY,
    difficulty INTEGER,
    platform INTEGER,
    min_players INTEGER,
    max_players INTEGER,
    length INTEGER,
    FOREIGN KEY (id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER NOT NULL PRIMARY KEY,
    author VARCHAR,
    pages INTEGER,
    tags VARCHAR,
    FOREIGN KEY (id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS borrows (
    user INTEGER NOT NULL,
    item INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    retrieval_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    register_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    planned_return DATETIME,
    returned DATETIME,
    reminded BOOLEAN DEFAULT FALSE,
    PRIMARY KEY(user, item, retrieval_date)
);

CREATE TABLE IF NOT EXISTS suggestions (
    name VARCHAR NOT NULL PRIMARY KEY,
    type VARCHAR NOT NULL,
    likes INTEGER DEFAULT 1,
    proposer INTEGER NOT NULL,
    proposed_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);