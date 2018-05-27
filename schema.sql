drop table if exists users;
create table users (
  id integer primary key autoincrement,
  email text not null,
  password text null,
  invite text not null,
  status int not null
);

