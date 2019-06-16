// ===== start of toloka part =======

function print_to_log(str) {
    document.getElementById("debug_console").value = document.getElementById("debug_console").value + "\n" + str;
}

function throw_and_log(error) {
    print_to_log("Ошибка! " + error);
    alert(error);
    throw error;
}

function find_object_by_all_members(objList, obj) {
    for (let i = 0; i < objList.length; i++) {
        if (JSON.stringify(obj) == JSON.stringify(objList[i])) return true;
    }
    return false;
}

document.last_range_from_table = null;
function get_selection_from_table() {
    let text = "";
    if (typeof window.getSelection != "undefined") {
        document.last_range_from_table = window.getSelection().getRangeAt(0);
        document.last_anchor_node_from_table = window.getSelection().anchorNode;
        text = window.getSelection().toString();
    }
    return text.trim();
}

function add_html_table_row(inputList, table) {
    let row = table.insertRow();
    for (let k = 0; k < inputList.length; ++k) {
        let cell = row.insertCell();
        cell.innerHTML = inputList[k].Text;
        cell.colSpan = inputList[k].MergedColsCount;
    }
}

function input_json_to_html_table(jsonStr){
    jsonStr = jsonStr.replace(/\n/g, '<br/>')
    let data = JSON.parse(jsonStr);
    let res = '<span class="input_title">' + data.Title + "</span>";
    let tbl = document.createElement("table");
    tbl.className = "input_table";
    //tbl.style = 'border: 1px solid black; border-collapse: collapse; padding: 5px;'
    let thead = document.createElement("thead");
    for (let i = 0; i < data.Header.length; ++i) {
        add_html_table_row(data.Header[i], thead);
    }
    tbl.appendChild(thead);
    let tbody = document.createElement("tbody");
    for (let i = 0; i < data.Header.length; ++i) {
        add_html_table_row(data.Data[i], tbody);
    }
    tbl.appendChild(tbody);
    res += tbl.outerHTML;
    return res;
}

Handlebars.registerHelper('convert_json_to_html_helper', function(jsonStr) {
    return input_json_to_html_table(jsonStr);
});

function strike_selection() {
    let range = document.last_range_from_table;
    if (range !=  null) {
        let strikeDiv = document.createElement('span');
        strikeDiv.style.textDecoration = "line-through";
        try {
            range.surroundContents(strikeDiv);
        }catch (err) {
            let anchorNode = document.last_anchor_node_from_table;
            if (anchorNode.nodeType == Node.TEXT_NODE) {
                let p = anchorNode.parentNode;
                p.innerHTML = "<span style='text-decoration: line-through'>" + p.innerHTML + "</span>";
            }
        }
    }
}

function get_declaration_json_elem() {
    return document.getElementsByName("declaration_json")[0];
}

function moveCursorToEnd(el) {
    el.scrollTop = el.scrollHeight;
}

function read_main_json() {
    try {
        let json_elem = get_declaration_json_elem();
        let json_str =  json_elem.value;
        if (json_str == null || json_str.trim().length ==0) {
            json_str = '{"persons": [],"document": {}}';
        }
        let res = JSON.parse(json_str);
        //document.getElementById("debug_console").value = "Json was successfully parsed";
        return res;
    } catch (err) {
        throw_and_log (err)
    }
}

document.json_versions = [];
document.table_versions = [];

function get_main_input_table () {
    return document.getElementsByClassName("input_table")[0];
}

function save_undo_version(){
    let json_elem = get_declaration_json_elem();
    let json_text = json_elem.value;
    if (json_text == null) json_text =  "";
    if (document.json_versions.length > 0 && document.json_versions[document.json_versions.length - 1] == json_text) {
        return;
    }
    document.json_versions.push(json_text);
    let mainInputTable = get_main_input_table();
    document.table_versions.push(mainInputTable.innerHTML);
}


function write_main_json(djs, strikeSelection=true) {
    let json_elem = get_declaration_json_elem();
    save_undo_version();
    json_elem.value = JSON.stringify(djs, "", 4);
    moveCursorToEnd(json_elem);
    if (strikeSelection) {
        strike_selection();
    }
}

function undo() {
    if (document.json_versions.length == 0) {
        return;
    }
    let text = document.json_versions.pop();
    get_declaration_json_elem().value = text;
    get_main_input_table().innerHTML = document.table_versions.pop();

}
window.undo = undo;


