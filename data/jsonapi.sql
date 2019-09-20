--
-- PostgreSQL database dump
--

-- Dumped from database version 11.2
-- Dumped by pg_dump version 11.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: user_status; Type: TYPE; Schema: public; Owner: jsonapi
--

CREATE TYPE public.user_status AS ENUM (
    'pending',
    'active',
    'disabled'
);


ALTER TYPE public.user_status OWNER TO jsonapi;

--
-- Name: check_article_read_access(integer, integer); Type: FUNCTION; Schema: public; Owner: jsonapi
--

CREATE FUNCTION public.check_article_read_access(p_article_id integer, p_user_id integer) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
BEGIN
    -- return true if the user is the author of the article
    IF EXISTS(SELECT *
              FROM articles
              WHERE id = p_article_id
                AND author_id = p_user_id) THEN
        RETURN TRUE;
    END IF;

    -- check permissions
    RETURN EXISTS(SELECT *
                  FROM article_read_access
                  WHERE article_id = p_article_id
                    AND user_id = p_user_id);
END;
$$;


ALTER FUNCTION public.check_article_read_access(p_article_id integer, p_user_id integer) OWNER TO jsonapi;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: article_keywords; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.article_keywords (
    article_id integer NOT NULL,
    keyword_id integer NOT NULL
);


ALTER TABLE public.article_keywords OWNER TO jsonapi;

--
-- Name: article_read_access; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.article_read_access (
    user_id integer NOT NULL,
    article_id integer NOT NULL
);


ALTER TABLE public.article_read_access OWNER TO jsonapi;

--
-- Name: articles; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.articles (
    id integer NOT NULL,
    author_id integer NOT NULL,
    title text NOT NULL,
    body text NOT NULL,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_on timestamp without time zone,
    is_published boolean DEFAULT false NOT NULL
);


ALTER TABLE public.articles OWNER TO jsonapi;

--
-- Name: articles_id_seq; Type: SEQUENCE; Schema: public; Owner: jsonapi
--

CREATE SEQUENCE public.articles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.articles_id_seq OWNER TO jsonapi;

--
-- Name: articles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jsonapi
--

ALTER SEQUENCE public.articles_id_seq OWNED BY public.articles.id;


--
-- Name: comments; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.comments (
    id integer NOT NULL,
    article_id integer NOT NULL,
    user_id integer NOT NULL,
    body text,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_on timestamp without time zone
);


ALTER TABLE public.comments OWNER TO jsonapi;

--
-- Name: comments_id_seq; Type: SEQUENCE; Schema: public; Owner: jsonapi
--

CREATE SEQUENCE public.comments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.comments_id_seq OWNER TO jsonapi;

--
-- Name: comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jsonapi
--

ALTER SEQUENCE public.comments_id_seq OWNED BY public.comments.id;


--
-- Name: keywords; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.keywords (
    id integer NOT NULL,
    name text NOT NULL
);


ALTER TABLE public.keywords OWNER TO jsonapi;

--
-- Name: keywords_id_seq; Type: SEQUENCE; Schema: public; Owner: jsonapi
--

CREATE SEQUENCE public.keywords_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.keywords_id_seq OWNER TO jsonapi;

--
-- Name: keywords_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jsonapi
--

ALTER SEQUENCE public.keywords_id_seq OWNED BY public.keywords.id;


--
-- Name: replies; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.replies (
    id integer NOT NULL,
    user_id integer NOT NULL,
    comment_id integer NOT NULL,
    body text,
    created_on timestamp without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_on timestamp without time zone
);


ALTER TABLE public.replies OWNER TO jsonapi;

--
-- Name: replies_id_seq; Type: SEQUENCE; Schema: public; Owner: jsonapi
--

CREATE SEQUENCE public.replies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.replies_id_seq OWNER TO jsonapi;

--
-- Name: replies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jsonapi
--

ALTER SEQUENCE public.replies_id_seq OWNED BY public.replies.id;


--
-- Name: user_names; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.user_names (
    id integer NOT NULL,
    title text,
    first text NOT NULL,
    middle text,
    last text NOT NULL,
    suffix text,
    nickname text
);


ALTER TABLE public.user_names OWNER TO jsonapi;

