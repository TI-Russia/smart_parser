import sys
from common.primitives import normalize_whitespace
import ahocorasick

RUSSIA_REGION_ID = 0

RUSSIAN_REGIONS = [
{"id":RUSSIA_REGION_ID, "name":"Россия","code":0,"short_name":"РФ","extra_short_name":"РФ","name_ru":"Россия","name_en":"Russia","short_name_ru":"РФ","short_name_en":"","extra_short_name_ru":"","extra_short_name_en":"","slug":"RU","federal_district_id":0},
{"id":1,"name":"Санкт-Петербург","code":78,"short_name":"Санкт-Петербург","extra_short_name":"Санкт-Петербург","name_ru":"Санкт-Петербург","name_en":"Saint Petersburg","short_name_ru":"Санкт-Петербург","short_name_en":"Saint Petersburg","extra_short_name_ru":"Санкт-Петербург","extra_short_name_en":"","slug":"RU.SP","federal_district_id":2},
{"id":3,"name":"Республика Адыгея","code":1,"short_name":"Адыгея","extra_short_name":"Адыгея","name_ru":"Республика Адыгея","name_en":"Republic of Adygea","short_name_ru":"Адыгея","short_name_en":"Republic of Adygea","extra_short_name_ru":"Адыгея","extra_short_name_en":"","slug":"RU.AD","federal_district_id":6},
{"id":4,"name":"Республика Башкортостан","code":2,"short_name":"Башкортостан","extra_short_name":"Башкортостан","name_ru":"Республика Башкортостан","name_en":"Republic of Bashkortostan","short_name_ru":"Башкортостан","short_name_en":"Republic of Bashkortostan","extra_short_name_ru":"Башкортостан","extra_short_name_en":"","slug":"RU.BK","federal_district_id":7},
{"id":5,"name":"Республика Бурятия","code":3,"short_name":"Бурятия","extra_short_name":"Бурятия","name_ru":"Республика Бурятия","name_en":"Republic of Buryatia","short_name_ru":"Бурятия","short_name_en":"Republic of Buryatia","extra_short_name_ru":"Бурятия","extra_short_name_en":"","slug":"RU.BU","federal_district_id":3},
{"id":6,"name":"Республика Алтай","code":4,"short_name":"Алтай","extra_short_name":"Алтай","name_ru":"Республика Алтай","name_en":"Altay Republic","short_name_ru":"Алтай","short_name_en":"Altay Republic","extra_short_name_ru":"Алтай","extra_short_name_en":"","slug":"RU.GA","federal_district_id":3},
{"id":8,"name":"Республика Ингушетия","code":6,"short_name":"Ингушетия","extra_short_name":"Ингушетия","name_ru":"Республика Ингушетия","name_en":"Republic of Ingushetia","short_name_ru":"Ингушетия","short_name_en":"Republic of Ingushetia","extra_short_name_ru":"Ингушетия","extra_short_name_en":"","slug":"RU.IN","federal_district_id":1},
{"id":9,"name":"Кабардино-Балкарская Республика","code":7,"short_name":"Кабардино-Балкария","extra_short_name":"Кабардино-Балкария","name_ru":"Кабардино-Балкарская Республика","name_en":"Kabardino-Balkar Republic","short_name_ru":"Кабардино-Балкария","short_name_en":"Kabardino-Balkar Republic","extra_short_name_ru":"Кабардино-Балкария","extra_short_name_en":"","slug":"RU.KB","federal_district_id":1},
{"id":11,"name":"Карачаево-Черкесская республика","code":9,"short_name":"Карачаево-Черкессия","extra_short_name":"Карачаево-Черкессия","name_ru":"Карачаево-Черкесская республика","name_en":"Karachayevo-Cherkess Republic","short_name_ru":"Карачаево-Черкессия","short_name_en":"Karachayevo-Cherkess Republic","extra_short_name_ru":"Карачаево-Черкессия","extra_short_name_en":"","slug":"RU.KC","federal_district_id":1},
{"id":12,"name":"Республика Карелия","code":10,"short_name":"Карелия","extra_short_name":"Карелия","name_ru":"Республика Карелия","name_en":"Republic of Karelia","short_name_ru":"Карелия","short_name_en":"Republic of Karelia","extra_short_name_ru":"Карелия","extra_short_name_en":"","slug":"RU.KI","federal_district_id":2},
{"id":13,"name":"Республика Коми","code":11,"short_name":"Коми","extra_short_name":"Коми","name_ru":"Республика Коми","name_en":"Komi Republic","short_name_ru":"Коми","short_name_en":"Komi Republic","extra_short_name_ru":"Коми","extra_short_name_en":"","slug":"RU.KO","federal_district_id":2},
{"id":17,"name":"Республика Северная Осетия — Алания","code":15,"short_name":"Северная Осетия — Алания","extra_short_name":"Сев. Осетия-Алания","name_ru":"Республика Северная Осетия — Алания","name_en":"Republic of North Ossetia-Alania","short_name_ru":"Северная Осетия — Алания","short_name_en":"Republic of North Ossetia-Alania","extra_short_name_ru":"Сев. Осетия-Алания","extra_short_name_en":"","slug":"RU.NO","federal_district_id":1},
{"id":18,"name":"Республика Татарстан","code":16,"short_name":"Татарстан","extra_short_name":"Татарстан","name_ru":"Республика Татарстан","name_en":"Republic of Tatarstan","short_name_ru":"Татарстан","short_name_en":"Republic of Tatarstan","extra_short_name_ru":"Татарстан","extra_short_name_en":"","slug":"RU.TT","federal_district_id":7},
{"id":20,"name":"Удмуртская республика","code":18,"short_name":"Удмуртия","extra_short_name":"Удмуртия","name_ru":"Удмуртская республика","name_en":"Udmurt Republic","short_name_ru":"Удмуртия","short_name_en":"Udmurt Republic","extra_short_name_ru":"Удмуртия","extra_short_name_en":"","slug":"RU.UD","federal_district_id":7},
{"id":21,"name":"Республика Хакасия","code":19,"short_name":"Хакасия","extra_short_name":"Хакасия","name_ru":"Республика Хакасия","name_en":"Republic of Khakassia","short_name_ru":"Хакасия","short_name_en":"Republic of Khakassia","extra_short_name_ru":"Хакасия","extra_short_name_en":"","slug":"RU.KK","federal_district_id":3},
{"id":24,"name":"Алтайский край","code":22,"short_name":"Алтайский край","extra_short_name":"Алтайский край","name_ru":"Алтайский край","name_en":"Altay Kray","short_name_ru":"Алтайский край","short_name_en":"Altay Kray","extra_short_name_ru":"Алтайский край","extra_short_name_en":"","slug":"RU.AL","federal_district_id":3},
{"id":27,"name":"Краснодарский край","code":23,"short_name":"Краснодарский край","extra_short_name":"Краснодарский край","name_ru":"Краснодарский край","name_en":"Krasnodar Kray","short_name_ru":"Краснодарский край","short_name_en":"Krasnodar Territory","extra_short_name_ru":"Краснодарский край","extra_short_name_en":"","slug":"RU.KD","federal_district_id":6},
{"id":28,"name":"Красноярский край","code":24,"short_name":"Красноярский край","extra_short_name":"Красноярский край","name_ru":"Красноярский край","name_en":"Krasnoyars Kray","short_name_ru":"Красноярский край","short_name_en":"Krasnoyarsk Territory","extra_short_name_ru":"Красноярский край","extra_short_name_en":"","slug":"RU.KX","federal_district_id":3},
{"id":29,"name":"Пермский край","code":59,"short_name":"Пермский край","extra_short_name":"Пермский край","name_ru":"Пермский край","name_en":"Perm Kray","short_name_ru":"Пермский край","short_name_en":"Perm Territory","extra_short_name_ru":"Пермский край","extra_short_name_en":"","slug":"RU.PE","federal_district_id":7},
{"id":32,"name":"Хабаровский край","code":27,"short_name":"Хабаровский край","extra_short_name":"Хабаровский край","name_ru":"Хабаровский край","name_en":"Khabarovsk Kray","short_name_ru":"Хабаровский край","short_name_en":"Khabarovsk Kray","extra_short_name_ru":"Хабаровский край","extra_short_name_en":"","slug":"RU.KH","federal_district_id":8},
{"id":33,"name":"Амурская область","code":28,"short_name":"Амурская область","extra_short_name":"Амурская обл.","name_ru":"Амурская область","name_en":"Amur Oblast","short_name_ru":"Амурская область","short_name_en":"Amur Region ","extra_short_name_ru":"Амурская обл.","extra_short_name_en":"","slug":"RU.AM","federal_district_id":8},
{"id":35,"name":"Брянская область","code":32,"short_name":"Брянская область","extra_short_name":"Брянская обл.","name_ru":"Брянская область","name_en":"Bryansk Oblast","short_name_ru":"Брянская область","short_name_en":"Bryansk Region","extra_short_name_ru":"Брянская обл.","extra_short_name_en":"","slug":"RU.BR","federal_district_id":4},
{"id":36,"name":"Владимирская область","code":33,"short_name":"Владимирская область","extra_short_name":"Владимирская обл.","name_ru":"Владимирская область","name_en":"Vladimir Oblast ","short_name_ru":"Владимирская область","short_name_en":"Vladimir Region","extra_short_name_ru":"Владимирская обл.","extra_short_name_en":"","slug":"RU.VL","federal_district_id":4},
{"id":37,"name":"Архангельская область","code":29,"short_name":"Архангельская область","extra_short_name":"Архангельская обл.","name_ru":"Архангельская область","name_en":"Arkhangelsk Oblast","short_name_ru":"Архангельская область","short_name_en":"Arkhangelsk Region","extra_short_name_ru":"Архангельская обл.","extra_short_name_en":"","slug":"RU.AR","federal_district_id":2},
{"id":38,"name":"Астраханская область","code":30,"short_name":"Астраханская область","extra_short_name":"Астраханская обл.","name_ru":"Астраханская область","name_en":"Astrakhan Oblast","short_name_ru":"Астраханская область","short_name_en":"Astrakhan Region","extra_short_name_ru":"Астраханская обл.","extra_short_name_en":"","slug":"RU.AS","federal_district_id":6},
{"id":41,"name":"Волгоградская область","code":34,"short_name":"Волгоградская область","extra_short_name":"Волгоградская обл.","name_ru":"Волгоградская область","name_en":"Volgograd Oblast ","short_name_ru":"Волгоградская область","short_name_en":"Volgograd Region","extra_short_name_ru":"Волгоградская обл.","extra_short_name_en":"","slug":"RU.VG","federal_district_id":6},
{"id":42,"name":"Вологодская область","code":35,"short_name":"Вологодская область","extra_short_name":"Вологодская обл.","name_ru":"Вологодская область","name_en":"Vologoda Oblast ","short_name_ru":"Вологодская область","short_name_en":"Vologda Region","extra_short_name_ru":"Вологодская обл.","extra_short_name_en":"","slug":"RU.VO","federal_district_id":2},
{"id":43,"name":"Воронежская область","code":36,"short_name":"Воронежская область","extra_short_name":"Воронежская обл.","name_ru":"Воронежская область","name_en":"Voronezh Oblast ","short_name_ru":"Воронежская область","short_name_en":"Voronezh Region","extra_short_name_ru":"Воронежская обл.","extra_short_name_en":"","slug":"RU.VR","federal_district_id":4},
{"id":44,"name":"Забайкальский край","code":75,"short_name":"Забайкальский край","extra_short_name":"Забайкальский край","name_ru":"Забайкальский край","name_en":"Zabaykalsky Kray","short_name_ru":"Забайкальский край","short_name_en":"Zabaykalsky Kray","extra_short_name_ru":"Забайкальский край","extra_short_name_en":"","slug":"RU.ZB","federal_district_id":3},
{"id":45,"name":"Иркутская область","code":38,"short_name":"Иркутская область","extra_short_name":"Иркутская обл.","name_ru":"Иркутская область","name_en":"Irkutsk Oblast","short_name_ru":"Иркутская область","short_name_en":"Irkutsk Region","extra_short_name_ru":"Иркутская обл.","extra_short_name_en":"","slug":"RU.IK","federal_district_id":3},
{"id":46,"name":"Калининградская область","code":39,"short_name":"Калининградская область","extra_short_name":"Калининградская обл.","name_ru":"Калининградская область","name_en":"Kaliningrad Oblast","short_name_ru":"Калининградская область","short_name_en":"Kaliningrad Oblast","extra_short_name_ru":"Калининградская обл.","extra_short_name_en":"","slug":"RU.KN","federal_district_id":2},
{"id":47,"name":"Республика Калмыкия","code":8,"short_name":"Калмыкия","extra_short_name":"Калмыкия","name_ru":"Республика Калмыкия","name_en":"Republic of Kalmykia","short_name_ru":"Калмыкия","short_name_en":"Republic of Kalmykia","extra_short_name_ru":"Калмыкия","extra_short_name_en":"","slug":"RU.KL","federal_district_id":6},
{"id":48,"name":"Камчатский край","code":41,"short_name":"Камчатский край","extra_short_name":"Камчатский край","name_ru":"Камчатский край","name_en":"Kamchatka Kray","short_name_ru":"Камчатский край","short_name_en":"Kamchatka Territory","extra_short_name_ru":"Камчатский край","extra_short_name_en":"","slug":"RU.KQ","federal_district_id":8},
{"id":50,"name":"Кемеровская область","code":42,"short_name":"Кемеровская область","extra_short_name":"Кемеровская обл.","name_ru":"Кемеровская область","name_en":"Kemerovo Oblast","short_name_ru":"Кемеровская область","short_name_en":"Kemerovo Region","extra_short_name_ru":"Кемеровская обл.","extra_short_name_en":"","slug":"RU.KE","federal_district_id":3},
{"id":51,"name":"Кировская область","code":43,"short_name":"Кировская область","extra_short_name":"Кировская обл.","name_ru":"Кировская область","name_en":"Kirov Oblast ","short_name_ru":"Кировская область","short_name_en":"Kirov Region","extra_short_name_ru":"Кировская обл.","extra_short_name_en":"","slug":"RU.KV","federal_district_id":7},
{"id":53,"name":"Костромская область","code":44,"short_name":"Костромская область","extra_short_name":"Костромская обл.","name_ru":"Костромская область","name_en":"Kostroma Oblast ","short_name_ru":"Костромская область","short_name_en":"Kostroma Region","extra_short_name_ru":"Костромская обл.","extra_short_name_en":"","slug":"RU.KT","federal_district_id":4},
{"id":55,"name":"Курская область","code":46,"short_name":"Курская область","extra_short_name":"Курская обл.","name_ru":"Курская область","name_en":"Kursk Oblast","short_name_ru":"Курская область","short_name_en":"Kursk Region","extra_short_name_ru":"Курская обл.","extra_short_name_en":"","slug":"RU.KS","federal_district_id":4},
{"id":56,"name":"Ленинградская область","code":47,"short_name":"Ленинградская область","extra_short_name":"Ленинградская обл.","name_ru":"Ленинградская область","name_en":"Leningrad Oblast ","short_name_ru":"Ленинградская область","short_name_en":"Leningrad Region","extra_short_name_ru":"Ленинградская обл.","extra_short_name_en":"","slug":"RU.LN","federal_district_id":2},
{"id":57,"name":"Липецкая область","code":48,"short_name":"Липецкая область","extra_short_name":"Липецкая обл.","name_ru":"Липецкая область","name_en":"Lipetsk Oblast","short_name_ru":"Липецкая область","short_name_en":"Lipetsk Region","extra_short_name_ru":"Липецкая обл.","extra_short_name_en":"","slug":"RU.LP","federal_district_id":4},
{"id":58,"name":"Магаданская область","code":49,"short_name":"Магаданская область","extra_short_name":"Магаданская обл.","name_ru":"Магаданская область","name_en":"Magadan Oblast ","short_name_ru":"Магаданская область","short_name_en":"Magadan Region","extra_short_name_ru":"Магаданская обл.","extra_short_name_en":"","slug":"RU.MG","federal_district_id":8},
{"id":59,"name":"Республика Дагестан","code":5,"short_name":"Дагестан","extra_short_name":"Дагестан","name_ru":"Республика Дагестан","name_en":"Republic of Dagestan","short_name_ru":"Дагестан","short_name_en":"Republic of Dagestan","extra_short_name_ru":"Дагестан","extra_short_name_en":"","slug":"RU.DA","federal_district_id":1},
{"id":61,"name":"Республика Марий Эл","code":12,"short_name":"Марий Эл","extra_short_name":"Марий Эл","name_ru":"Республика Марий Эл","name_en":"Mari El Republic","short_name_ru":"Марий Эл","short_name_en":"Mari El Republic","extra_short_name_ru":"Марий Эл","extra_short_name_en":"","slug":"RU.ME","federal_district_id":7},
{"id":62,"name":"Республика Мордовия","code":13,"short_name":"Мордовия","extra_short_name":"Мордовия","name_ru":"Республика Мордовия","name_en":"Republic of Mordovia","short_name_ru":"Мордовия","short_name_en":"Republic of Mordovia","extra_short_name_ru":"Мордовия","extra_short_name_en":"","slug":"RU.MR","federal_district_id":7},
{"id":63,"name":"Москва","code":77,"short_name":"Москва","extra_short_name":"Москва","name_ru":"Москва","name_en":"Moscow","short_name_ru":"Москва","short_name_en":"Moscow","extra_short_name_ru":"Москва","extra_short_name_en":"","slug":"RU.MS.CITY","federal_district_id":4},
{"id":64,"name":"Московская область","code":50,"short_name":"Московская область","extra_short_name":"Московская обл.","name_ru":"Московская область","name_en":"Moscow Oblast ","short_name_ru":"Московская область","short_name_en":"Moscow Region","extra_short_name_ru":"Московская обл.","extra_short_name_en":"","slug":"RU.MS","federal_district_id":4},
{"id":65,"name":"Мурманская область","code":51,"short_name":"Мурманская область","extra_short_name":"Мурманская обл.","name_ru":"Мурманская область","name_en":"Murmansk Oblast","short_name_ru":"Мурманская область","short_name_en":"Murmansk Region","extra_short_name_ru":"Мурманская обл.","extra_short_name_en":"","slug":"RU.MM","federal_district_id":2},
{"id":66,"name":"Нижегородская область","code":52,"short_name":"Нижегородская область","extra_short_name":"Нижегородская обл.","name_ru":"Нижегородская область","name_en":"Nizhegorod Oblast","short_name_ru":"Нижегородская область","short_name_en":"Nizhegorod Oblast","extra_short_name_ru":"Нижегородская обл.","extra_short_name_en":"","slug":"RU.NZ","federal_district_id":7},
{"id":67,"name":"Новгородская область","code":53,"short_name":"Новгородская область","extra_short_name":"Новгородская обл.","name_ru":"Новгородская область","name_en":"Novgorod Oblast ","short_name_ru":"Новгородская область","short_name_en":"Novgorod Region","extra_short_name_ru":"Новгородская обл.","extra_short_name_en":"","slug":"RU.NG","federal_district_id":2},
{"id":68,"name":"Новосибирская область","code":54,"short_name":"Новосибирская область","extra_short_name":"Новосибирская обл.","name_ru":"Новосибирская область","name_en":"Novosibirsk Oblast ","short_name_ru":"Новосибирская область","short_name_en":"Novosibirsk Region","extra_short_name_ru":"Новосибирская обл.","extra_short_name_en":"","slug":"RU.NS","federal_district_id":3},
{"id":69,"name":"Омская область","code":55,"short_name":"Омская область","extra_short_name":"Омская обл.","name_ru":"Омская область","name_en":"Omsk Oblast ","short_name_ru":"Омская область","short_name_en":"Omsk Region","extra_short_name_ru":"Омская обл.","extra_short_name_en":"","slug":"RU.OM","federal_district_id":3},
{"id":70,"name":"Орловская область","code":57,"short_name":"Орловская область","extra_short_name":"Орловская обл.","name_ru":"Орловская область","name_en":"Oryol Oblast ","short_name_ru":"Орловская область","short_name_en":"Oryol Region","extra_short_name_ru":"Орловская обл.","extra_short_name_en":"","slug":"RU.OL","federal_district_id":4},
{"id":72,"name":"Пензенская область","code":58,"short_name":"Пензенская область","extra_short_name":"Пензенская обл.","name_ru":"Пензенская область","name_en":"Penza Oblast ","short_name_ru":"Пензенская область","short_name_en":"Penza Region","extra_short_name_ru":"Пензенская обл.","extra_short_name_en":"","slug":"RU.PZ","federal_district_id":7},
{"id":74,"name":"Приморский край","code":25,"short_name":"Приморский край","extra_short_name":"Приморский край","name_ru":"Приморский край","name_en":"Primorsky Kray","short_name_ru":"Приморский край","short_name_en":"Primorsky Kray","extra_short_name_ru":"Приморский край","extra_short_name_en":"","slug":"RU.PR","federal_district_id":8},
{"id":75,"name":"Псковская область","code":60,"short_name":"Псковская область","extra_short_name":"Псковская обл.","name_ru":"Псковская область","name_en":"Pskov Oblast ","short_name_ru":"Псковская область","short_name_en":"Pskov Region","extra_short_name_ru":"Псковская обл.","extra_short_name_en":"","slug":"RU.PS","federal_district_id":2},
{"id":76,"name":"Ростовская область","code":61,"short_name":"Ростовская область","extra_short_name":"Ростовская обл.","name_ru":"Ростовская область","name_en":"Rostov Oblast ","short_name_ru":"Ростовская область","short_name_en":"Rostov Oblast","extra_short_name_ru":"Ростовская обл.","extra_short_name_en":"","slug":"RU.RO","federal_district_id":6},
{"id":77,"name":"Самарская область","code":63,"short_name":"Самарская область","extra_short_name":"Самарская обл.","name_ru":"Самарская область","name_en":"Samara Oblast","short_name_ru":"Самарская область","short_name_en":"Samara Oblast","extra_short_name_ru":"Самарская обл.","extra_short_name_en":"","slug":"RU.SA","federal_district_id":7},
{"id":79,"name":"Саратовская область","code":64,"short_name":"Саратовская область","extra_short_name":"Саратовская обл.","name_ru":"Саратовская область","name_en":"Saratov Oblast","short_name_ru":"Саратовская область","short_name_en":"Saratov Oblast","extra_short_name_ru":"Саратовская обл.","extra_short_name_en":"","slug":"RU.SR","federal_district_id":7},
{"id":80,"name":"Свердловская область","code":66,"short_name":"Свердловская область","extra_short_name":"Свердловская обл.","name_ru":"Свердловская область","name_en":"Sverdlovsk Oblast","short_name_ru":"Свердловская область","short_name_en":"Sverdlovsk Oblast","extra_short_name_ru":"Свердловская обл.","extra_short_name_en":"","slug":"RU.SV","federal_district_id":5},
{"id":81,"name":"Ставропольский край","code":26,"short_name":"Ставропольский край","extra_short_name":"Ставропольский край","name_ru":"Ставропольский край","name_en":"Stavropol Kray","short_name_ru":"Ставропольский край","short_name_en":"Stavropol Kray","extra_short_name_ru":"Ставропольский край","extra_short_name_en":"","slug":"RU.ST","federal_district_id":1},
{"id":82,"name":"Тамбовская область","code":68,"short_name":"Тамбовская область","extra_short_name":"Тамбовская обл.","name_ru":"Тамбовская область","name_en":"Tambov Oblast","short_name_ru":"Тамбовская область","short_name_en":"Tambov Oblast","extra_short_name_ru":"Тамбовская обл.","extra_short_name_en":"","slug":"RU.TB","federal_district_id":4},
{"id":84,"name":"Тульская область","code":71,"short_name":"Тульская область","extra_short_name":"Тульская обл.","name_ru":"Тульская область","name_en":"Tula Oblast","short_name_ru":"Тульская область","short_name_en":"Tula Oblast","extra_short_name_ru":"Тульская обл.","extra_short_name_en":"","slug":"RU.TL","federal_district_id":4},
{"id":85,"name":"Республика Тува (Тыва)","code":17,"short_name":"Тува (Тыва)","extra_short_name":"Тува (Тыва)","name_ru":"Республика Тува (Тыва)","name_en":"Tyva Republic","short_name_ru":"Тува (Тыва)","short_name_en":"Tyva Republic","extra_short_name_ru":"Тува (Тыва)","extra_short_name_en":"","slug":"RU.TU","federal_district_id":3},
{"id":86,"name":"Тюменская область","code":72,"short_name":"Тюменская область","extra_short_name":"Тюменская обл.","name_ru":"Тюменская область","name_en":"Tyumen Oblast","short_name_ru":"Тюменская область","short_name_en":"Tyumen Oblast","extra_short_name_ru":"Тюменская обл.","extra_short_name_en":"","slug":"RU.TY","federal_district_id":5},
{"id":88,"name":"Ульяновская область","code":73,"short_name":"Ульяновская область","extra_short_name":"Ульяновская обл.","name_ru":"Ульяновская область","name_en":"Ulyanovsk Oblast","short_name_ru":"Ульяновская область","short_name_en":"Ulyanovsk Oblast","extra_short_name_ru":"Ульяновская обл.","extra_short_name_en":"","slug":"RU.UL","federal_district_id":7},
{"id":89,"name":"Челябинская область","code":74,"short_name":"Челябинская область","extra_short_name":"Челябинская обл.","name_ru":"Челябинская область","name_en":"Chelyabinsk Oblast","short_name_ru":"Челябинская область","short_name_en":"Chelyabinsk Oblast","extra_short_name_ru":"Челябинская обл.","extra_short_name_en":"","slug":"RU.CL","federal_district_id":5},
{"id":90,"name":"Чеченская республика","code":95,"short_name":"Чечня","extra_short_name":"Чечня","name_ru":"Чеченская республика","name_en":"Chechen Republic","short_name_ru":"Чечня","short_name_en":"Chechen Republic","extra_short_name_ru":"Чечня","extra_short_name_en":"","slug":"RU.CN","federal_district_id":1},
{"id":91,"name":"Чувашская республика - Чувашия","code":21,"short_name":"Чувашия","extra_short_name":"Чувашия","name_ru":"Чувашская республика - Чувашия","name_en":"Chuvash Republic","short_name_ru":"Чувашия","short_name_en":"Chuvash Republic","extra_short_name_ru":"Чувашия","extra_short_name_en":"","slug":"RU.CV","federal_district_id":7},
{"id":92,"name":"Республика Саха (Якутия)","code":14,"short_name":"Саха (Якутия)","extra_short_name":"Саха (Якутия)","name_ru":"Республика Саха (Якутия)","name_en":"Sakha (Yakutia) Republic","short_name_ru":"Саха (Якутия)","short_name_en":"Sakha (Yakutia) Republic","extra_short_name_ru":"Саха (Якутия)","extra_short_name_en":"","slug":"RU.SK","federal_district_id":8},
{"id":93,"name":"Еврейская автономная область","code":79,"short_name":"Еврейская АО","extra_short_name":"Еврейская АО","name_ru":"Еврейская автономная область","name_en":"Jewish Autonomous Oblast","short_name_ru":"Еврейская АО","short_name_en":"Jewish Autonomous Region","extra_short_name_ru":"Еврейская АО","extra_short_name_en":"","slug":"RU.YV","federal_district_id":8},
{"id":94,"name":"Сахалинская область","code":65,"short_name":"Сахалинская область","extra_short_name":"Сахалинская обл.","name_ru":"Сахалинская область","name_en":"Sakhalin Oblast","short_name_ru":"Сахалинская область","short_name_en":"Sakhalin Oblast","extra_short_name_ru":"Сахалинская обл.","extra_short_name_en":"","slug":"RU.SL","federal_district_id":8},
{"id":95,"name":"Чукотский автономный округ","code":87,"short_name":"Чукотский АО","extra_short_name":"Чукотский АО","name_ru":"Чукотский автономный округ","name_en":"Chukotka Autonomous Okrug","short_name_ru":"Чукотский АО","short_name_en":"Chukotka Autonomous Okrug","extra_short_name_ru":"Чукотский АО","extra_short_name_en":"","slug":"RU.CK","federal_district_id":8},
{"id":96,"name":"Белгородская область","code":31,"short_name":"Белгородская область","extra_short_name":"Белгородская обл.","name_ru":"Белгородская область","name_en":"Belgorod Oblast","short_name_ru":"Белгородская область","short_name_en":"Belgorod Region","extra_short_name_ru":"Белгородская обл.","extra_short_name_en":"","slug":"RU.BL","federal_district_id":4},
{"id":97,"name":"Калужская область","code":40,"short_name":"Калужская область","extra_short_name":"Калужская обл.","name_ru":"Калужская область","name_en":"Kaluga Oblast","short_name_ru":"Калужская область","short_name_en":"Kaluga Oblast","extra_short_name_ru":"Калужская обл.","extra_short_name_en":"","slug":"RU.KG","federal_district_id":4},
{"id":98,"name":"Курганская область","code":45,"short_name":"Курганская область","extra_short_name":"Курганская обл.","name_ru":"Курганская область","name_en":"Kurgan Oblast","short_name_ru":"Курганская область","short_name_en":"Kurgan Region","extra_short_name_ru":"Курганская обл.","extra_short_name_en":"","slug":"RU.KU","federal_district_id":5},
{"id":99,"name":"Ивановская область","code":37,"short_name":"Ивановская область","extra_short_name":"Ивановская обл.","name_ru":"Ивановская область","name_en":"Ivanovo Oblast","short_name_ru":"Ивановская область","short_name_en":"Ivanovo Region","extra_short_name_ru":"Ивановская обл.","extra_short_name_en":"","slug":"RU.IV","federal_district_id":4},
{"id":100,"name":"Смоленская область","code":67,"short_name":"Смоленская область","extra_short_name":"Смоленская обл.","name_ru":"Смоленская область","name_en":"Smolensk Oblast","short_name_ru":"Смоленская область","short_name_en":"Smolensk Oblast","extra_short_name_ru":"Смоленская обл.","extra_short_name_en":"","slug":"RU.SM","federal_district_id":4},
{"id":101,"name":"Тверская область","code":69,"short_name":"Тверская область","extra_short_name":"Тверская обл.","name_ru":"Тверская область","name_en":"Tver Oblast","short_name_ru":"Тверская область","short_name_en":"Tver Oblast","extra_short_name_ru":"Тверская обл.","extra_short_name_en":"","slug":"RU.TV","federal_district_id":4},
{"id":102,"name":"Ненецкий автономный округ","code":83,"short_name":"Ненецкий АО","extra_short_name":"Ненецкий АО","name_ru":"Ненецкий автономный округ","name_en":"Nenets Autonomous Okrug","short_name_ru":"Ненецкий АО","short_name_en":"Nenets Autonomous Okrug","extra_short_name_ru":"Ненецкий АО","extra_short_name_en":"","slug":"RU.NN","federal_district_id":2},
{"id":103,"name":"Рязанская область","code":62,"short_name":"Рязанская область","extra_short_name":"Рязанская обл.","name_ru":"Рязанская область","name_en":"Ryazan Oblast","short_name_ru":"Рязанская область","short_name_en":"Ryazan Oblast","extra_short_name_ru":"Рязанская обл.","extra_short_name_en":"","slug":"RU.RZ","federal_district_id":4},
{"id":104,"name":"Ямало-Ненецкий автономный округ","code":89,"short_name":"Ямало-Ненецкий АО","extra_short_name":"Ямало-Ненецкий АО","name_ru":"Ямало-Ненецкий автономный округ","name_en":"Yamalo-Nenets Autonomous Okrug","short_name_ru":"Ямало-Ненецкий АО","short_name_en":"Yamalo-Nenets Autonomous Okrug","extra_short_name_ru":"Ямало-Ненецкий АО","extra_short_name_en":"","slug":"RU.YN","federal_district_id":5},
{"id":105,"name":"Оренбургская область","code":56,"short_name":"Оренбургская область","extra_short_name":"Оренбургская обл.","name_ru":"Оренбургская область","name_en":"Orenburg Oblast ","short_name_ru":"Оренбургская область","short_name_en":"Orenburg Region","extra_short_name_ru":"Оренбургская обл.","extra_short_name_en":"","slug":"RU.OB","federal_district_id":7},
{"id":106,"name":"Томская область","code":70,"short_name":"Томская область","extra_short_name":"Томская обл.","name_ru":"Томская область","name_en":"Tomsk Oblast","short_name_ru":"Томская область","short_name_en":"Tomsk Oblast","extra_short_name_ru":"Томская обл.","extra_short_name_en":"","slug":"RU.TO","federal_district_id":3},
{"id":107,"name":"Ярославская область","code":76,"short_name":"Ярославская область","extra_short_name":"Ярославская обл.","name_ru":"Ярославская область","name_en":"Yaroslavskaya oblast ","short_name_ru":"Ярославская область","short_name_en":"Yaroslavl Region","extra_short_name_ru":"Ярославская обл.","extra_short_name_en":"","slug":"RU.YS","federal_district_id":4},
{"id":108,"name":"Ханты-Мансийский автономный округ — Югра","code":86,"short_name":"Ханты-Мансийский АО — Югра","extra_short_name":"Ханты-Манс-ий АО (Югра)","name_ru":"Ханты-Мансийский автономный округ — Югра","name_en":"Khanty-Mansiysk Autonomous Okrug - Yugra","short_name_ru":"Ханты-Мансийский АО — Югра","short_name_en":"Khanty-Mansiysk Autonomous Okrug - Yugra","extra_short_name_ru":"Ханты-Манс-ий АО (Югра)","extra_short_name_en":"","slug":"RU.KM","federal_district_id":5},
{"id":109,"name":"Республика Крым*","code":82,"short_name":"Крым*","extra_short_name":"Crimea","name_ru":"Республика Крым*","name_en":"","short_name_ru":"Крым*","short_name_en":"","extra_short_name_ru":"Crimea","extra_short_name_en":"","slug":"Cr","federal_district_id":6},
{"id":110,"name":"Севастополь*","code":92,"short_name":"Севастополь*","extra_short_name":"Sevast","name_ru":"Севастополь*","name_en":"","short_name_ru":"Севастополь*","short_name_en":"","extra_short_name_ru":"Sevast","extra_short_name_en":"","slug":"Sevast","federal_district_id":6}
]

