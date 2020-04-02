drop database if exists disclosures_db;

create database disclosures_db character set utf8mb4 collate utf8mb4_unicode_ci;

create user if not exists 'disclosures'@'localhost' identified by 'disclosures';

grant all privileges on `disclosures_db`.* to 'disclosures'@'localhost';

use disclosures_db;

drop table if exists document_files;
create table document_files (
  id int not null auto_increment,
  office_name  longtext,
  sha256 char(64),
  declarator_document_id_if_dlrobot_failed int,
  web_domain char(64),
  file_path char(64),
  primary key (id)
);

drop table if exists sections;

create table sections
    (
        id int not null auto_increment,
        document_file_id int,
        fio longtext not null,
        income_year int not null,
        declarant_income int,
        smart_parser_json longtext,
        person_id int,
        primary key (id)
    )
    engine=InnoDB
    row_format=COMPRESSED
    key_block_size=8;


/*  ======  example values  ========*/


insert into document_files
    (
        office_name,
        sha256,
        web_domain,
        file_path
    )
    values (
        "тестовый офис",
        "aaaaaa",
        "pravo.ru",
        "125.docx"
    );

insert into sections
       (fio,
        income_year,
        declarant_income,
        smart_parser_json
        )
    values (
        "Тестов тест тестович",
        2011,
        10000,
        JSON_QUOTE('{"realty": "aaaaa"}')
    );

