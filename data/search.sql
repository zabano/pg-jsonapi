TRUNCATE articles_ts;
INSERT INTO articles_ts (article_id, tsvector)
SELECT articles.id,
       setweight(to_tsvector(articles.title), 'A') ||
       setweight(to_tsvector(author_name.last), 'B') ||
       setweight(to_tsvector(author_name.first), 'B') ||
       setweight(to_tsvector(articles.body), 'C')
FROM articles
         JOIN users author ON articles.author_id = author.id
         JOIN user_names author_name ON author.id = author_name.id;

TRUNCATE users_ts;
INSERT INTO users_ts (user_id, tsvector)
SELECT users.id,
       setweight(to_tsvector(users.email), 'A') ||
       setweight(to_tsvector(user_names.last), 'B') ||
       setweight(to_tsvector(user_names.first), 'B')
FROM users
         JOIN user_names ON users.id = user_names.id;