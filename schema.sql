DROP TABLE IF EXISTS user;

CREATE TABLE user (
  id INTEGER PRIMARY KEY,
  username VARCHAR(100) UNIQUE,
  email VARCHAR UNIQUE,
  password VARCHAR
);

DROP TABLE IF EXISTS urls;

CREATE TABLE urls (
  id INTEGER PRIMARY KEY,
  original_url TEXT NOT NULL,
  short_url TEXT,
  custom_url TEXT,
  barcode_filename TEXT,
  clicks INTEGER NOT NULL DEFAULT 0,
  created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  user_id INTEGER,
  FOREIGN KEY (user_id) REFERENCES user(id)
);