function get_new_value(message){
    let text = get_selection_from_table();
    if (text == "") {
        text =  window.prompt(message);
    }
    if (text == null) {
        text = "";
    }
    return text.trim()
}

function get_radio_button_value (name) {
    let rad = document.getElementsByName(name);
    for (var i=0; i < rad.length; i++) {
        if (rad[i].checked) {
            return rad[i].value == "" ? null : rad[i].value;
        }
    }
    return null;
}

function get_radio_button_values(name) {
    let rad = document.getElementsByName(name);
    let values = []
    for (let i=0; i < rad.length; i++) {
        if (rad[i].value) {
            values.push( rad[i].value == "" ? null : rad[i].value );
        }
    }
    return values;
}

function delete_table_rows_before(table, rowIndex) {
    let headerSize = 0;
    for (let r=0; r < rowIndex; r++) {
        if (table.rows[headerSize].cells[0].tagName == "TH") {
            headerSize ++;
        }
        else {
            table.deleteRow(headerSize);
        }
    }
}

function delete_table_rows_after(table, rowIndex) {
    let rowsCount = table.rows.length;
    for (let r=rowIndex; r < rowsCount; r++) {
        table.deleteRow(rowIndex);
    }
}

function get_selected_row(selected_node, error_message) {
    let cell = selected_node;
    if (cell.tagName != "TD") {
        cell = cell.parentNode;
        if (cell.tagName != "TD") {
            throw_and_log(error_message);
        }
    }
    return cell.parentNode;
}


function show_modal_dialog(elementId) {
    let modalDlg = document.getElementById(elementId);
    let okButton = modalDlg.getElementsByClassName("ok_button")[0];
    let cancelButton = modalDlg.getElementsByClassName("cancel_button")[0];
    let mainInputField = modalDlg.getElementsByClassName("main_input_text_field")[0];
    let text = get_selection_from_table();
    if (text !=  "") {
        mainInputField.value = text;
    }
    get_declaration_json_elem().style.display = 'none';
    modalDlg.style.display = 'block';
    okButton.focus();
    document.onkeydown = function(e) {
        if (e.key === "Escape") {cancelButton.onclick(null);}
        if (e.key === "Enter") {okButton.onclick(null);};
    };
}

function close_modal_dialog(elementId) {
    get_declaration_json_elem().style.display = 'inline';
    let elem = document.getElementById(elementId);
    if (elem.style.display == "none") {
        // уже закрыто
        return false;
    }
    else {
        elem.style.display = 'none';
        document.onkeydown = null;
        return true;
    }
}


function get_last_person(djson) {
    if (djson.persons.length == 0) {
        throw_and_log ( new Error("Не нашли ни одного декларанта в выходном json ( persons )"));
    }
    let person = djson.persons[djson.persons.length - 1];
    if ( !('name_raw' in person) ) {
        throw_and_log ( new Error("У декларанта нет ФИО (поле 'name_raw')"));
    };
    return person;
}

function add_declarant() {
    let djson = read_main_json();
    let text = get_new_value("Введите ФИО");
    if (text.length > 50) {
        throw_and_log("ФИО слишком длинное (>50 символов)");
    }
    if (text != "") {
        if (djson.persons.length > 0) {
            djson.persons[0].name_raw = text;
        }
        else {
            djson.persons.push({'name_raw': text});
        }
        write_main_json(djson);
    }
}
window.add_declarant = add_declarant;

function check_json()
{
    let s = read_main_json();
    write_main_json(s);
}
window.check_json = check_json;


function add_declarant_role() {
    let djson = read_main_json();
    let person = get_last_person(djson);
    let text = get_new_value("Введите роль (должность):");
    if (text != "") {
        person.role = text;
        write_main_json(djson);
    }
}
window.add_declarant_role = add_declarant_role;

function isNormalYear(str) {
    let n = Math.floor(Number(str));
    return n !== Infinity && String(n) === str && n >= 2000 && n < 2030;
}

function add_year() {
    let djson = read_main_json();
    let person = get_last_person(djson);
    let text = get_new_value("Введите год");
    if (text != "") {
        if (!isNormalYear(text)) {
            throw_and_log ("Год - это число между 2000 и 2030")
        }
        person.year = text;
        write_main_json(djson);
    }
}
window.add_year = add_year;



