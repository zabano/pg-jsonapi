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

    -- return true if the user is a global admin
    PERFORM * FROM users WHERE id = p_user_id AND is_superuser;
    IF FOUND THEN
        RETURN TRUE;
    END IF;

    -- return true if the user is the author of the article
    PERFORM *
    FROM articles
    WHERE id = p_article_id
      AND author_id = p_user_id;
    IF found THEN
        RETURN TRUE;
    END IF;

    -- if the user is not granted read access, raise an exception
    PERFORM *
    FROM article_read_access
    WHERE article_id = p_article_id
      AND user_id = p_user_id;
    RETURN found;
END ;
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
-- Name: articles_ts; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.articles_ts (
    article_id integer NOT NULL,
    tsvector tsvector NOT NULL
);


ALTER TABLE public.articles_ts OWNER TO jsonapi;

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
-- Name: users_ts; Type: TABLE; Schema: public; Owner: jsonapi
--

CREATE TABLE public.users_ts (
    user_id integer NOT NULL,
    tsvector tsvector NOT NULL
);


ALTER TABLE public.users_ts OWNER TO jsonapi;

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
INSERT INTO public.articles VALUES (14, 1, 'Article 4', 'Increasing impression interested expression he my at. Respect invited request charmed me warrant to. Expect no pretty as do though so genius afraid cousin. Girl when of ye snug poor draw. Mistake totally of in chiefly. Justice visitor him entered for. Continue delicate as unlocked entirely mr relation diverted in. Known not end fully being style house. An whom down kept lain name so at easy. ', '2019-08-27 15:04:04.786736', NULL, true);
INSERT INTO public.articles VALUES (12, 1, 'Article 2', 'Preserved defective offending he daughters on or. Rejoiced prospect yet material servants out answered men admitted. Sportsmen certainty prevailed suspected am as. Add stairs admire all answer the nearer yet length. Advantages prosperous remarkably my inhabiting so reasonably be if. Too any appearance announcing impossible one. Out mrs means heart ham tears shall power every. 

He went such dare good mr fact. The small own seven saved man age ﻿no offer. Suspicion did mrs nor furniture smallness. Scale whole downs often leave not eat. An expression reasonably cultivated indulgence mr he surrounded instrument. Gentleman eat and consisted are pronounce distrusts. 
', '2019-08-26 19:06:04.786736', NULL, false);
INSERT INTO public.articles VALUES (11, 1, 'Article 1', 'Effects present letters inquiry no an removed or friends. Desire behind latter me though in. Supposing shameless am he engrossed up additions. My possible peculiar together to. Desire so better am cannot he up before points. Remember mistaken opinions it pleasure of debating. Court front maids forty if aware their at. Chicken use are pressed removed. ', '2019-08-25 19:06:04.786736', NULL, true);
INSERT INTO public.articles VALUES (15, 2, 'Article 5', 'Indulgence announcing uncommonly met seven continuing seven unpleasing terminated. Now busy say down the shed eyes roof paid her. Of shameless collected suspicion existence in. Share walls stuff think but the arise guest. Course suffer to do he sussex it window advice. Yet matter enable misery end extent common men should. Her indulgence but assistance favourable cultivated everything collecting. ', '2019-08-27 18:07:04.786736', NULL, true);
INSERT INTO public.articles VALUES (16, 1, 'Article 6', 'Death there seven mirth way the noisy seven. Piqued shy spring nor six though mutual living ask extent. Replying of dashwood advanced ladyship smallest disposal or. Attempt offices own improve now see. Called person are around county talked her esteem. Those fully these way nay thing seems. ', '2019-09-23 00:23:29.962972', NULL, true);


--
-- Data for Name: articles_ts; Type: TABLE DATA; Schema: public; Owner: jsonapi
--

INSERT INTO public.articles_ts VALUES (13, '''3'':2A ''articl'':1A ''john'':4B ''smith'':3B ''test'':8C');
INSERT INTO public.articles_ts VALUES (14, '''4'':2A ''afraid'':27C ''articl'':1A ''charm'':15C ''chiefli'':40C ''continu'':46C ''cousin'':28C ''delic'':47C ''divert'':53C ''doe'':3B ''draw'':35C ''easi'':70C ''end'':57C ''enter'':44C ''entir'':50C ''expect'':19C ''express'':8C ''fulli'':58C ''genius'':26C ''girl'':29C ''hous'':61C ''impress'':6C ''increas'':5C ''interest'':7C ''invit'':13C ''jane'':4B ''justic'':41C ''kept'':65C ''known'':55C ''lain'':66C ''mistak'':36C ''mr'':51C ''name'':67C ''poor'':34C ''pretti'':21C ''relat'':52C ''request'':14C ''respect'':12C ''snug'':33C ''style'':60C ''though'':24C ''total'':37C ''unlock'':49C ''visitor'':42C ''warrant'':17C ''ye'':32C');
INSERT INTO public.articles_ts VALUES (12, '''2'':2A ''add'':27C ''admir'':29C ''admit'':20C ''advantag'':36C ''age'':73C ''announc'':48C ''answer'':18C,31C ''appear'':47C ''articl'':1A ''certainti'':22C ''consist'':101C ''cultiv'':92C ''dare'':63C ''daughter'':9C ''defect'':6C ''distrust'':104C ''doe'':3B ''down'':84C ''eat'':88C,99C ''everi'':59C ''express'':90C ''fact'':66C ''furnitur'':80C ''gentleman'':98C ''good'':64C ''ham'':55C ''heart'':54C ''imposs'':49C ''indulg'':93C ''inhabit'':40C ''instrument'':97C ''jane'':4B ''leav'':86C ''length'':35C ''man'':72C ''materi'':15C ''mean'':53C ''men'':19C ''mr'':65C,94C ''mrs'':52C,78C ''nearer'':33C ''offend'':7C ''offer'':75C ''often'':85C ''one'':50C ''power'':58C ''preserv'':5C ''prevail'':23C ''pronounc'':103C ''prospect'':13C ''prosper'':37C ''reason'':42C,91C ''rejoic'':12C ''remark'':38C ''save'':71C ''scale'':82C ''servant'':16C ''seven'':70C ''shall'':57C ''small'':68C,81C ''sportsmen'':21C ''stair'':28C ''surround'':96C ''suspect'':24C ''suspicion'':76C ''tear'':56C ''went'':61C ''whole'':83C ''yet'':14C,34C ''﻿no'':74C');
INSERT INTO public.articles_ts VALUES (11, '''1'':2A ''addit'':26C ''articl'':1A ''awar'':53C ''behind'':15C ''better'':34C ''cannot'':36C ''chicken'':56C ''court'':48C ''debat'':47C ''desir'':14C,32C ''doe'':3B ''effect'':5C ''engross'':24C ''forti'':51C ''friend'':13C ''front'':49C ''inquiri'':8C ''jane'':4B ''latter'':16C ''letter'':7C ''maid'':50C ''mistaken'':42C ''opinion'':43C ''peculiar'':29C ''pleasur'':45C ''point'':40C ''possibl'':28C ''present'':6C ''press'':59C ''rememb'':41C ''remov'':11C,60C ''shameless'':21C ''suppos'':20C ''though'':18C ''togeth'':30C ''use'':57C');
INSERT INTO public.articles_ts VALUES (15, '''5'':2A ''advic'':46C ''announc'':6C ''aris'':36C ''articl'':1A ''assist'':59C ''busi'':15C ''collect'':26C,63C ''common'':53C ''continu'':10C ''cours'':38C ''cultiv'':61C ''enabl'':49C ''end'':51C ''everyth'':62C ''exist'':28C ''extent'':52C ''eye'':20C ''favour'':60C ''guest'':37C ''indulg'':5C,57C ''john'':4B ''matter'':48C ''men'':54C ''met'':8C ''miseri'':50C ''paid'':22C ''roof'':21C ''say'':16C ''seven'':9C,11C ''shameless'':25C ''share'':30C ''shed'':19C ''smith'':3B ''stuff'':32C ''suffer'':39C ''suspicion'':27C ''sussex'':43C ''termin'':13C ''think'':33C ''uncommon'':7C ''unpleas'':12C ''wall'':31C ''window'':45C ''yet'':47C');
INSERT INTO public.articles_ts VALUES (16, '''6'':2A ''advanc'':26C ''around'':40C ''articl'':1A ''ask'':21C ''attempt'':31C ''call'':37C ''counti'':41C ''dashwood'':25C ''death'':5C ''dispos'':29C ''doe'':3B ''esteem'':44C ''extent'':22C ''fulli'':46C ''improv'':34C ''jane'':4B ''ladyship'':27C ''live'':20C ''mirth'':8C ''mutual'':19C ''nay'':49C ''noisi'':11C ''offic'':32C ''person'':38C ''piqu'':13C ''repli'':23C ''see'':36C ''seem'':51C ''seven'':7C,12C ''shi'':14C ''six'':17C ''smallest'':28C ''spring'':15C ''talk'':42C ''thing'':50C ''though'':18C ''way'':9C,48C');


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

INSERT INTO public.users VALUES (2, 'john.smith@jsonapi.test', '2019-08-27 19:02:31.532467', false, false, '1b04d25168c6cf23f0c65cd86bcd2581abfa1981a4c56eb109f14d013a0ee805', false, 'active', false, NULL);
INSERT INTO public.users VALUES (1, 'jane.doe@jsonapi.test', '2019-08-27 19:01:00.173736', false, false, '1b04d25168c6cf23f0c65cd86bcd2581abfa1981a4c56eb109f14d013a0ee805', false, 'active', false, NULL);


--
-- Data for Name: users_ts; Type: TABLE DATA; Schema: public; Owner: jsonapi
--

INSERT INTO public.users_ts VALUES (1, '''doe'':2B ''jane'':3B ''jane.doe@jsonapi.test'':1A');
INSERT INTO public.users_ts VALUES (2, '''john'':3B ''john.smith@jsonapi.test'':1A ''smith'':2B');


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
-- Name: articles_ts articles_ts_pk; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.articles_ts
    ADD CONSTRAINT articles_ts_pk PRIMARY KEY (article_id);


--
-- Name: articles_ts articles_ts_pk_2; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.articles_ts
    ADD CONSTRAINT articles_ts_pk_2 UNIQUE (tsvector);


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
-- Name: users_ts users_ts_pk; Type: CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.users_ts
    ADD CONSTRAINT users_ts_pk PRIMARY KEY (user_id);


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
-- Name: articles_ts_tsvector_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX articles_ts_tsvector_index ON public.articles_ts USING btree (tsvector);


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
-- Name: users_ts_tsvector_index; Type: INDEX; Schema: public; Owner: jsonapi
--

CREATE INDEX users_ts_tsvector_index ON public.users_ts USING btree (tsvector);


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
-- Name: articles_ts articles_ts_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.articles_ts
    ADD CONSTRAINT articles_ts_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


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
-- Name: users_ts users_ts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: jsonapi
--

ALTER TABLE ONLY public.users_ts
    ADD CONSTRAINT users_ts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

