Handlebars.registerHelper('field', function() {
    return "";
});

function convert_json_from_tsv(jsonStr) {
    jsonStr = jsonStr.replace(/""/g, '"');
    jsonStr = jsonStr.replace(/^"/, '');
    jsonStr = jsonStr.replace(/"$/, '');
    return JSON.parse(jsonStr);
}

function ApplyContextToFile(file, context)
{
    var rawFile = new XMLHttpRequest();
    rawFile.open("GET", file, false);
    rawFile.onreadystatechange = function ()
    {
        if(rawFile.readyState === 4)
        {
            if(rawFile.status === 200 || rawFile.status == 0)
            {
                var allText = rawFile.responseText;
                let handleBarsTemplate = Handlebars.compile(allText);
                document.body.innerHTML = handleBarsTemplate(context);
            }
        }
    }
    rawFile.send(null);
    return rawFile;
}


let tsvLine = 'section-4391002	section-1908515	"{""sections"": [{""person"": {""name_raw"": ""Готько В. Я.""}, ""incomes"": [{""size"": 1345891, ""relative"": null}, {""size"": 85602, ""relative"": ""супруг(а)""}], ""vehicles"": [{""text"": ""а/м легковой Форд"", ""relative"": null}, {""text"": ""а/м легковой ВАЗ"", ""relative"": null}], ""real_estates"": [{""square"": 76, ""type_raw"": ""квартира"", ""owntype_raw"": ""В собственности"", ""relative"": null, ""country_raw"": ""Россия""}, {""square"": 50, ""type_raw"": ""квартира"", ""owntype_raw"": ""В собственности"", ""relative"": null, ""country_raw"": ""Россия""}, {""square"": 50, ""type_raw"": ""квартира"", ""owntype_raw"": ""В собственности"", ""relative"": ""супруг(а)"", ""country_raw"": ""Россия""}, {""square"": 50, ""type_raw"": ""квартира"", ""owntype_raw"": ""В собственности"", ""relative"": ""ребенок"", ""country_raw"": ""Россия""}], ""year"": ""2017"", ""source"": ""disclosures"", ""office"": ""Министерство обороны"", ""office_id"": 450, ""office_section_count"": 351383, ""surname_rank"": 58109}]}"	"{""sections"": [{""person"": {""name_raw"": ""Готько В.Я.""}, ""incomes"": [{""size"": 1564751, ""relative"": null}, {""size"": 90000, ""relative"": ""супруг(а)""}], ""vehicles"": [{""text"": ""а/м легковой Форд"", ""relative"": null}, {""text"": ""а/м легковой Форд"", ""relative"": null}], ""real_estates"": [{""square"": 76, ""type_raw"": ""квартира"", ""owntype_raw"": ""В собственности"", ""relative"": null, ""country_raw"": ""Россия""}, {""square"": 50, ""type_raw"": ""квартира"", ""owntype_raw"": ""В собственности"", ""relative"": null, ""country_raw"": ""Россия""}, {""square"": 50, ""type_raw"": ""квартира"", ""owntype_raw"": ""В собственности"", ""relative"": ""супруг(а)"", ""country_raw"": ""Россия""}, {""square"": 50, ""type_raw"": ""квартира"", ""owntype_raw"": ""В собственности"", ""relative"": ""ребенок"", ""country_raw"": ""Россия""}], ""year"": ""2018"", ""source"": ""disclosures"", ""office"": ""Министерство обороны"", ""office_id"": 450, ""office_section_count"": 351383, ""surname_rank"": 58109}]}"';
let items = tsvLine.split("\t");
let context = {
    id_left: items[0],
    id_right: items[1],
    json_left: convert_json_from_tsv(items[2]),
    json_right: convert_json_from_tsv(items[3])
};

ApplyContextToFile("task.html", context);
ShowDifferences(document);

