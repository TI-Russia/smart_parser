SET FOREIGN_KEY_CHECKS=0;
delete from declarations_person where id in (select person_id from  declarations_section where dedupe_score>0);
update declarations_section set person_id=null where dedupe_score > 0;
update declarations_section set dedupe_score = 0;
SET FOREIGN_KEY_CHECKS=1;
