CREATE TABLE IF NOT EXISTS items (
    id INTEGER NOT NULL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    length INTEGER,
    description TEXT NOT NULL DEFAULT 'No description provided',
    thumbnail TEXT DEFAULT 'https://i.imgur.com/OJhoTqu.png',
    type TEXT CHECK( type IN ('videogame','boardgame','book') ) NOT NULL,
    copies INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER NOT NULL,
    category TEXT NOT NULL,
    PRIMARY KEY(id, category),
    FOREIGN KEY (id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS boardgames (
    id INTEGER NOT NULL PRIMARY KEY,
    min_players INTEGER NOT NULL,
    max_players INTEGER NOT NULL,
    bgg_id INTEGER DEFAULT -1,
    bgg_rating REAL DEFAULT -1.0,
    bgg_average_rating REAL DEFAULT -1.0,
    bgg_rank INTEGER DEFAULT -1,
    learn_difficulty INTEGER DEFAULT 0,
    play_difficulty INTEGER DEFAULT 0,
    FOREIGN KEY (id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS videogames (
    id INTEGER NOT NULL PRIMARY KEY,
    min_players INTEGER NOT NULL,
    max_players INTEGER NOT NULL,
    playing_time INTEGER NOT NULL,
    difficulty INTEGER DEFAULT 0,
    platform INTEGER DEFAULT 0,
    FOREIGN KEY (id) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER NOT NULL PRIMARY KEY,
    author TEXT NOT NULL,
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

CREATE TABLE IF NOT EXISTS interests (
    user INTEGER NOT NULL,
    item INTEGER NOT NULL,
    declared_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(user, item),
    FOREIGN KEY (item) REFERENCES items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS suggestions (
    name TEXT NOT NULL PRIMARY KEY,
    type TEXT NOT NULL,
    likes INTEGER DEFAULT 1,
    proposer INTEGER NOT NULL,
    proposed_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);