--
-- Name: users; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email text NOT NULL,
    created_on timestamp(6) without time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    is_confirmed boolean DEFAULT false NOT NULL,
    force_password_reset boolean DEFAULT false NOT NULL,
    password character varying(128) NOT NULL,
    is_approved boolean DEFAULT false NOT NULL,
    status public.user_status DEFAULT 'pending'::public.user_status NOT NULL,
    is_superuser boolean DEFAULT false,
    first text
);


ALTER TABLE public.users OWNER TO jsonapi;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: jsonapi
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO jsonapi;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: jsonapi
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: articles id; Type: DEFAULT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.articles ALTER COLUMN id SET DEFAULT nextval('public.articles_id_seq'::regclass);


--
-- Name: comments id; Type: DEFAULT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.comments ALTER COLUMN id SET DEFAULT nextval('public.comments_id_seq'::regclass);


--
-- Name: keywords id; Type: DEFAULT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.keywords ALTER COLUMN id SET DEFAULT nextval('public.keywords_id_seq'::regclass);


--
-- Name: replies id; Type: DEFAULT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.replies ALTER COLUMN id SET DEFAULT nextval('public.replies_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Data for Name: article_keywords; Type: TABLE DATA; Schema: public; Owner: jsonapi
--

INSERT INTO public.article_keywords VALUES (12, 5);
INSERT INTO public.article_keywords VALUES (12, 6);
INSERT INTO public.article_keywords VALUES (11, 1);
INSERT INTO public.article_keywords VALUES (11, 2);
INSERT INTO public.article_keywords VALUES (11, 3);
INSERT INTO public.article_keywords VALUES (11, 4);


--
-- Data for Name: article_read_access; Type: TABLE DATA; Schema: public; Owner: jsonapi
--

INSERT INTO public.article_read_access VALUES (1, 13);


--
-- Data for Name: articles; Type: TABLE DATA; Schema: public; Owner: jsonapi
--

INSERT INTO public.articles VALUES (13, 2, 'Article 3', 'This is a test.', '2019-08-27 12:03:04.786736', NULL, false);
INSERT INTO public.articles VALUES (12, 1, 'Article 2', 'This is a test.', '2019-08-26 19:06:04.786736', NULL, false);
INSERT INTO public.articles VALUES (15, 2, 'Article 5', 'This is a test.', '2019-08-27 18:07:04.786736', NULL, true);
INSERT INTO public.articles VALUES (14, 1, 'Article 4', 'This is a test.', '2019-08-27 15:04:04.786736', NULL, true);
INSERT INTO public.articles VALUES (11, 1, 'Article 1', 'This is a test.', '2019-08-25 19:06:04.786736', NULL, true);


--
-- Data for Name: comments; Type: TABLE DATA; Schema: public; Owner: jsonapi
--

INSERT INTO public.comments VALUES (1, 11, 2, 'This is a test.', '2019-09-03 18:49:19.036388', NULL);
INSERT INTO public.comments VALUES (4, 15, 1, 'This is a test.', '2019-09-10 17:19:12.216478', NULL);
INSERT INTO public.comments VALUES (5, 15, 2, 'Another test.', '2019-09-10 17:19:12.216478', NULL);


--
-- Data for Name: keywords; Type: TABLE DATA; Schema: public; Owner: jsonapi
--

INSERT INTO public.keywords VALUES (1, 'foo');
INSERT INTO public.keywords VALUES (2, 'bar');
INSERT INTO public.keywords VALUES (3, 'test');
INSERT INTO public.keywords VALUES (4, 'apple');
INSERT INTO public.keywords VALUES (5, 'orange');
INSERT INTO public.keywords VALUES (6, 'red');


--
-- Data for Name: replies; Type: TABLE DATA; Schema: public; Owner: jsonapi
--



--
-- Data for Name: user_names; Type: TABLE DATA; Schema: public; Owner: jsonapi
--

INSERT INTO public.user_names VALUES (1, NULL, 'Jane', NULL, 'Doe', NULL, NULL);
INSERT INTO public.user_names VALUES (2, NULL, 'John', NULL, 'Smith', NULL, NULL);


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: jsonapi
--

INSERT INTO public.users VALUES (1, 'jane.doe@jsonapi.test', '2019-08-27 19:01:00.173736', false, false, '1b04d25168c6cf23f0c65cd86bcd2581abfa1981a4c56eb109f14d013a0ee805', false, 'active', false, NULL);
INSERT INTO public.users VALUES (2, 'john.smith@jsonapi.test', '2019-08-27 19:02:31.532467', false, false, '1b04d25168c6cf23f0c65cd86bcd2581abfa1981a4c56eb109f14d013a0ee805', false, 'active', false, NULL);


--
-- Name: articles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jsonapi
--

SELECT pg_catalog.setval('public.articles_id_seq', 5, true);


--
-- Name: comments_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jsonapi
--

SELECT pg_catalog.setval('public.comments_id_seq', 5, true);


--
-- Name: keywords_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jsonapi
--

SELECT pg_catalog.setval('public.keywords_id_seq', 5, true);


--
-- Name: replies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jsonapi
--

SELECT pg_catalog.setval('public.replies_id_seq', 1, false);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: jsonapi
--

SELECT pg_catalog.setval('public.users_id_seq', 2, true);


--
-- Name: article_keywords article_keywords_pk; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.article_keywords
    ADD CONSTRAINT article_keywords_pk PRIMARY KEY (article_id, keyword_id);


--
-- Name: article_read_access article_read_access_pk; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.article_read_access
    ADD CONSTRAINT article_read_access_pk PRIMARY KEY (user_id, article_id);


--
-- Name: articles articles_pk; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_pk PRIMARY KEY (id);


--
-- Name: comments comments_pk; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT comments_pk PRIMARY KEY (id);


--
-- Name: keywords keywords_pk; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.keywords
    ADD CONSTRAINT keywords_pk PRIMARY KEY (id);


--
-- Name: replies replies_pk; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.replies
    ADD CONSTRAINT replies_pk PRIMARY KEY (id);


--
-- Name: user_names user_names_pkey; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.user_names
    ADD CONSTRAINT user_names_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: article_keywords_article_id_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX article_keywords_article_id_index ON public.article_keywords USING btree (article_id);


--
-- Name: article_keywords_keyword_id_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX article_keywords_keyword_id_index ON public.article_keywords USING btree (keyword_id);


--
-- Name: articles_author_id_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX articles_author_id_index ON public.articles USING btree (author_id);


--
-- Name: comments_article_id_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX comments_article_id_index ON public.comments USING btree (article_id);


--
-- Name: comments_user_id_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX comments_user_id_index ON public.comments USING btree (user_id);


--
-- Name: keywords_name_uindex; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE UNIQUE INDEX keywords_name_uindex ON public.keywords USING btree (name);


--
-- Name: replies_article_id_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX replies_article_id_index ON public.replies USING btree (comment_id);


--
-- Name: replies_user_id_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX replies_user_id_index ON public.replies USING btree (user_id);


--
-- Name: users_created_on_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX users_created_on_index ON public.users USING btree (created_on);


--
-- Name: users_email_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX users_email_index ON public.users USING btree (email);


--
-- Name: users_id_is_superuser_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX users_id_is_superuser_index ON public.users USING btree (id, is_superuser);


--
-- Name: users_id_key; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE UNIQUE INDEX users_id_key ON public.users USING btree (id);


--
-- Name: users_status_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX users_status_index ON public.users USING btree (status);


--
-- Name: article_keywords article_keywords_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.article_keywords
    ADD CONSTRAINT article_keywords_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: article_keywords article_keywords_keyword_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.article_keywords
    ADD CONSTRAINT article_keywords_keyword_id_fkey FOREIGN KEY (keyword_id) REFERENCES public.keywords(id) ON DELETE CASCADE;


--
-- Name: article_read_access article_read_access_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.article_read_access
    ADD CONSTRAINT article_read_access_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: article_read_access article_read_access_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.article_read_access
    ADD CONSTRAINT article_read_access_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: comments articles_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT articles_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: articles articles_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_author_id_fkey FOREIGN KEY (author_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: comments articles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.comments
    ADD CONSTRAINT articles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: replies replies_comment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.replies
    ADD CONSTRAINT replies_comment_id_fkey FOREIGN KEY (comment_id) REFERENCES public.comments(id) ON DELETE CASCADE;


--
-- Name: replies replies_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.replies
    ADD CONSTRAINT replies_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_names user_names_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.user_names
    ADD CONSTRAINT user_names_id_fkey FOREIGN KEY (id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

