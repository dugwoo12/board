CREATE TABLE users(idx INTEGER PRIMARY KEY,name varchar(20), password varchar(30), email varchar(30),nname varchar(30), pnum varchar(15));
CREATE TABLE board(idx INTEGER PRIMARY KEY, name varchar(50) not null, title varchar(50) not null, content varchar(500) not null, dt date default current_timestamp, upload TEXT);
CREATE TABLE reply(idx INTEGER PRIMARY KEY , name varchar(50) not null ,content varchar(500) not null, dt date default current_timestamp, idx_r INTEGER, FOREIGN KEY(idx_r) REFERENCES board(idx));
