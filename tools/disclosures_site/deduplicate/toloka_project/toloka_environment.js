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


let tsvLine = 'person-74671\tsection-193506\t"{""sections"": [{""person"": {""name_raw"": ""Васильев С.В."", ""role"": ""test role1""}, ""incomes"": [{""size"": 2335586.83, ""relative"": null}, {""size"": 624770.21, ""relative"": ""Супруг(а)""}], ""vehicles"": [{""text"": ""Nissan"", ""relative"": null}, {""text"": ""Honda"", ""relative"": ""Супруг(а)""}], ""real_estates"": [{""square"": 68.0, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": null, ""country_raw"": ""Россия""}, {""square"": 68.0, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": ""Супруг(а)"", ""country_raw"": ""Россия""}, {""square"": 68.0, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": ""Ребенок"", ""country_raw"": ""Россия""}, {""square"": 68.0, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": ""Ребенок"", ""country_raw"": ""Россия""}], ""years"": ""2014"", ""source"": ""declarator"", ""office"": ""Министерство обороны""}, {""person"": {""name_raw"": ""Васильев С.В."", ""role"": ""test role1""}, ""incomes"": [{""size"": 2335586.83, ""relative"": null}, {""size"": 624770.21, ""relative"": ""Супруг(а)""}], ""vehicles"": [{""text"": ""Nissan"", ""relative"": null}, {""text"": ""Honda"", ""relative"": ""Супруг(а)""}], ""real_estates"": [{""square"": 68.0, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": null, ""country_raw"": ""Россия""}, {""square"": 68.0, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": ""Супруг(а)"", ""country_raw"": ""Россия""}, {""square"": 68.0, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": ""Ребенок"", ""country_raw"": ""Россия""}, {""square"": 68.0, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": ""Ребенок"", ""country_raw"": ""Россия""}], ""years"": ""2013"", ""source"": ""declarator"", ""office"": ""Министерство обороны""}]}"\t"{""sections"": [{""person"": {""name_raw"": ""Васильев С.В."", ""role"": ""test role2""}, ""incomes"": [{""size"": 2022602.97, ""relative"": null}, {""size"": 758646.0, ""relative"": ""Супруг(а)""}], ""vehicles"": [{""text"": ""Nissan"", ""relative"": null}, {""text"": ""Акура MDX"", ""relative"": ""Супруг(а)""}], ""real_estates"": [{""square"": 97.3, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": null, ""country_raw"": ""Россия""}, {""square"": 97.3, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": ""Супруг(а)"", ""country_raw"": ""Россия""}, {""square"": 97.3, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": ""Ребенок"", ""country_raw"": ""Россия""}, {""square"": 97.3, ""type_raw"": ""Квартира"", ""owntype_raw"": ""В пользовании"", ""relative"": ""Ребенок"", ""country_raw"": ""Россия""}], ""years"": ""2015"", ""source"": ""declarator"", ""office"": ""Министерство обороны""}]}"\t\t\t0000020573--5c94caf38baa8101042d71ed\t3\t0';
let items = tsvLine.split("\t");
let context = {
    id_left: items[0],
    id_right: items[1],
    json_left: convert_json_from_tsv(items[2]),
    json_right: convert_json_from_tsv(items[3])
};

ApplyContextToFile("task.html", context);
ShowDifferences(document);

