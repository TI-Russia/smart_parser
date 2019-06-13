//==== exact copy of myscript.js

function print_to_log(str, error) {
    document.getElementById("debug_console").value = str;
    alert(str);
}

function throw_and_log(error) {
    print_to_log("Ошибка! " + error);
    throw error;
}


document.last_selection_from_table = null;
function get_selection_from_table() {
    let text = "";
    if (typeof window.getSelection != "undefined") {
        document.last_selection_from_table = window.getSelection();
        text = window.getSelection().toString();
    }
    return text.trim();
}

function strike_selection() {
    let selection = document.last_selection_from_table;
    if (selection !=  null && selection.rangeCount) {
        let range = selection.getRangeAt(0);
        let strikeDiv = document.createElement('span');
        strikeDiv.style.textDecoration = "line-through";
        try {
            range.surroundContents(strikeDiv);
        }catch (err) {
            let anchorNode =  selection.anchorNode;
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

function read_main_json()
{
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
    document.table_versions.push(get_main_input_table().innerHTML);
}


function write_main_json(djs) {
    let json_elem = get_declaration_json_elem();
    save_undo_version();
    json_elem.value = JSON.stringify(djs, "", 4);
    moveCursorToEnd(json_elem);
    strike_selection();
    //json_elem.focus();
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

function show_modal_dialog(elementId, mainInputFieldId, closeFunction) {
    let text = get_selection_from_table();
    if (text !=  "") {
        document.getElementById(mainInputFieldId).value = text;
    }
    get_declaration_json_elem().style.display = 'none';
    document.getElementById(elementId).style.display = 'block';
    document.onkeydown = function(e) {
        if (e.key === "Escape") {closeFunction(false);}
        if (e.key === "Enter") {closeFunction(true);}
    };
}

function close_modal_dialog(elementId) {
    get_declaration_json_elem().style.display = 'inline';
    let elem = document.getElementById(elementId);
    elem.style.display = 'none';
    document.onkeydown = null;
}

function close_realty_modal_box(save_results=true){
    close_modal_dialog('RealtyTypeDialog');
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
            "country_raw"': "Россия"
        };
        person.real_estates.push(real_estate)
        write_main_json(djson);
    }
}
window.close_realty_modal_box = close_realty_modal_box;


function add_realty() {
    show_modal_dialog('RealtyTypeDialog', 'realty_type', close_realty_modal_box);
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
        person.incomes.push(income)
        write_main_json(djson);
    }
}
window.close_income_modal_box = close_income_modal_box;

function add_income() {
    show_modal_dialog('IncomeDialog', 'income_value', close_income_modal_box);
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
    write_main_json(djson);
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
        person.vehicles.push(vehicle)
        write_main_json(djson);
    }
}
window.close_vehicle_modal_box = close_vehicle_modal_box;

function add_vehicle() {
    show_modal_dialog('VehicleDialog', 'vehicle_value', close_vehicle_modal_box);
}
window.add_vehicle = add_vehicle;

function check_mandatory_fields()
{
    let djson = read_main_json();
    let p = get_last_person(djson);
    if (!('incomes' in p) || p.incomes.length == 0) {
        throw_and_log("Не найдено поле дохода (поле incomes)")
    }
}
window.check_mandatory_fields = check_mandatory_fields;