#region id to other cases (dative or genitive)
REGIONS_ALL_FORMS = {
    "1": {
        "dative": [
            "по санкт-петербургу",
            "по г.санкт-петербургу",
            "по г. санкт-петербургу"
        ],
        "genitive": [
            "санкт-петербурга"
        ],
        "locative": [
            "в санкт-петербурге",
            "в г.санкт-петербурге",
            "в г. санкт-петербурге"
        ]
    },
    "3": {
        "dative": [
            "по республике адыгея"
        ],
        "genitive": [
            "республики адыгея"
        ],
        "locative": [
            "в республике адыгеи"
        ]
    },
    "4": {
        "dative": [
            "по республике башкортостан"
        ],
        "genitive": [
            "республики башкортостан"
        ],
        "locative": [
            "в республике башкортостан"
        ]
    },
    "5": {
        "dative": [
            "по республике бурятия"
        ],
        "genitive": [
            "республики бурятия"
        ],
        "locative": [
            "в республике бурятии"
        ]
    },
    "6": {
        "dative": [
            "по республике алтай"
        ],
        "genitive": [
            "республики алтай"
        ],
        "locative": [
            "в республике алтай"
        ]
    },
    "8": {
        "dative": [
            "по республике ингушетия"
        ],
        "genitive": [
            "республики ингушетия"
        ],
        "locative": [
            "в республике ингушетии"
        ]
    },
    "9": {
        "dative": [
            "по кабардино-балкарской республике"
        ],
        "genitive": [
            "кабардино-балкарской республики"
        ],
        "locative": [
            "в кабардино-балкарской республике"
        ]
    },
    "11": {
        "dative": [
            "по карачаево-черкесской республике"
        ],
        "genitive": [
            "карачаево-черкесской республики"
        ],
        "locative": [
            "в карачаево-черкесской республике"
        ]
    },
    "12": {
        "dative": [
            "по республике карелия"
        ],
        "genitive": [
            "республики карелия"
        ],
        "locative": [
            "в республике карели"
        ]
    },
    "13": {
        "dative": [
            "по республике коми"
        ],
        "genitive": [
            "республики коми"
        ],
        "locative": [
            "в республике коми"
        ]
    },
    "17": {
        "dative": [
            "по республике северная осетия-алания",
            "по северной осетии"
        ],
        "genitive": [
            "республики северная осетия-алания"
        ],
        "locative": [
            "в республике северная осети",
            "в северной осети"
        ]
    },
    "18": {
        "dative": [
            "по республике татарстан"
        ],
        "genitive": [
            "республики татарстан"
        ],
        "locative": [
            "в республике татарстан"
        ]
    },
    "20": {
        "dative": [
            "по удмуртской республике"
        ],
        "genitive": [
            "удмуртской республики"
        ],
        "locative": [
            "в удмуртской республике"
        ]
    },
    "21": {
        "dative": [
            "по республике хакасия"
        ],
        "genitive": [
            "республики хакасия"
        ],
        "locative": [
            "в республике хакаси"
        ]
    },
    "24": {
        "dative": [
            "по алтайскому краю"
        ],
        "genitive": [
            "алтайского края"
        ],
        "locative": [
            "в алтайском крае"
        ]
    },
    "27": {
        "dative": [
            "по краснодарскому краю"
        ],
        "genitive": [
            "краснодарскому края"
        ],
        "locative": [
            "в краснодарском крае"
        ]
    },
    "28": {
        "dative": [
            "по красноярскому краю"
        ],
        "genitive": [
            "красноярского края"
        ],
        "locative": [
            "в красноярском крае"
        ]
    },
    "29": {
        "dative": [
            "по пермскому краю"
        ],
        "genitive": [
            "пермского края"
        ],
        "locative": [
            "в пермском крае"
        ]
    },
    "32": {
        "dative": [
            "по хабаровскому краю"
        ],
        "genitive": [
            "хабаровского края"
        ],
        "locative": [
            "в хабаровском крае"
        ]
    },
    "33": {
        "dative": [
            "по амурской области"
        ],
        "genitive": [
            "амурской области"
        ],
        "locative": [
            "в амурской области"
        ]
    },
    "35": {
        "dative": [
            "по брянской области"
        ],
        "genitive": [
            "брянской области"
        ],
        "locative": [
            "в брянской области"
        ]
    },
    "36": {
        "dative": [
            "по владимирской области"
        ],
        "genitive": [
            "владимирской области"
        ],
        "locative": [
            "в владимирской области"
        ]
    },
    "37": {
        "dative": [
            "по архангельской области",
            "по архангельской области и ненецкому автономному округу"
        ],
        "genitive": [
            "архангельской области",
            "архангельской области и ненецкому автономному округу"
        ],
        "locative": [
            "в архангельской области",
            "в архангельской области и ненецком автономном округе"
        ]
    },
    "38": {
        "dative": [
            "по астраханской области"
        ],
        "genitive": [
            "астраханской области"
        ],
        "locative": [
            "в астраханской области"
        ]
    },
    "41": {
        "dative": [
            "по волгоградской области"
        ],
        "genitive": [
            "волгоградской области"
        ],
        "locative": [
            "в волгоградской области"
        ]
    },
    "42": {
        "dative": [
            "по вологодской области"
        ],
        "genitive": [
            "вологодской области"
        ],
        "locative": [
            "в вологодской области"
        ]
    },
    "43": {
        "dative": [
            "по воронежской области"
        ],
        "genitive": [
            "воронежской области"
        ],
        "locative": [
            "в воронежской области"
        ]
    },
    "44": {
        "dative": [
            "по забайкальскому краю"
        ],
        "genitive": [
            "забайкальскому краю"
        ],
        "locative": [
            "в забайкальском крае"
        ]
    },
    "45": {
        "dative": [
            "по иркутской области"
        ],
        "genitive": [
            "иркутской области"
        ],
        "locative": [
            "в иркутской области"
        ]
    },
    "46": {
        "dative": [
            "по калининградской области"
        ],
        "genitive": [
            "калининградской области"
        ],
        "locative": [
            "в калининградской области"
        ]
    },
    "47": {
        "dative": [
            "по республике калмыкия"
        ],
        "genitive": [
            "республики калмыкия"
        ],
        "locative": [
            "в республике калмыки"
        ]
    },
    "48": {
        "dative": [
            "по камчатскому краю"
        ],
        "genitive": [
            "камчатского края"
        ],
        "locative": [
            "в камчатском крае"
        ]
    },
    "50": {
        "dative": [
            "по кемеровской области",
            "по кемеровской области - кузбассу"
        ],
        "genitive": [
            "кемеровской области",
            "кемеровской области - кузбасса"
        ],
        "locative": [
            "в кемеровской области",
            "в кемеровской области - кузбассе"
        ]
    },
    "51": {
        "dative": [
            "по кировской области"
        ],
        "genitive": [
            "кировской области"
        ],
        "locative": [
            "в кировской области"
        ]
    },
    "53": {
        "dative": [
            "по костромской области"
        ],
        "genitive": [
            "костромской области"
        ],
        "locative": [
            "в костромской области"
        ]
    },
    "55": {
        "dative": [
            "по курской области"
        ],
        "genitive": [
            "курской области"
        ],
        "locative": [
            "в курской области"
        ]
    },
    "56": {
        "dative": [
            "по ленинградской области"
        ],
        "genitive": [
            "ленинградской области"
        ],
        "locative": [
            "в ленинградской области"
        ]
    },
    "57": {
        "dative": [
            "по липецкой области"
        ],
        "genitive": [
            "липецкой области"
        ],
        "locative": [
            "в липецкой области"
        ]
    },
    "58": {
        "dative": [
            "по магаданской области"
        ],
        "genitive": [
            "магаданской области"
        ],
        "locative": [
            "в магаданской области"
        ]
    },
    "59": {
        "dative": [
            "по республике дагестан"
        ],
        "genitive": [
            "республики дагестан"
        ],
        "locative": [
            "в республике дагестан"
        ]
    },
    "61": {
        "dative": [
            "по республике марий эл"
        ],
        "genitive": [
            "республики марий эл"
        ],
        "locative": [
            "в республике марий эл"
        ]
    },
    "62": {
        "dative": [
            "по республике мордовия"
        ],
        "genitive": [
            "республики мордовия"
        ],
        "locative": [
            "в республике мордови"
        ]
    },
    "63": {
        "dative": [
            "по москве",
            "по г.москве",
            "по г. москве"
        ],
        "genitive": [
            "москвы",
            "г.москвы",
            "г. москвы"
        ],
        "locative": [
            "в москве",
            "в г.москва",
            "в г. москва",
            "в г.москве",
            "в г. москве"
        ]
    },
    "64": {
        "dative": [
            "по московской области"
        ],
        "genitive": [
            "московской области"
        ],
        "locative": [
            "в московской области"
        ]
    },
    "65": {
        "dative": [
            "по мурманской области"
        ],
        "genitive": [
            "мурманской области"
        ],
        "locative": [
            "в мурманской области"
        ]
    },
    "66": {
        "dative": [
            "по нижегородской области"
        ],
        "genitive": [
            "нижегородской области"
        ],
        "locative": [
            "в нижегородской области"
        ]
    },
    "67": {
        "dative": [
            "по новгородской области"
        ],
        "genitive": [
            "новгородской области"
        ],
        "locative": [
            "в новгородской области"
        ]
    },
    "68": {
        "dative": [
            "по новосибирской области"
        ],
        "genitive": [
            "новосибирской области"
        ],
        "locative": [
            "в новосибирской области"
        ]
    },
    "69": {
        "dative": [
            "по омской области"
        ],
        "genitive": [
            "омской области"
        ],
        "locative": [
            "в омской области"
        ]
    },
    "70": {
        "dative": [
            "по орловской области"
        ],
        "genitive": [
            "орловской области"
        ],
        "locative": [
            "в орловской области"
        ]
    },
    "72": {
        "dative": [
            "по пензенской области"
        ],
        "genitive": [
            "пензенской области"
        ],
        "locative": [
            "в пензенской области"
        ]
    },
    "74": {
        "dative": [
            "по приморскому краю"
        ],
        "genitive": [
            "приморскому краю"
        ],
        "locative": [
            "в приморском крае"
        ]
    },
    "75": {
        "dative": [
            "по псковской области"
        ],
        "genitive": [
            "псковской области"
        ],
        "locative": [
            "в псковской области"
        ]
    },
    "76": {
        "dative": [
            "по ростовской области"
        ],
        "genitive": [
            "ростовской области"
        ],
        "locative": [
            "в ростовской области"
        ]
    },
    "77": {
        "dative": [
            "по самарской области"
        ],
        "genitive": [
            "самарской области"
        ],
        "locative": [
            "в самарской области"
        ]
    },
    "79": {
        "dative": [
            "по саратовской области"
        ],
        "genitive": [
            "саратовской области"
        ],
        "locative": [
            "в саратовской области"
        ]
    },
    "80": {
        "dative": [
            "по свердловской области"
        ],
        "genitive": [
            "свердловской области"
        ],
        "locative": [
            "в свердловской области"
        ]
    },
    "81": {
        "dative": [
            "по ставропольскому краю"
        ],
        "genitive": [
            "ставропольского края"
        ],
        "locative": [
            "в ставропольском крае"
        ]
    },
    "82": {
        "dative": [
            "по тамбовской области"
        ],
        "genitive": [
            "тамбовской области"
        ],
        "locative": [
            "в тамбовской области"
        ]
    },
    "84": {
        "dative": [
            "по тульской области"
        ],
        "genitive": [
            "тульской области"
        ],
        "locative": [
            "в тульской области"
        ]
    },
    "85": {
        "dative": [
            "по республике тыва",
            "по республике тува"
        ],
        "genitive": [
            "республики тыва",
            "республики тува"
        ],
        "locative": [
            "в республике тыва",
            "в республике тува"
        ]
    },
    "86": {
        "dative": [
            "по тюменской области"
        ],
        "genitive": [
            "тюменской области"
        ],
        "locative": [
            "в тюменской области"
        ]
    },
    "88": {
        "dative": [
            "по ульяновской области"
        ],
        "genitive": [
            "ульяновской области"
        ],
        "locative": [
            "в ульяновской области"
        ]
    },
    "89": {
        "dative": [
            "по челябинской области"
        ],
        "genitive": [
            "челябинской области"
        ],
        "locative": [
            "в челябинской области"
        ]
    },
    "90": {
        "dative": [
            "по чеченской республике"
        ],
        "genitive": [
            "чеченской республики"
        ],
        "locative": [
            "в чеченской республике"
        ]
    },
    "91": {
        "dative": [
            "по чувашской республике"
        ],
        "genitive": [
            "чувашской республики"
        ],
        "locative": [
            "в чувашской республике"
        ]
    },
    "92": {
        "dative": [
            "по республике саха (якутия)"
        ],
        "genitive": [
            "республики саха (якутия)"
        ],
        "locative": [
            "в республике саха (якутия)"
        ]
    },
    "93": {
        "dative": [
            "по еврейской автономной области"
        ],
        "genitive": [
            "еврейской автономной области"
        ],
        "locative": [
            "в еврейской автономной области"
        ]
    },
    "94": {
        "dative": [
            "по сахалинской области"
        ],
        "genitive": [
            "сахалинской области"
        ],
        "locative": [
            "в сахалинской области"
        ]
    },
    "95": {
        "dative": [
            "по чукотскому автономному округу"
        ],
        "genitive": [
            "чукотского автономного округа"
        ],
        "locative": [
            "в чукотском автономном округе"
        ]
    },
    "96": {
        "dative": [
            "по белгородской области"
        ],
        "genitive": [
            "белгородской области"
        ],
        "locative": [
            "в белгородской области"
        ]
    },
    "97": {
        "dative": [
            "по калужской области"
        ],
        "genitive": [
            "калужской области"
        ],
        "locative": [
            "в калужской области"
        ]
    },
    "98": {
        "dative": [
            "по курганской области"
        ],
        "genitive": [
            "курганской области"
        ],
        "locative": [
            "в курганской области"
        ]
    },
    "99": {
        "dative": [
            "по ивановской области"
        ],
        "genitive": [
            "ивановской области"
        ],
        "locative": [
            "в ивановской области"
        ]
    },
    "100": {
        "dative": [
            "по смоленской области"
        ],
        "genitive": [
            "смоленской области"
        ],
        "locative": [
            "в смоленской области"
        ]
    },
    "101": {
        "dative": [
            "по тверской области"
        ],
        "genitive": [
            "тверской области"
        ],
        "locative": [
            "в тверской области"
        ]
    },
    "102": {
        "dative": [
            "по ненецкому автономному округу"
        ],
        "genitive": [
            "ненецкого автономного округа"
        ],
        "locative": [
            "в ненецком автономном округе"
        ]
    },
    "103": {
        "dative": [
            "по рязанской области"
        ],
        "genitive": [
            "рязанской области"
        ],
        "locative": [
            "в рязанской области"
        ]
    },
    "104": {
        "dative": [
            "по ямало-ненецкому автономному округу"
        ],
        "genitive": [
            "ямало-ненецкого автономного округа"
        ],
        "locative": [
            "в ямало-ненецком автономном округе"
        ]
    },
    "105": {
        "dative": [
            "по оренбургской области"
        ],
        "genitive": [
            "оренбургской области"
        ],
        "locative": [
            "в оренбургской области"
        ]
    },
    "106": {
        "dative": [
            "по томской области"
        ],
        "genitive": [
            "томской области"
        ],
        "locative": [
            "в томской области"
        ]
    },
    "107": {
        "dative": [
            "по ярославской области"
        ],
        "genitive": [
            "ярославской области"
        ],
        "locative": [
            "в ярославской области"
        ]
    },
    "108": {
        "dative": [
            "по ханты-мансийскому автономному округу - югре"
        ],
        "genitive": [
            "ханты-мансийского автономного округа - югры"
        ],
        "locative": [
            "в ханты-мансийском автономном округе - югре"
        ]
    },
    "109": {
        "dative": [
            "по республике крым"
        ],
        "genitive": [
            "республики крым"
        ],
        "locative": [
            "в республике крым"
        ]
    },
    "110": {
        "dative": [
            "по г. севастополю",
            "по севастополю"
        ],
        "genitive": [
            "г. севастополя",
            "севастополя"
        ],
        "locative": [
            "в г. севастополе",
            "в севастополе"
        ]
    }
}


