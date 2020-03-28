DROP DATABASE IF EXISTS dlrobotdb ;
CREATE DATABASE dlrobotdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'dlrobotdb'@'localhost' IDENTIFIED BY 'dlrobotdb';
GRANT ALL PRIVILEGES ON `dlrobotdb`.* TO 'dlrobotdb'@'localhost'