function close_realty_modal_box(save_results=true){
    if (!close_modal_dialog('RealtyTypeDialog')) {
        return;
    }
    if (save_results) {
        let djson = read_main_json();
        let person = get_last_person(djson);
        if (!("real_estates" in person)) {
            person.real_estates = [];
        }
        let real_estate = {
            'text': document.getElementById('realty_type').value,
            "own_type":   get_radio_button_value ('owntype'),
            "relative":   get_radio_button_value ('whose_realty'),
            "country_raw": 'Россия'
        };
        person.real_estates.push(real_estate)
        write_main_json(djson);
    }
}
window.close_realty_modal_box = close_realty_modal_box;


function add_realty() {
    show_modal_dialog('RealtyTypeDialog');
}
window.add_realty = add_realty;

function add_realty_property(property_name, message) {
    let djson = read_main_json();
    let person = get_last_person(djson);
    if (!('real_estates' in person)) {
        throw_and_log ( new Error("У декларанта нет ни одной записи о недвижимости (поле 'real_estates')"));
    }
    let text = get_new_value(message);
    if (text != "") {
        person.real_estates[person.real_estates.length - 1][property_name] = text;
        write_main_json(djson);
    }

}
function add_square() {
    add_realty_property ('square', "Введите площадь:");
}
window.add_square = add_square;

function add_share() {
    add_realty_property ('share_amount', "Введите долю:");
}
window.add_share = add_share;


function add_country() {
    add_realty_property ('country_raw', "Введите страну:");
}
window.add_country = add_country;


function close_income_modal_box(save_results=true){
    close_modal_dialog('IncomeDialog');
    if (save_results) {
        let djson = read_main_json();
        let person = get_last_person(djson);
        if (!("incomes" in person)) {
            person.incomes = [];
        }
        let income  = {
            'size': document.getElementById('income_value').value,
            "relative":   get_radio_button_value ('whose_income')
        };
        if  (find_object_by_all_members(person.incomes, income)) {
            return;
        }
        person.incomes.push(income)
        write_main_json(djson);
    }
}
window.close_income_modal_box = close_income_modal_box;

function add_income() {
    show_modal_dialog('IncomeDialog');
}
window.add_income = add_income;


function cut_by_selection() {
    if (typeof window.getSelection == "undefined") {
        return;
    }
    let obj = window.getSelection();
    let start_row = get_selected_row (obj.anchorNode, "Не выделена ячейка таблицы");
    let last_row = get_selected_row (obj.focusNode, "Выделение выхоодит за пределы таблицы");
    let table = start_row.parentNode;

    let djson = read_main_json();
    let table_row_range = {'begin_row': start_row.rowIndex, 'last_row': last_row.rowIndex };
    if (!djson.persons.length) {
        let person = {'table_row_range': table_row_range}
        djson.persons.push(person);
    } else {
        let person = get_last_person(djson)
        person['table_row_range'] = table_row_range;
    }
    write_main_json(djson, false);
    // modify table after save_undo_version
    delete_table_rows_after(table, last_row.rowIndex + 1);
    delete_table_rows_before(table, start_row.rowIndex);

}
window.cut_by_selection = cut_by_selection;


function close_vehicle_modal_box(save_results=true){
    close_modal_dialog('VehicleDialog');
    if (save_results) {
        let djson = read_main_json();
        let person = get_last_person(djson);
        if (!("vehicles" in person)) {
            person.vehicles = [];
        }
        let vehicle  = {
            'text': document.getElementById('vehicle_value').value,
            "relative":   get_radio_button_value ('whose_vehicle')
        };
        if  (find_object_by_all_members(person.vehicles, vehicle)) {
            return;
        }
        person.vehicles.push(vehicle)
        write_main_json(djson);
    }
}
window.close_vehicle_modal_box = close_vehicle_modal_box;

function add_vehicle() {
    show_modal_dialog('VehicleDialog');
}
window.add_vehicle = add_vehicle;

function check_relative(field) {
    if (typeof field == "undefined") return;
    let values = get_radio_button_values('whose_realty')
    for (let i = 0; i < field.length; i++) {
        if  ( (field[i].relative != null)  && (values.indexOf(field[i].relative) == -1)){
            throw_and_log("bad relative in " + JSON.stringify(field[i], ""));
        };
    }
}

