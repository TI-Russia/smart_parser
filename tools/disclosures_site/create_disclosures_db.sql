drop database if exists disclosures_db;
drop database if exists test_disclosures_db;
create database disclosures_db character set utf8mb4 collate utf8mb4_unicode_ci;
create user if not exists 'disclosures'@ identified by 'disclosures';
GRANT ALL PRIVILEGES ON *.* TO 'disclosures'@;

