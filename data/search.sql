TRUNCATE articles_ts;
INSERT INTO articles_ts (article_id, tsvector)
SELECT articles.id,
       setweight(to_tsvector(articles.title), 'A') ||
       setweight(to_tsvector(author_name.last), 'B') ||
       setweight(to_tsvector(author_name.first), 'B') ||
       setweight(to_tsvector(coalesce(string_agg(DISTINCT keywords.name, ' '), '')), 'B') ||
       setweight(to_tsvector(articles.body), 'C')
FROM articles
         JOIN users author ON articles.author_id = author.id
         JOIN user_names author_name ON author.id = author_name.id
         LEFT JOIN article_keywords ON articles.id = article_keywords.article_id
         LEFT JOIN keywords ON article_keywords.keyword_id = keywords.id
GROUP BY articles.id,
         articles.title,
         author_name.last,
         author_name.first,
         articles.body
ORDER BY articles.id;

TRUNCATE users_ts;
INSERT INTO users_ts (user_id, tsvector)
SELECT users.id,
       setweight(to_tsvector(users.email), 'A') ||
       setweight(to_tsvector(user_names.last), 'B') ||
       setweight(to_tsvector(user_names.first), 'B')
FROM users
         JOIN user_names ON users.id = user_names.id
ORDER BY users.id;