function check_real_estate_own_type(person) {
    if (typeof person.real_estates == "undefined") return;
    let values = get_radio_button_values('owntype')
    for (let i = 0; i < person.real_estates.length; i++) {
        let o = person.real_estates.own_type;
        if  ( values.indexOf(person.real_estates[i].own_type) == -1) {
            throw_and_log("bad own type in " + JSON.stringify(person.real_estates[i], ""));
        };
    }
}

function check_mandatory_fields(successMessage=true)
{
    let djson = read_main_json();
    let person = get_last_person(djson);
    if (!('incomes' in person) || person.incomes.length == 0) {
        throw_and_log("Не найдено поле дохода (поле incomes)")
    }
    if (!('year' in person) ) {
        throw_and_log("Не найдено поле года (year)")
    }
    check_relative(person.real_estates);
    check_relative(person.vehicles);
    check_relative(person.incomes);
    check_real_estate_own_type(person);
    if (successMessage)  alert("Успех!")
}
window.check_mandatory_fields = check_mandatory_fields;

document.onkeypress = function(e) {
    if (document.activeElement.name == "declaration_json") return;
    if (document.activeElement.tagName == "input") return;
    if ((e.key == "Н") || (e.key == "н") || (e.key == "y") || (e.key == "Y"))  {
        window.add_realty();
    }
    if ((e.key == "Ф") || (e.key == "ф") || (e.key == "A") || (e.key == "a"))  {
        window.add_declarant();
    }
    if ((e.key == "Р") || (e.key == "р") || (e.key == "H") || (e.key == "h"))  {
        window.add_declarant_role();
    }
    if ((e.key == "Д") || (e.key == "д") || (e.key == "l") || (e.key == "L"))  {
        window.add_income();
    }
    if ((e.key == "Г") || (e.key == "г") || (e.key == "U") || (e.key == "u"))  {
        window.add_year();
    }
    if ((e.key == "Т") || (e.key == "т") || (e.key == "N") || (e.key == "n"))  {
        window.add_vehicle();
    }
    if ((e.key == "П") || (e.key == "п") || (e.key == "G") || (e.key == "g"))  {
        window.add_square();
    }


};

// ===== end of toloka part =======

Handlebars.registerHelper('field', function() {
    let elem = document.createElement('textarea');
    elem.style.width = '100%';
    elem.rows = 20;
    elem.name = 'declaration_json'
    return elem.outerHTML;
});

