CREATE TABLE blacklist (scope TEXT PRIMARY KEY, snowflakes bigint ARRAY);
CREATE TABLE userlog (id bigint PRIMARY KEY, name TEXT ARRAY, avatar TEXT ARRAY);
CREATE TABLE social (id bigint PRIMARY KEY, hugs TEXT ARRAY, kisses TEXT ARRAY, relation bigint, ship TEXT, blocked bigint ARRAY);
CREATE TABLE ships (id TEXT PRIMARY KEY, captain bigint, partner bigint,name TEXT,customtext TEXT,colour bigint,icon TEXT,timestamp bigint);
CREATE TABLE globalmsg (id bigint PRIMARY KEY, messages bigint);
CREATE TABLE guilds (id bigint PRIMARY KEY, data TEXT);
CREATE TABLE voice_activity (user_id bigint, server_id bigint, seconds_active bigint, PRIMARY KEY (user_id, server_id))