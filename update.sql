CREATE TEMPORARY TABLE t1_backup(
	"feed_id"	INTEGER,
	"identifier"	TEXT,
	"uri"	TEXT,
	"title"	TEXT,
	"updated"	FLOAT,
	"author"	TEXT,
	"content"	TEXT,
	"unread"	INTEGER
);
INSERT INTO t1_backup SELECT "feed_id","identifier","uri","title","updated","author","content","unread" FROM articles;
DROP TABLE "articles";
CREATE TABLE "articles" (
	"feed_id"	INTEGER,
	"identifier"	TEXT,
	"uri"	TEXT,
	"title"	TEXT,
	"updated"	FLOAT,
	"author"	TEXT,
	"content"	TEXT,
	"unread"	INTEGER
);
INSERT INTO articles SELECT "feed_id","identifier","uri","title","updated","author","content","unread" FROM t1_backup;
DROP TABLE t1_backup;