let taskSource = document.getElementsByClassName("main_task_table")[0];
let handleBarsTemplate = Handlebars.compile(taskSource.innerHTML);
let inputJson =  "{\"Title\":\"1 \nСВЕДЕНИЯ \nо доходах, об имуществе и обязательствах имущественного характера лиц, замещающих должности в Федеральной службе исполнения наказаний, \nи членов их семей за отчетный период с 1 января 2012 г. по 31 декабря 2012 г. \n \n\",\"DataStart\":2,\"DataEnd\":16,\"Header\":[[{\"MergedColsCount\":1,\"Text\":\"Фамилия, имя, отчество \n\"},{\"MergedColsCount\":1,\"Text\":\"Должность \n\"},{\"MergedColsCount\":1,\"Text\":\"Общая сумма декларированног о годового дохода за 2012 год (руб.) \n\"},{\"MergedColsCount\":3,\"Text\":\"Перечень объектов недвижимого имущества, принадлежащих на праве собственности или находящихся в пользовании \n\"},{\"MergedColsCount\":1,\"Text\":\"Перечень транспортных средств, \nпринадлежащих на праве \nсобственности \n(вид, марка) \n\"}],[{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"Вид объектов недвижимости \n\"},{\"MergedColsCount\":1,\"Text\":\"Площадь \n(кв.м.) \n\"},{\"MergedColsCount\":1,\"Text\":\"Страна располож ения \n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"}]],\"Data\":[[{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":5,\"Text\":\"Руководство территориальных органов и образовательных учреждений ФСИН России \n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"}],[{\"MergedColsCount\":1,\"Text\":\"Заев Ю.Ю. \n\"},{\"MergedColsCount\":1,\"Text\":\"Начальник \nУФСИН России по Республике \nАдыгея (Адыгея) \n\"},{\"MergedColsCount\":1,\"Text\":\"795 449,40 \n\"},{\"MergedColsCount\":1,\"Text\":\"земельный участок \n(собственность, общая долевая) \n\"},{\"MergedColsCount\":1,\"Text\":\"490,0 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"автомобиль легковой Киа Спортаж \n\"}],[{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"квартира \n(пользование) \n\"},{\"MergedColsCount\":1,\"Text\":\"48,0 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"}],[{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"гаражный бокс \n(собственность) \n\"},{\"MergedColsCount\":1,\"Text\":\"22,4 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"}],[{\"MergedColsCount\":1,\"Text\":\"Супруга \n\"},{\"MergedColsCount\":1,\"Text\":\" \n\"},{\"MergedColsCount\":1,\"Text\":\"84 000,00 \n\"},{\"MergedColsCount\":1,\"Text\":\"квартира \n(собственность) \n\"},{\"MergedColsCount\":1,\"Text\":\"63,3 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"- \n\"}],[{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"квартира \n(пользование) \n\"},{\"MergedColsCount\":1,\"Text\":\"48,0 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"}],[{\"MergedColsCount\":1,\"Text\":\"Черанев А.Г. \n\"},{\"MergedColsCount\":1,\"Text\":\"Заместитель начальника \nУФСИН России по Республике \nАдыгея (Адыгея) \n\"},{\"MergedColsCount\":1,\"Text\":\"708 732,00 \n\"},{\"MergedColsCount\":1,\"Text\":\"земельный участок (собственность) \n\"},{\"MergedColsCount\":1,\"Text\":\"741,0 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"автомобиль легковой Тойота Королла \n\"}],[{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"квартира \n(собственность) \n\"},{\"MergedColsCount\":1,\"Text\":\"61,1 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"}],[{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"},{\"MergedColsCount\":1,\"Text\":\"квартира \n(пользование) \n\"},{\"MergedColsCount\":1,\"Text\":\"53,4 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"\n\"}],[{\"MergedColsCount\":1,\"Text\":\"супруга \n\"},{\"MergedColsCount\":1,\"Text\":\" \n\"},{\"MergedColsCount\":1,\"Text\":\"248 300,00 \n\"},{\"MergedColsCount\":1,\"Text\":\"жилой дом \n(собственность) \n\"},{\"MergedColsCount\":1,\"Text\":\"44,4 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"- \n\"}],[{\"MergedColsCount\":1,\"Text\":\"Чиназиров А.В. \n\"},{\"MergedColsCount\":1,\"Text\":\"Заместитель начальника \nУФСИН России по Республике \nАдыгея (Адыгея) \n\"},{\"MergedColsCount\":1,\"Text\":\"510 551,22 \n\"},{\"MergedColsCount\":1,\"Text\":\"квартира \n(собственность, 1/4 доли) \n\"},{\"MergedColsCount\":1,\"Text\":\"61,2 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"автомобиль легковой Опель Вектра \n\"}],[{\"MergedColsCount\":1,\"Text\":\"Супруга \n\"},{\"MergedColsCount\":1,\"Text\":\" \n\"},{\"MergedColsCount\":1,\"Text\":\"380 521,68 \n\"},{\"MergedColsCount\":1,\"Text\":\"квартира \n(собственность, 1/4 доли) \n\"},{\"MergedColsCount\":1,\"Text\":\"61,2 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"- \n\"}],[{\"MergedColsCount\":1,\"Text\":\"Дочь \n\"},{\"MergedColsCount\":1,\"Text\":\" \n\"},{\"MergedColsCount\":1,\"Text\":\"- \n\"},{\"MergedColsCount\":1,\"Text\":\"квартира \n(собственность, 1/4 доли) \n\"},{\"MergedColsCount\":1,\"Text\":\"61,2 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"- \n\"}],[{\"MergedColsCount\":1,\"Text\":\"Сын \n\"},{\"MergedColsCount\":1,\"Text\":\" \n\"},{\"MergedColsCount\":1,\"Text\":\"- \n\"},{\"MergedColsCount\":1,\"Text\":\"квартира \n(собственность, 1/4 доли) \n\"},{\"MergedColsCount\":1,\"Text\":\"61,2 \n\"},{\"MergedColsCount\":1,\"Text\":\"Россия \n\"},{\"MergedColsCount\":1,\"Text\":\"- \n\"}]]}";
let context = {input_id: "1", input_json: inputJson, declaration_json:"hkfhggkfjhgfk"};
let html  = handleBarsTemplate(context);
taskSource.innerHTML = html;