class TRegion:
    def __init__(self):
        self.id = None
        self.name = None
        self.short_name = None
        self.extra_short_name = None
        self.short_name_en = None
        self.extra_short_name_en  = None
        self.name_en = None
        self.name = None

    def from_json(self, r):
        self.id = int(r['id'])

        self.name = r['name']
        self.short_name = r['short_name']
        self.extra_short_name = r['extra_short_name']

        self.name_en = r['name_en']
        self.short_name_en = r['short_name_en']
        self.extra_short_name_en = r['extra_short_name_en']
        return self


class TRussianRegions:
    def __init__(self):
        self.regions = list()
        self.max_region_id = 0
        for region in RUSSIAN_REGIONS:
            r = TRegion().from_json(region)
            self.regions.append(r)
            self.max_region_id = max(self.max_region_id, r.id)
        self.region_name_to_region = dict()
        self.region_id_to_region = dict()
        for r in self.regions:
            self.region_name_to_region[r.name.lower().strip('*')] = r
            self.region_name_to_region[r.short_name.lower().strip('*')] = r
            self.region_id_to_region[r.id] = r

        self.all_forms = self.build_all_forms()

    def get_region_by_id(self, id: int):
        return self.region_id_to_region[id]

    def build_all_forms(self):
        all_forms = ahocorasick.Automaton()
        for name, region in self.region_name_to_region.items():
            all_forms.add_word(name, (region.id, name) )
        for region_id, forms in REGIONS_ALL_FORMS.items():
            region_id = int(region_id)
            for f in forms['dative']:
                all_forms.add_word(f, (region_id, f))
            for f in forms['genitive']:
                all_forms.add_word(f, (region_id, f))
            for f in forms['locative']:
                all_forms.add_word(f, (region_id, f))
        all_forms.make_automaton()
        return all_forms

    def get_region_in_nominative(self, russian_name):
        russian_name = russian_name.lower()
        if russian_name == "территории за пределами рф":
            return None
        elif russian_name.find('якутия') != -1:
            return self.region_id_to_region[92]
        elif russian_name.find('москва') != -1:
            return self.region_id_to_region[63]
        elif russian_name.find('санкт-петербург') != -1:
            return self.region_id_to_region[1]
        elif russian_name.find('севастополь') != -1:
            return self.region_id_to_region[110]
        elif russian_name.find('ханты') != -1:
            return self.region_id_to_region[108]
        elif russian_name.find('алания') != -1:
            return self.region_id_to_region[17]
        elif russian_name.find(' тыв') != -1:
            return self.region_id_to_region[85]
        elif russian_name.find('карачаево-') != -1:
            return self.region_id_to_region[11]
        elif russian_name.find('северная осетия') != -1:
            return self.region_id_to_region[17]
        return self.region_name_to_region.get(russian_name)

    def get_region_in_nominative_and_dative(self, russian_name):
        russian_name = normalize_whitespace(russian_name.strip().lower())
        for region_id, x in REGIONS_ALL_FORMS.items():
            for region_in_dative in x.get('dative', []):
                if russian_name.endswith(region_in_dative):
                    return self.region_id_to_region[int(region_id)]
        return self.get_region_in_nominative(russian_name)

    def get_region_all_forms(self, text, unknown_region=None):
        text = normalize_whitespace(text.strip().lower())
        best_region_id = unknown_region
        max_form_len = 0
        for pos, (region_id, form) in self.all_forms.iter(text):
            if len(form) > max_form_len:
                best_region_id = region_id
                max_form_len = len(form)
        return best_region_id


if __name__ == "__main__":
    import json
    for id, info in REGIONS_ALL_FORMS.items():
        info['locative'] = []
        for l in info['dative']:
            if l.startswith('по'):
                l = "в" +l[2:]
            info['locative'].append(l)
    print (json.dumps(REGIONS_ALL_FORMS, ensure_ascii=False, indent=4))
    sys.exit(1)
    regions = TRussianRegions()
    for x in sys.stdin:
        region = regions.get_region_in_nominative_and_dative(x)
        if region is None:
            print ("{} is not found".format(x.strip()))
        else:
            print("{} -> {}".format(x.strip(), region.name))