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

function find_object_by_relative(objList, relative) {
    for (let i = 0; i < objList.length; i++) {
        if (relative == objList[i].relative) return true;
    }
    return false;
}

document.last_range_from_table = null;
document.last_anchor_node_from_table = null;
document.last_focus_node_from_table = null;

function normalize_string(s) {
    s = s.replace(/\s+/g, ' ');
    s = s.trim();
    return s;
}

function get_selection_from_table() {
    let selection = window.getSelection();
    if (selection == null) return "";
    if  (selection.rangeCount == 0) return "";
    document.last_range_from_table = selection.getRangeAt(0);
    document.last_anchor_node_from_table = selection.anchorNode;
    document.last_focus_node_from_table = selection.focusNode;
    return  normalize_string(selection.toString());
}

function add_html_table_row(inputList, table) {
    let row = table.insertRow();
    for (let k = 0; k < inputList.length; ++k) {
        let cell = row.insertCell();
        let text = inputList[k].t;
        text = text.replace(/\n/g, "<br/>");
        cell.innerHTML = text;
        cell.colSpan = inputList[k].mc;
    }
}

function input_json_to_html_table(jsonStr) {
    if (typeof window.getSelection == "undefined") {
        alert ("К сожалению, ваш браузер не поддерживается!")
        return;
    }
    let data;
    try {
        data = JSON.parse(jsonStr);
    } catch (err) {
        alert ("Не могу распарсить входной json. Программисты накосячили! Напишите нам об этом. " + err);
        throw err;
    }
    let res = '<span class="input_title">' + data.Title + "</span>";
    let tbl = document.createElement("table");
    tbl.className = "input_table";
    let thead = document.createElement("thead");
    for (let i = 0; i < data.Header.length; ++i) {
        add_html_table_row(data.Header[i], thead);
    }
    if (data.Section != null) {
        for (let i = 0; i < data.Section.length; ++i) {
            add_html_table_row(data.Section[i], thead);
        }
    }
    tbl.appendChild(thead);
    let tbody = document.createElement("tbody");
    tbody.setAttribute("id", "input_table_data")
    for (let i = 0; i < data.Data.length; ++i) {
        add_html_table_row(data.Data[i], tbody);
    }
    let lastRow = tbody.insertRow();
    let cell = lastRow.insertCell();
    cell.innerHTML = "конец таблицы";

    tbl.appendChild(tbody);
    res += tbl.outerHTML;
    return res;
}

Handlebars.registerHelper('convert_json_to_html_helper', function(jsonStr) {
    return input_json_to_html_table(jsonStr);
});


Handlebars.registerHelper('owner_types', function(radio_button_name, image_div_name ) {
    let ownerTypeTemplate =  "<label> <input type=\"radio\" name={{name}}  class=\"ownertype_class\" value=\"{{value}}\" " +
        "                           onclick=\"window.show_icon('{{image}}', '{{image_div_name}}')\"\n" +
        "                           {{#if checked}} checked {{/if}}\" />{{{title}}}</label> <br/><br/>";
    let ownerTypes = [
        {'value': "", title:"Д<u>е</u>кларант", image:"http://aot.ru/images/declarator/declarant.png", "checked":"checked"},
        {'value': "Супруг(а)", title:"<u>С</u>упруг(а)", image:"http://aot.ru/images/declarator/spouse.png"},
        {'value': "Ребенок", title:"Ре<u>б</u>енок", image:"http://aot.ru/images/declarator/child.png"}
    ];
    let template = Handlebars.compile(ownerTypeTemplate);
    let html = "";
    for (let i=0; i < ownerTypes.length; i++) {
        let context = ownerTypes[i];
        context['name'] = radio_button_name;
        context['image_div_name'] = image_div_name;
        html += template(context);
    }
    return html;
});

function is_copied_span(elem) {
    return elem.nodeType == Node.ELEMENT_NODE && elem.className == 'copied_text';
}

function html_to_text_plain(element) {
    if (element.nodeType == Node.TEXT_NODE) {
        return element.textContent;
    }
    if (element.nodeType == Node.ELEMENT_NODE && element.tagName == "BR") {
        return "\n";
    }
    // assert false
    return element.textContent;
}

function html_to_text_plain_or_span(element) {
    if (!is_copied_span(element)) {
        return html_to_text_plain(element);
    }
    let text = "";
    for (let i = 0; i < element.childNodes.length; i++) {
        text += html_to_text_plain(element.childNodes[i]);
    }
    return text;
}


function get_striked_situation(tdElement) {
    let spans = [];
    let text = "";
    for (let i = 0; i < tdElement.childNodes.length; i++) {
         let child = tdElement.childNodes[i];
         let child_text = html_to_text_plain_or_span(child);
         let copied = is_copied_span(child);
         for (let k=0; k < child_text.length; k++)  {
             spans.push(copied);
         }
         text += child_text;
     }
     return {"spans": spans, "text": text}
}

//  copies Range.toString  but convert <br> to \n
function getSelectionCharacterOffsetWithin(tdElement, range) {
    let text = "";
    let begin = -1;
    let end = -1;
    for (let i = 0; i < tdElement.childNodes.length; i++) {
        let child = tdElement.childNodes[i];
        if (child  == range.startContainer) {
            begin = text.length + range.startOffset;
        }
        if (child  == range.endContainer) {
            end = text.length + range.endOffset;
        }
        if (tdElement  == range.startContainer && i == range.startOffset ) {
            begin = text.length;
        }
        if (tdElement  == range.endContainer && i == range.endOffset) {
            end = text.length;
        }
        text += html_to_text_plain_or_span(child);
    }
    if (begin == -1) {
        begin = 0;
    }
    if (end == -1) {
        end = text.length;
    }
    return { start: begin, end: end };
}


function strike_range_in_span_array(tdElement, range, strike_spans) {
    let r = getSelectionCharacterOffsetWithin (tdElement, range);
    for (let i = r.start; i  < r.end;i++ ) {
        strike_spans[i] = true;
    }
}


function strike_range_outside_table(range) {
    let strikeDiv = document.createElement('span');
    strikeDiv.style.textDecoration = "line-through";
    strikeDiv.className = "copied_text";
    try {
        range.surroundContents(strikeDiv);
    }catch (err) {
    }
}

function copy_char(text, i, outputText) {
    if (text[i] == "\n") {
        outputText += "<br/>";
    }
    else {
        outputText += text[i];
    }
    return outputText;
}

function strike_spans(tdElement, strike_situation) {
    let i = 0;
    let text = strike_situation.text;
    let spans = strike_situation.spans;
    let outputHtml = "";
    while (i <  spans.length) {
        if (spans[i] == false) {
            outputHtml =  copy_char(text, i, outputHtml)
            i++;
        }
        else {
            outputHtml += "<span class='copied_text' style='text-decoration: line-through'>";
            while (i <  spans.length && spans[i]) {
                outputHtml =  copy_char(text, i, outputHtml)
                i++;
            }
            outputHtml += "</span>";
        }
    }
    tdElement.innerHTML = outputHtml;
}

function strike_selection() {
    let range = document.last_range_from_table;
    if (range ==  null) return;
    let parent = document.last_anchor_node_from_table;
    let tdElement  = null;
    while (parent != null) {
        if (parent.tagName == "TD") {
            tdElement = parent;
        }
        if (parent.id == "input_table_data") {
            break;
        }
        parent = parent.parentNode;
    }
    if  (parent == null || tdElement == null) {
        strike_range_outside_table(range);
    } else {
        let situation = get_striked_situation(tdElement);
        strike_range_in_span_array(tdElement, range, situation.spans);
        strike_spans(tdElement, situation);
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
        let res = JSON.parse(json_str);
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
    let json_text = document.json_versions.pop();
    get_declaration_json_elem().value = json_text;
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
    return normalize_string(text)
}

function get_radio_button_value (name) {
    let rad = document.getElementsByName(name);
    for (let i=0; i < rad.length; i++) {
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

function delete_table_rows_before(tbody, rowIndex) {
    for (let r=0; r < rowIndex; r++) {
        tbody.deleteRow(0);
    }
}

function delete_table_rows_after(tbody, rowIndex) {
    let rowsCount = tbody.rows.length;
    for (let r=rowIndex; r < rowsCount; r++) {
        tbody.deleteRow(rowIndex);
    }
}

function get_selected_row(selected_node, error_message=null) {
    let cell = selected_node;
    if (cell.tagName != "TD") {
        cell = cell.parentNode;
        if (cell.tagName != "TD") {
            if (error_message != null) throw_and_log(error_message);
            return null;
        }
    }
    return cell.parentNode;
}
function get_selected_row_index() {
    let row = get_selected_row(document.last_anchor_node_from_table);
    if (row == null) return -1;
    return row.rowIndex;
}

window.current_modal_dlg = null;
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
    window.current_modal_dlg = modalDlg;
}

function close_modal_dialog(elementId) {
    get_declaration_json_elem().style.display = 'inline';
    window.current_modal_dlg = null;
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
    if ( !('person' in person) ) {
        throw_and_log ( new Error("У декларанта нет ФИО (нет зоны person c полем 'name_raw')"));
    };
    if ( !('name_raw' in person.person) ) {
        throw_and_log ( new Error("У декларанта нет ФИО (поле 'name_raw')"));
    };
    return person;
}

function starts_with_a_digit(s) {
    return ('0123456789'.indexOf(s[0]) != -1 );
}

//================================= BUTTONS ======================================


function check_has_name() {
    if (get_declaration_json_elem().value.trim() == "") {
        throw_and_log("Сначала нужно найти начало декларации (кнопка 'ФИО' или 'Отдел')");
    }
}

function check_cut_after() {
    let djson = read_main_json();
    let person = get_last_person(djson);

    if (!('cut_after' in person)) {
        throw_and_log("Cначала найдите начало следующего декларанта, выделите и нажмите кнопку 'Обрезать'. " +
            "Если не видите  начала следующего, обрезайте по строке, в которой написано 'конец таблицы'");
    }
}

function cut_by_selection(cutAfter) {
    let selection = window.getSelection();
    if (selection.rangeCount == 0) return;
    let startNode = selection.getRangeAt(0).startContainer;
    let start_row = get_selected_row (startNode, "Не выделена ячейка таблицы");
    let tbody = start_row.parentNode;
    let table = tbody.parentNode;
    let headerSize = table.tHead.rows.length;
    // modify table after save_undo_version
    if (cutAfter) {
        let djson = read_main_json();
        djson.persons[0].cut_after = 1;
        write_main_json(djson, false);
        delete_table_rows_after(tbody, start_row.rowIndex  - headerSize);
    } else {
        delete_table_rows_before(tbody, start_row.rowIndex - headerSize);
    }
}

function set_declarant_end  () {
    check_has_name();
    cut_by_selection(true);
}
window.set_declarant_end = set_declarant_end;

function create_or_read_json () {
    if (get_declaration_json_elem().value.trim().length > 0) {
        return read_main_json();
    } else {
        return {
            persons: [{}],
            document: {},
        }
    }
}

function add_declarant() {
    let text = get_new_value("Введите ФИО");
    if (text.length == 0) return;
    if (text.length > 50) {
        throw_and_log("ФИО слишком длинное (>50 символов)");
    }
    if (text.indexOf(" ") == -1 && text.indexOf(".") == -1) {
        throw_and_log("Однословных ФИО не бывает");
    }
    if (starts_with_a_digit(text)) {
        throw_and_log("Недопустимый ФИО");
    }

    if (text == "") return;
    let djson = create_or_read_json();
    let  cutBefore = false;
    if (!('person' in djson.persons[0])) {
        cutBefore = true;
        djson.persons[0].person  = {}
    }
    djson.persons[0].person.name_raw = text;
    write_main_json(djson);
    if (cutBefore) cut_by_selection(false);
}
window.add_declarant = add_declarant;


function add_declarant_role() {
    check_cut_after();
    let djson = read_main_json();
    let person = get_last_person(djson);
    let text = get_new_value("Введите роль (должность):");
    if (text == "") return;
    if (starts_with_a_digit(text)) {
        throw_and_log("плохой тип недвижимости: " + text);
    }
    person.person.role = text;
    write_main_json(djson);
}
window.add_declarant_role = add_declarant_role;

function add_realties_number() {
    check_cut_after();
    let djson = read_main_json();
    let person = get_last_person(djson);
    let text =  window.prompt("Введите количество объектов недвижимости:");
    if (text != "") {
        let n = Math.floor(Number(text));
        if (n == null || n == Infinity || Number.isNaN(n)) {
            throw_and_log("не могу прочитать число!")
        }
        person.real_estates_count = n;
        write_main_json(djson);
    }
}
window.add_realties_number = add_realties_number;


function isNormalYear(str) {
    let n = Math.floor(Number(str));
    if (n==-1) {
        return true;
    }
    return n !== Infinity && String(n) === str && n >= 2000 && n < 2030;
}

function add_year() {
    check_cut_after();
    let djson = read_main_json();
    let person = get_last_person(djson);
    let text = get_new_value("Введите год");
    if (text != "") {
        if (!isNormalYear(text)) {
            throw_and_log ("Год - это число между 2000 и 2030 или -1 (не найден)")
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
        let type_raw = normalize_string( document.getElementById('realty_type').value );
        if (type_raw.length == 0) return;
        if (starts_with_a_digit(type_raw)) {
            throw_and_log("плохой тип недвижимости: " + type_raw);
        }
        let real_estate = {
            'type_raw': type_raw,
            "own_type_by_column":   get_radio_button_value ('realty_own_type_by_column'),
            "relative":   get_radio_button_value ( 'realty_owner_type'),
            "country_raw": 'Россия',
            "source_row": get_selected_row_index()
        };
        person.real_estates.push(real_estate)
        write_main_json(djson);
    }
}
window.close_realty_modal_box = close_realty_modal_box;


function add_realty() {
    let djson = read_main_json();
    let person = get_last_person(djson);
    if (!('real_estates_count' in person)) {
        throw_and_log("Сначала посчитайте кол-во объектов недвижимости и нажмите кнопку 'Кол-во', чтобы ничего не забыть")
    }
    show_modal_dialog('RealtyTypeDialog');
}
window.add_realty = add_realty;

function check_has_real_estate() {
    let djson = read_main_json();
    let person = get_last_person(djson);
    if (!('real_estates' in person)) {
        throw_and_log ( new Error("У декларанта нет ни одной записи о недвижимости (поле 'real_estates')"));
    }
}

function add_square() {
    check_has_real_estate();
    let djson = read_main_json();
    let person = get_last_person(djson);
    let text = get_new_value("Введите площадь:");
    if (text == "") return;
    if (!starts_with_a_digit(text)) {
        throw_and_log("Площадь должна начинаться с числа")
    }
    person.real_estates[person.real_estates.length - 1]['square_raw'] = text;
    write_main_json(djson);
}
window.add_square = add_square;

function add_own_type() {
    check_has_real_estate();
    let djson = read_main_json();
    let person = get_last_person(djson);
    let text = get_new_value("Введите вид владения:");
    if (text == "") return;
    if (starts_with_a_digit(text)) {
        throw_and_log("Недопустимый подтип владения")
    }
    person.real_estates[person.real_estates.length - 1]['own_type_raw'] = text;
    write_main_json(djson);
}
window.add_own_type = add_own_type;


function add_country() {
    check_has_real_estate();
    let djson = read_main_json();
    let person = get_last_person(djson);
    let text = get_new_value("Введите страну:");
    if (text == "") return;
    if (starts_with_a_digit(text)) {
        throw_and_log("Недопустимое название страны")
    }
    let lower_t = text.toLowerCase();
    if  (lower_t == "российская федерация" || lower_t == "рф" || lower_t == "россия")  {
        text = "Россия";
        alert("страна и так по умолчанию - Россия, не нажимайте эту кнопку, если недвижимость в РФ");
    }
    person.real_estates[person.real_estates.length - 1]["country_raw"] = text;
    write_main_json(djson);
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
        let income_str = normalize_string(document.getElementById('income_value').value);
        if (income_str == "") return;
        if (!starts_with_a_digit(income_str)) {
            throw_and_log("Недопустимое значение дохода")
        }
        let relative = get_radio_button_value ('income_owner_type')
        if (relative != null && income_str[0] == '0') {
            throw_and_log( "Почему вы не читали инструкцию? Нулевой доход у родственников заполнять не надо")
        }
        let income  = {
            'size_raw': income_str,
            "source_row": get_selected_row_index(),
            "relative":   get_radio_button_value ('income_owner_type')
        };
        if  (find_object_by_all_members(person.incomes, income)) {
            throw_and_log("Попытка повторно добаавить ту же информацию")
        }
        if (find_object_by_relative(person.incomes, income.relative)) {
            throw_and_log("Попытка повторно приписать доход одной и той же персоне")
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


function close_vehicle_modal_box(save_results=true){
    close_modal_dialog('VehicleDialog');
    if (save_results) {
        let djson = read_main_json();
        let person = get_last_person(djson);
        if (!("vehicles" in person)) {
            person.vehicles = [];
        }
        let vehicle_str = normalize_string(document.getElementById('vehicle_value').value);
        if (vehicle_str.length == 0) return;
        let vehicle  = {
            'text': vehicle_str,
            "source_row": get_selected_row_index(),
            "relative":   get_radio_button_value ('vehicle_owner_type')
        };
        if  (find_object_by_all_members(person.vehicles, vehicle)) {
            throw_and_log("Попытка повторно добаавить ту же информацию")
        }
        person.vehicles.push(vehicle)
        write_main_json(djson);
    }
}
window.close_vehicle_modal_box = close_vehicle_modal_box;

function add_vehicle() {
    check_cut_after();
    show_modal_dialog('VehicleDialog');
}
window.add_vehicle = add_vehicle;

function check_relative(field) {
    if (typeof field == "undefined") return;
    let values = get_radio_button_values('vehicle_owner_type')
    for (let i = 0; i < field.length; i++) {
        if  ( (field[i].relative != null)  && (values.indexOf(field[i].relative) == -1)){
            throw_and_log("bad relative in " + JSON.stringify(field[i], ""));
        };
    }
}


function check_source_row_to_relative_one_field(field, source_row_2_relative) {

    if (field == null) return;

    for (let i = 0; i < field.length; i++) {
        let r = field[i];
        if ('source_row' in r && r.source_row != -1) {
            if (r.source_row in source_row_2_relative) {
                if (r.relative != source_row_2_relative[r.source_row]) {
                    throw_and_log("Из одной и той же строки (" + r.source_row +
                        ") вы приписали информацию разным персонам (родственникам или декларантам, поле relative). Кажется, так не бывает." +
                        " Если случилось, пришлите нам пример, а это задание пропустите. В одной строке входной таблицы у всех поле relative должен быть одинаковым");
                }
            }
            source_row_2_relative[r.source_row] = r.relative;
        }
        if ('source_row' in r) delete r.source_row;
    }
}

function check_source_row_to_relative(person) {
    let source_row_2_relative = {};
    check_source_row_to_relative_one_field(person.real_estates, source_row_2_relative);
    check_source_row_to_relative_one_field(person.incomes, source_row_2_relative);
    check_source_row_to_relative_one_field(person.vehicles, source_row_2_relative);
}

function check_real_estate_records(person) {
    check_real_estates_count(person);

    if (typeof person.real_estates == "undefined") return;

    let values = get_radio_button_values('realty_own_type_by_column')
    let has_own_type_raw = false;
    let own_type_by_columns = new Set();
    for (let i = 0; i < person.real_estates.length; i++) {
        let r = person.real_estates[i];
        if  ( r.own_type_by_column != null && values.indexOf(r.own_type_by_column) == -1) {
            let s =  "Неправильный own_type_by_column: ";
            s += r.own_type_by_column;
            s +=  "\n\n" + JSON.stringify(r, "");
            throw_and_log(s);
        };
        if (!('square_raw'  in r)) {
            let s = "нет площади у недвижимости:\n";
            s += JSON.stringify(r, "");
            s += "\n\nПоставьте \"square_raw\": -1, если ее реально нет во входной таблице";
            throw_and_log(s);
        }

        if (r.own_type_raw != null) {
            if (r.own_type_by_column == "В собственности") {
                has_own_type_raw = true;
            }
        }
        own_type_by_columns.add(r.own_type_by_column);
    }
    if  (own_type_by_columns.has(null) && own_type_by_columns.size != 1) {
        throw_and_log("Если есть смешанная колонка недвижимости, то других нет");
    }

    for (let i = 0; i < person.real_estates.length; i++) {
        let r = person.real_estates[i];
        if (has_own_type_raw  && r.own_type_by_column == "В собственности" && r.own_type_raw == null) {
            throw_and_log("В одном из объектов недвижимости, котораый в собственности, вы приписали подтип владения ("
                + r.own_type_raw + "), а в другом не приписали. Либо есть эта колонка, либо нет.");
        }
        if (r.own_type_by_column == "В пользовании" && r.own_type_raw != null) {
            throw_and_log("Мы сами не видели декларация, где указаны подтип владения государственных квартир. Если вы нашли, пожалуйста, "
                + " пришлите нам пример задания, а это задания пропустите.");
        }
    }
}

function create_text_for_real_estate_type(person) {
    if (typeof person.real_estates == "undefined") return;
    for (let i = 0; i < person.real_estates.length; i++) {
        let r = person.real_estates[i];
        if ('text' in r) continue; // already converted
        if (!('own_type_raw' in r)) {
            if (!('type_raw' in r)) {
                throw_and_log("cannot find 'type_raw' in " + JSON.stringify(r, ""));
            }
            r.text = r.type_raw;
            delete r.type_raw;
        } else {
            r.text = r.type_raw;
        }
    }
}


function check_real_estates_count(person) {
    if (!('real_estates_count' in person)) {
        throw_and_log("Не найдено поле real_estates_count (нажмите кнопку 'Кол-во')");
    }
    if (person.real_estates_count == 0 && !('real_estates' in person)) {
        return;
    }
    if (person.real_estates_count != person.real_estates.length) {
        throw_and_log("Поле real_estates_count (кнопка 'Кол-во') не равно числу добавленных объектов недвижимости")
    }
}

function sort_json_by_keys(o) {
    const isObject = (v) => ('[object Object]' === Object.prototype.toString.call(v));

    if (Array.isArray(o)) {
        return o.sort().map(v => isObject(v) ? sort_json_by_keys(v) : v);
    } else if (isObject(o)) {
        return Object
            .keys(o)
            .sort()
            .reduce((a, k) => {
                if (isObject(o[k])) {
                    a[k] = sort_json_by_keys(o[k]);
                } else if (Array.isArray(o[k])) {
                    a[k] = o[k].map(v => isObject(v) ? sort_json_by_keys(v) : v);
                } else {
                    a[k] = o[k];
                }

                return a;
            }, {});
    }

    return o;
}

function compare_string(a,b) {
    if (a == null) a = "";
    if (b == null) b = "";
    return  a.localeCompare(b);
}

function sort_declaration_json(person) {
    if ('incomes' in person) {
        person.incomes.sort(function(a, b) {
            return compare_string(a['size_raw'], b['size_raw']);
        })
    }
    if ('real_estates' in person) {
        person.real_estates.sort(function(a, b) {
            if  (a['relative'] !=  b['relative']) return compare_string(a['relative'], b['relative']);
            if  (a['own_type_by_column'] !=  b['own_type_by_column']) return compare_string(a['own_type_by_column'], b['own_type_by_column']);
            if  (a['square_raw'] !=  b['square_raw']) return compare_string(a['square_raw'], b['square_raw']);
            return compare_string(a['text'], b['text']);
        })
    }
    if ('vehicles' in person) {
        person.vehicles.sort(function(a, b) {
            if  (a['relative'] !=  b['relative']) return compare_string(a['relative'], b['relative']);
            return compare_string(a['text'], b['text']);
        })
    }
    return sort_json_by_keys(person);
}

function find_unstriked_text(elem) {
    for (let i = 0; i < elem.childNodes.length; i++) {
        let child = elem.childNodes[i];
        if (is_copied_span(child)) continue;
        let trim_text  = child.textContent.replace(/\s+/g, "");
        if (trim_text != "") return trim_text;
    }
    return '';
}

function check_table_strike_text() {
    let tbody = document.getElementById("input_table_data");
    for (let r=0; r < tbody.rows.length; r++) {
        for (let c=0; c < tbody.rows[r].cells.length; c++) {
            let cell = tbody.rows[r].cells[c];
            let html = cell.innerHTML;
            if (html != null  &&  html.indexOf("copied_text") != -1) {
                let left_text = find_unstriked_text(cell);
                if (left_text != "") {
                    throw_and_log("В ячейке есть зачеркнутый и незачеркнутый текст, наверно, вы забыли перенести: " +
                        '"'+ left_text+ '". Содержимое ячейки: \n' +  cell.textContent);
                }
            }
        }
    }

}

function check_mandatory_fields(successMessage=true) {
    check_has_name();

    let djson = read_main_json();
    if (djson.persons_empty == 1) {
        if (successMessage)  alert("Успех!")
        return;
    }
    check_table_strike_text();

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
    create_text_for_real_estate_type(person);
    check_real_estate_records(person);
    check_source_row_to_relative(person);
    djson.persons[0] = sort_declaration_json(person);
    write_main_json(djson, false);
    if (successMessage)  alert("Успех!")
}
window.check_mandatory_fields = check_mandatory_fields;

function  switch_radio_in_modal(modalDlg, className, radioBtnValue) {
    if (modalDlg == null) return;
    let inputs = modalDlg.getElementsByClassName(className);
    for (let i =0; i < inputs.length; i++) {
            if (inputs[i].value == radioBtnValue)  {
                inputs[i].checked = true;
                inputs[i].onclick(null);
            }

    }
}

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
    if ((e.key == "П") || (e.key == "п") || (e.key == "G") || (e.key == "g")) {
        window.add_square();
    }
    if ((e.key == "О") || (e.key == "о") || (e.key == "J") || (e.key == "j")) {
        window.set_declarant_end();
    }
    if ((e.key == "Л") || (e.key == "л") || (e.key == "K") || (e.key == "k")) {
        window.add_department();
    }
    if ((e.key == "В") || (e.key == "в") || (e.key == "D") || (e.key == "d")) {
        window.add_own_type();
    }
    if ((e.key == "К") || (e.key == "к") || (e.key == "R") || (e.key == "r")) {
        window.add_realties_number();
    }
    if ((e.key == "Е") || (e.key == "е") || (e.key == "T") || (e.key == "t")) {
        switch_radio_in_modal(window.current_modal_dlg, "ownertype_class", "");
    }
    if ((e.key == "С") || (e.key == "с") || (e.key == "C") || (e.key == "c")) {
        switch_radio_in_modal(window.current_modal_dlg,"ownertype_class", "Супруг(а)");
    }
    if ((e.key == "Б") || (e.key == "б") || (e.key == ",") || (e.key == "<")) {
        switch_radio_in_modal(window.current_modal_dlg,"ownertype_class", "Ребенок");
    }

};


function show_icon(url, placeId) {
    let elem = document.getElementsByName(placeId)[0];
    elem.innerHTML = ''
    let img = document.createElement('img');
    img.src = url;
    elem.appendChild(img);
}
window.show_icon = show_icon;


function add_department() {
    let text = get_new_value("Введите отдел (организацию)");
    if (text.length == 0) return;
    if (starts_with_a_digit(text))  {
        throw_and_log("Недопустимый департамент " + text);
    }
    let djson = create_or_read_json();;
    let person = djson.persons[0]
    if (!('person' in person))  person.person = {};
    person.person.department = text;
    write_main_json(djson);
    cut_by_selection(false);
}
window.add_department = add_department;

String.prototype.hashCodeNoSpaces = function() {
    let hash = 0;
    let s = this.replace(/[\s():;,".-]/g, "")
    for (let i = 0; i < s.length; i++) {
        let chr   = s.charCodeAt(i);
        hash  = ((hash << 5) - hash) + chr;
        hash |= 0;
    }
    return hash;
};


function on_toloka_validate(solutions) {
    check_mandatory_fields(false);

    let text = get_declaration_json_elem().value;
    let djson = JSON.parse(text);
    if (!('persons_empty' in djson)) {
        if ('cut_after' in djson.persons[0]) {
            delete djson.persons[0].cut_after;
        }
    }
    let jsonStr = JSON.stringify(djson);
    let hashCode = jsonStr.hashCodeNoSpaces();
    if (solutions != null) {
        solutions.output_values["declaration_json"] = jsonStr;
        solutions.output_values["declaration_hashcode"] = hashCode;
    }
}


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
//let tsvLine = '96b9b248c792469e480540f53b364371__43_63\t"{""Title"":""Сведения\\n о доходах, расходах, об имуществе и обязательствах имущественного характера, \\nпредставленные руководителями федеральных государственных учреждений, находящихся в ведении \\nМинистерства труда и социальной защиты Российской Федерации\\n(с учетом уточнений, представленных до 30 сентября 2013 года)\\nза отчетный период с 1 января 2012 года по 31 декабря 2012 года, \\nподлежащих размещению на официальном сайте Министерства труда и социальной защиты Российской Федерации \\nв соответствии порядком размещения указанных сведений на официальных сайтах федеральных государственных органов, утвержденным Указом Президента Российской Федерации от 8 июля 2013 г. № 613\\n\\n"",""InputFileName"":""documents/6353.docx"",""DataStart"":43,""DataEnd"":63,""Header"":[[{""mc"":1,""mr"":2,""r"":0,""c"":0,""t"":""Фамилия, имя, отчество\\n\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":1,""t"":""Должность\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":2,""t"":""Общая сумма декларированного годового дохода за 2012 г. (руб.)\\n""},{""mc"":3,""mr"":1,""r"":0,""c"":3,""t"":""Перечень объектов недвижимого имущества,\\nпринадлежащих на праве собственности или находящихся в пользовании\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":6,""t"":""Перечень транспортных средств, принадлежащих на праве собственности\\n(вид, марка)\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":7,""t"":""Сведения об источниках получения средств, за счет которых совершена сделка по приобретению объектов недвижимого имущества, транспортных средств, ценных бумаг, акций (долей участия, паев в уставных (складочных) капиталах организаций)*\\n""}],[{""mc"":1,""mr"":1,""r"":1,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":3,""t"":""Вид объектов недвижимости\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":4,""t"":""Площадь\\n(кв.м)\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":5,""t"":""Страна расположения\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":6,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":7,""t"":""\\n""}]],""Section"":[],""Data"":[[{""mc"":1,""mr"":1,""r"":43,""c"":0,""t"":""Супруг \\n""},{""mc"":1,""mr"":1,""r"":43,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":2,""t"":""1 328 817,5\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":3,""t"":""Квартира (долевая собственность 1/2)\\n\\nГараж (безвозмездное пользование)\\n\\nЖилой дом (безвозмездное пользование)\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":4,""t"":""93,8\\n\\n\\n35,0\\n\\n\\n104,0\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":5,""t"":""Россия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":6,""t"":""а/м Опель Антара\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":44,""c"":0,""t"":""Сын \\n""},{""mc"":1,""mr"":1,""r"":44,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":2,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":3,""t"":""Квартира (безвозмездное пользование)\\n\\nЖилой дом (безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":4,""t"":""93,8\\n\\n\\n\\n104,0\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":45,""c"":0,""t"":""Гаркуша Людмила Генриховна\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":1,""t"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Иркутской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":45,""c"":2,""t"":""3 260 700,05\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":3,""t"":""Земельный участок дачный\\n(собственность)\\n\\nЗемельный участок для ведения ЛПХ\\n(собственность)\\n\\n\\nЗемельный участок под ИЖС\\n(собственность)\\n\\nКвартира\\n(собственность)\\n\\nДом дачный\\n(собственность)\\n\\nГараж-бокс\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":4,""t"":""\\n1339,0\\n\\n\\n\\n143000,0\\n\\n\\n\\n\\n1204,0\\n\\n\\n\\n59,2\\n\\n\\n25,0\\n\\n\\n19,4\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":5,""t"":""\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":6,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":46,""c"":0,""t"":""\\nГичкун \\nЛюдмила Петровна\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":1,""t"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Волгоградской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":46,""c"":2,""t"":""2 082 008,53\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":3,""t"":""Земельный участок дачный\\n(собственность)\\n\\nКвартира (долевая собственность 3/4)\\n\\nГараж-бокс (собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":4,""t"":""569,0\\n\\n\\n\\n55,8\\n\\n\\n21,4\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":47,""c"":0,""t"":""Гнутов \\nВалерий Павлович\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Кировской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":47,""c"":2,""t"":""2 120 367,0\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":3,""t"":""Земельный участок дачный\\n(собственность)\\n\\nЗемельный участок (собственность)\\n\\nКвартира (долевая собственность 1/2)\\n\\nГараж (долевая собственность 1/2)\\n\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":4,""t"":""400,0\\n\\n\\n\\n1710,0\\n\\n\\n75,7\\n\\n\\n24,0\\n\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":48,""c"":0,""t"":""Супруга \\n""},{""mc"":1,""mr"":1,""r"":48,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":2,""t"":""2 009 446,0\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":3,""t"":""Земельный участок дачный\\n(долевая собственность 1/2)\\n\\n\\nКвартира (долевая собственность 1/2)\\n\\nКвартира (долевая собственность 1/3)\\n\\nГараж (долевая собственность 1/2)\\n\\n\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":4,""t"":""\\n400,0\\n\\n\\n\\n\\n\\n75,7\\n\\n\\n30,0\\n\\n\\n24,0\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":5,""t"":""\\nРоссия\\n\\n\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":6,""t"":""\\nа/м Нива-шевроле (собственность)\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":49,""c"":0,""t"":""\\nГоловнин \\nИгорь Владимирович\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Костромской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":49,""c"":2,""t"":""1 160 685,0\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":3,""t"":""Квартира\\n(собственность)\\n\\nКвартира (долевая собственность 1/2)\\n\\nКвартира (долевая собственность 1/3)\\n\\nГаражный бокс (собственность)\\n\\nНежилое помещение (долевая собственность 1/2)\\n\\n\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":4,""t"":""30,1\\n\\n\\n107,3\\n\\n\\n102,2\\n\\n\\n43,0\\n\\n\\n19,8\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":5,""t"":""Россия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":6,""t"":""а/м КИА-Каренс (собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":50,""c"":0,""t"":""Супруга \\n""},{""mc"":1,""mr"":1,""r"":50,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":2,""t"":""185 420,0\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":3,""t"":""Квартира (долевая собственность 1/2)\\n\\n\\nНежилое помещение (долевая собственность 1/2)\\n\\n\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":4,""t"":""107,3\\n\\n\\n\\n19,8\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":51,""c"":0,""t"":""Сын \\n""},{""mc"":1,""mr"":1,""r"":51,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":2,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":3,""t"":""Квартира (долевая собственность 1/3)\\n\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":4,""t"":""102,2\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":52,""c"":0,""t"":""\\nГончаренко Александр Георгиевич\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Алтайскому краю\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":52,""c"":2,""t"":""3 916 781,05 \\n(в том числе доход от продажи транспортного средства)\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":3,""t"":""Земельный участок (совместная собственность)\\n\\nЗемельный участок (совместная собственность)\\n\\nЗемельный участок\\nдачный (совместная собственность)\\n\\nКвартира (долевая собственность 1/5)\\n\\n\\nКвартира (совместная собственность)\\n\\nКвартира (совместная собственность)\\n\\nДом дачный (совместная собственность)\\n\\nГараж (совместная собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":4,""t"":""1000,0\\n\\n\\n\\n1456,0\\n\\n\\n\\n500,0\\n\\n\\n\\n88,0\\n\\n\\n\\n46,4\\n\\n\\n30,9\\n\\n\\n48,0\\n\\n\\n\\n18,0\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":6,""t"":""а/м Тойота Хайлендер\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":53,""c"":0,""t"":""Супруга \\n""},{""mc"":1,""mr"":1,""r"":53,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":2,""t"":""630 864,32\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":3,""t"":""Земельный участок (совместная собственность)\\n\\nЗемельный участок (совместная собственность)\\n\\nЗемельный участок\\nдачный (совместная собственность)\\n\\n\\nКвартира (долевая собственность 1/5)\\n\\nКвартира (совместная собственность)\\n\\nКвартира (совместная собственность)\\n\\nДом дачный (совместная собственность)\\n\\nГараж (совместная собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":4,""t"":""\\n1000,0\\n\\n\\n\\n1456,0\\n\\n\\n\\n500,0\\n\\n\\n\\n\\n88,0\\n\\n\\n46,4\\n\\n\\n30,9\\n\\n\\n48,0\\n\\n\\n\\n18,0\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":5,""t"":""\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":6,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":54,""c"":0,""t"":""\\nГородцова Надежда Павловна\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":1,""t"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Ямало-Ненецкому автономному округу\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":54,""c"":2,""t"":""4 307 635,19\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":3,""t"":""Квартира\\n(собственность)\\n\\nКвартира\\n(собственность)\\n\\nКвартира\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":4,""t"":""58,8\\n\\n\\n72,2\\n\\n\\n90,3\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":5,""t"":""Россия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":55,""c"":0,""t"":""Григорьева Татьяна Михайловна\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":1,""t"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Псковской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":55,""c"":2,""t"":""1 970 930,0\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":3,""t"":""Квартира\\n(безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":4,""t"":""60,5\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":56,""c"":0,""t"":""Супруг \\n""},{""mc"":1,""mr"":1,""r"":56,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":2,""t"":""674 320,0\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":3,""t"":""Квартира\\n(собственность)\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":4,""t"":""60,5\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":6,""t"":""а/м Хонда CRV (собственность)\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":57,""c"":0,""t"":""Громов Владимир Николаевич  \\n""},{""mc"":1,""mr"":1,""r"":57,""c"":1,""t"":""Директор\\nФКОУ СПО \\""Кинешемский технологический техникум-интернат\\"" Минтруда России\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":2,""t"":""1 345 953,24\\n(в том числе доход от продажи транспортного средства)\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":3,""t"":""Квартира (долевая собственность 1/2)\\n\\nКвартира (долевая собственность 1/2)\\n\\n\\nЗемельный участок (безвозмездное пользование)\\n\\nКвартира\\n(безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":4,""t"":""\\n77,9\\n\\n\\n82,0\\n\\n\\n\\n600,0\\n\\n\\n\\n64,4\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":5,""t"":""\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":6,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":58,""c"":0,""t"":""\\nСупруга \\n""},{""mc"":1,""mr"":1,""r"":58,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":2,""t"":""1 304 626, 54\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":3,""t"":""Квартира (долевая собственность 1/2)\\n\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":4,""t"":""82,0\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":6,""t"":""а/м ХОНДА CR-V (собственность)\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":59,""c"":0,""t"":""Сын \\n""},{""mc"":1,""mr"":1,""r"":59,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":2,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":3,""t"":""Квартира (безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":4,""t"":""82,0\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":60,""c"":0,""t"":""Гулина \\nОльга Владимировна\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Республике Мордовия\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":60,""c"":2,""t"":""926446,66\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":3,""t"":""Земельный участок под ИЖС (собственность)\\n\\nЗемельный участок под многоквартирным домом (собственность общая долевая 34/1000)\\n\\nЖилой дом (собственность)\\n\\nПомещение нежилое (собственность)\\n\\nКвартира (безвозмездное пользование)\\n\\nКомната (безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":4,""t"":""953,0\\n\\n\\n\\n248,91\\n\\n\\n\\n\\n\\n226,3\\n\\n\\n137,4\\n\\n\\n111,9\\n\\n\\n\\n18,0\\n\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":61,""c"":0,""t"":""\\nСупруг \\n""},{""mc"":1,""mr"":1,""r"":61,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":2,""t"":""1722069,54\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":3,""t"":""Земельный участок под ИЖС (собственность)\\n\\nДом жилой (собственность)\\n\\nКвартира \\n(безвозмездное пользование)\\n\\nКомната (безвозмездное пользование)\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":4,""t"":""1000,0\\n\\n\\n\\n56,7\\n\\n\\n111,9\\n\\n\\n\\n18,0\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":6,""t"":""а/м Ситроен С5\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":62,""c"":0,""t"":""Данжинов \\nБаатр \\nПурвеевич\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Республике Калмыкия\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":62,""c"":2,""t"":""1 053 843,68\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":3,""t"":""Дом жилой (собственность)\\n\\nЗемельный участок (аренда)\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":4,""t"":""197,6\\n\\n\\n691,0\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":5,""t"":""Россия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":7,""t"":""-\\n""}]]}"\t"{""persons"":[{""incomes"":[{""relative"":null,""size_raw"":""3 260 700,05""}],""person"":{""name_raw"":""Гаркуша Людмила Генриховна"",""role"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе ФКУ \\""ГБ МСЭ по Иркутской области\\"" Минтруда России""},""real_estates"":[{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""1204,0"",""text"":""Земельный участок под ИЖС (собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""1339,0"",""text"":""Земельный участок дачный(собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""143000,0"",""text"":""Земельный участок для ведения ЛПХ (собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""19,4"",""text"":""Гараж-бокс (собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""25,0"",""text"":""Дом дачный (собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""59,2"",""text"":""Квартира (собственность)""}],""real_estates_count"":6,""year"":""2012""}],""document"":{}}"\tЭто довольно редкий тип файла, но он есть. У Гаркуши - шесть отдельных квартир в смешанной колонке, приходится копировать части текста из ячеек, а не полностью всю ячейку. Каждому объекту надо сопоставить площадь.  Очень осторожно выделяйте, включая  подтип владения и нажимайте кнопку \'Недвижимость\'.   Год - 2012, а не 2013';
//let tsvLine = '96b9b248c792469e480540f53b364371__43_63\t"{""Title"":""adfdf"",""InputFileName"":""documents/6353.docx"",""DataStart"":43,""DataEnd"":63,""Header"":[[{""mc"":1,""mr"":2,""r"":0,""c"":0,""t"":""Фамилия\\n, имя, отчество\\n\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":1,""t"":""Должность\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":2,""t"":""Общая сумма декларированного годового дохода за 2012 г. (руб.)\\n""},{""mc"":3,""mr"":1,""r"":0,""c"":3,""t"":""Перечень объектов недвижимого имущества,\\nпринадлежащих на праве собственности или находящихся в пользовании\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":6,""t"":""Перечень транспортных средств, принадлежащих на праве собственности\\n(вид, марка)\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":7,""t"":""Сведения об источниках получения средств, за счет которых совершена сделка по приобретению объектов недвижимого имущества, транспортных средств, ценных бумаг, акций (долей участия, паев в уставных (складочных) капиталах организаций)*\\n""}],[{""mc"":1,""mr"":1,""r"":1,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":3,""t"":""Вид объектов недвижимости\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":4,""t"":""Площадь\\n(кв.м)\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":5,""t"":""Страна расположения\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":6,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":7,""t"":""\\n""}]],""Section"":[],""Data"":[[{""mc"":1,""mr"":1,""r"":43,""c"":0,""t"":""Супруг \\n""},{""mc"":1,""mr"":1,""r"":43,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":2,""t"":""1 328 817,5\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":3,""t"":""Квартира (долевая собственность 1/2)\\n\\nГараж (безвозмездное пользование)\\n\\nЖилой дом (безвозмездное пользование)\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":4,""t"":""93,8\\n\\n\\n35,0\\n\\n\\n104,0\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":5,""t"":""Россия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":6,""t"":""а/м Опель Антара\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":43,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":44,""c"":0,""t"":""Сын \\n""},{""mc"":1,""mr"":1,""r"":44,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":2,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":3,""t"":""Квартира (безвозмездное пользование)\\n\\nЖилой дом (безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":4,""t"":""93,8\\n\\n\\n\\n104,0\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":44,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":45,""c"":0,""t"":""Гаркуша Людмила Генриховна\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":1,""t"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Иркутской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":45,""c"":2,""t"":""3 260 700,05\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":3,""t"":""Земельный участок дачный\\n(собственность)\\n\\nЗемельный участок для ведения ЛПХ\\n(собственность)\\n\\n\\nЗемельный участок под ИЖС\\n(собственность)\\n\\nКвартира\\n(собственность)\\n\\nДом дачный\\n(собственность)\\n\\nГараж-бокс\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":4,""t"":""\\n1339,0\\n\\n\\n\\n143000,0\\n\\n\\n\\n\\n1204,0\\n\\n\\n\\n59,2\\n\\n\\n25,0\\n\\n\\n19,4\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":5,""t"":""\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":6,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":45,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":46,""c"":0,""t"":""\\nГичкун \\nЛюдмила Петровна\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":1,""t"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Волгоградской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":46,""c"":2,""t"":""2 082 008,53\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":3,""t"":""Земельный участок дачный\\n(собственность)\\n\\nКвартира (долевая собственность 3/4)\\n\\nГараж-бокс (собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":4,""t"":""569,0\\n\\n\\n\\n55,8\\n\\n\\n21,4\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":46,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":47,""c"":0,""t"":""Гнутов \\nВалерий Павлович\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Кировской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":47,""c"":2,""t"":""2 120 367,0\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":3,""t"":""Земельный участок дачный\\n(собственность)\\n\\nЗемельный участок (собственность)\\n\\nКвартира (долевая собственность 1/2)\\n\\nГараж (долевая собственность 1/2)\\n\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":4,""t"":""400,0\\n\\n\\n\\n1710,0\\n\\n\\n75,7\\n\\n\\n24,0\\n\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":47,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":48,""c"":0,""t"":""Супруга \\n""},{""mc"":1,""mr"":1,""r"":48,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":2,""t"":""2 009 446,0\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":3,""t"":""Земельный участок дачный\\n(долевая собственность 1/2)\\n\\n\\nКвартира (долевая собственность 1/2)\\n\\nКвартира (долевая собственность 1/3)\\n\\nГараж (долевая собственность 1/2)\\n\\n\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":4,""t"":""\\n400,0\\n\\n\\n\\n\\n\\n75,7\\n\\n\\n30,0\\n\\n\\n24,0\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":5,""t"":""\\nРоссия\\n\\n\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":6,""t"":""\\nа/м Нива-шевроле (собственность)\\n""},{""mc"":1,""mr"":1,""r"":48,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":49,""c"":0,""t"":""\\nГоловнин \\nИгорь Владимирович\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Костромской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":49,""c"":2,""t"":""1 160 685,0\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":3,""t"":""Квартира\\n(собственность)\\n\\nКвартира (долевая собственность 1/2)\\n\\nКвартира (долевая собственность 1/3)\\n\\nГаражный бокс (собственность)\\n\\nНежилое помещение (долевая собственность 1/2)\\n\\n\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":4,""t"":""30,1\\n\\n\\n107,3\\n\\n\\n102,2\\n\\n\\n43,0\\n\\n\\n19,8\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":5,""t"":""Россия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":6,""t"":""а/м КИА-Каренс (собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":49,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":50,""c"":0,""t"":""Супруга \\n""},{""mc"":1,""mr"":1,""r"":50,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":2,""t"":""185 420,0\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":3,""t"":""Квартира (долевая собственность 1/2)\\n\\n\\nНежилое помещение (долевая собственность 1/2)\\n\\n\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":4,""t"":""107,3\\n\\n\\n\\n19,8\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":50,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":51,""c"":0,""t"":""Сын \\n""},{""mc"":1,""mr"":1,""r"":51,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":2,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":3,""t"":""Квартира (долевая собственность 1/3)\\n\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":4,""t"":""102,2\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":51,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":52,""c"":0,""t"":""\\nГончаренко Александр Георгиевич\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Алтайскому краю\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":52,""c"":2,""t"":""3 916 781,05 \\n(в том числе доход от продажи транспортного средства)\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":3,""t"":""Земельный участок (совместная собственность)\\n\\nЗемельный участок (совместная собственность)\\n\\nЗемельный участок\\nдачный (совместная собственность)\\n\\nКвартира (долевая собственность 1/5)\\n\\n\\nКвартира (совместная собственность)\\n\\nКвартира (совместная собственность)\\n\\nДом дачный (совместная собственность)\\n\\nГараж (совместная собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":4,""t"":""1000,0\\n\\n\\n\\n1456,0\\n\\n\\n\\n500,0\\n\\n\\n\\n88,0\\n\\n\\n\\n46,4\\n\\n\\n30,9\\n\\n\\n48,0\\n\\n\\n\\n18,0\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":6,""t"":""а/м Тойота Хайлендер\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":52,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":53,""c"":0,""t"":""Супруга \\n""},{""mc"":1,""mr"":1,""r"":53,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":2,""t"":""630 864,32\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":3,""t"":""Земельный участок (совместная собственность)\\n\\nЗемельный участок (совместная собственность)\\n\\nЗемельный участок\\nдачный (совместная собственность)\\n\\n\\nКвартира (долевая собственность 1/5)\\n\\nКвартира (совместная собственность)\\n\\nКвартира (совместная собственность)\\n\\nДом дачный (совместная собственность)\\n\\nГараж (совместная собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":4,""t"":""\\n1000,0\\n\\n\\n\\n1456,0\\n\\n\\n\\n500,0\\n\\n\\n\\n\\n88,0\\n\\n\\n46,4\\n\\n\\n30,9\\n\\n\\n48,0\\n\\n\\n\\n18,0\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":5,""t"":""\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":6,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":53,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":54,""c"":0,""t"":""\\nГородцова Надежда Павловна\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":1,""t"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Ямало-Ненецкому автономному округу\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":54,""c"":2,""t"":""4 307 635,19\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":3,""t"":""Квартира\\n(собственность)\\n\\nКвартира\\n(собственность)\\n\\nКвартира\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":4,""t"":""58,8\\n\\n\\n72,2\\n\\n\\n90,3\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":5,""t"":""Россия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":54,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":55,""c"":0,""t"":""Григорьева Татьяна Михайловна\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":1,""t"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Псковской области\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":55,""c"":2,""t"":""1 970 930,0\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":3,""t"":""Квартира\\n(безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":4,""t"":""60,5\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":55,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":56,""c"":0,""t"":""Супруг \\n""},{""mc"":1,""mr"":1,""r"":56,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":2,""t"":""674 320,0\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":3,""t"":""Квартира\\n(собственность)\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":4,""t"":""60,5\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":6,""t"":""а/м Хонда CRV (собственность)\\n""},{""mc"":1,""mr"":1,""r"":56,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":57,""c"":0,""t"":""Громов Владимир Николаевич  \\n""},{""mc"":1,""mr"":1,""r"":57,""c"":1,""t"":""Директор\\nФКОУ СПО \\""Кинешемский технологический техникум-интернат\\"" Минтруда России\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":2,""t"":""1 345 953,24\\n(в том числе доход от продажи транспортного средства)\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":3,""t"":""Квартира (долевая собственность 1/2)\\n\\nКвартира (долевая собственность 1/2)\\n\\n\\nЗемельный участок (безвозмездное пользование)\\n\\nКвартира\\n(безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":4,""t"":""\\n77,9\\n\\n\\n82,0\\n\\n\\n\\n600,0\\n\\n\\n\\n64,4\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":5,""t"":""\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":6,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":57,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":58,""c"":0,""t"":""\\nСупруга \\n""},{""mc"":1,""mr"":1,""r"":58,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":2,""t"":""1 304 626, 54\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":3,""t"":""Квартира (долевая собственность 1/2)\\n\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":4,""t"":""82,0\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":6,""t"":""а/м ХОНДА CR-V (собственность)\\n""},{""mc"":1,""mr"":1,""r"":58,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":59,""c"":0,""t"":""Сын \\n""},{""mc"":1,""mr"":1,""r"":59,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":2,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":3,""t"":""Квартира (безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":4,""t"":""82,0\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":5,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":59,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":60,""c"":0,""t"":""Гулина \\nОльга Владимировна\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Республике Мордовия\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":60,""c"":2,""t"":""926446,66\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":3,""t"":""Земельный участок под ИЖС (собственность)\\n\\nЗемельный участок под многоквартирным домом (собственность общая долевая 34/1000)\\n\\nЖилой дом (собственность)\\n\\nПомещение нежилое (собственность)\\n\\nКвартира (безвозмездное пользование)\\n\\nКомната (безвозмездное пользование)\\n\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":4,""t"":""953,0\\n\\n\\n\\n248,91\\n\\n\\n\\n\\n\\n226,3\\n\\n\\n137,4\\n\\n\\n111,9\\n\\n\\n\\n18,0\\n\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":60,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":61,""c"":0,""t"":""\\nСупруг \\n""},{""mc"":1,""mr"":1,""r"":61,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":2,""t"":""1722069,54\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":3,""t"":""Земельный участок под ИЖС (собственность)\\n\\nДом жилой (собственность)\\n\\nКвартира \\n(безвозмездное пользование)\\n\\nКомната (безвозмездное пользование)\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":4,""t"":""1000,0\\n\\n\\n\\n56,7\\n\\n\\n111,9\\n\\n\\n\\n18,0\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":5,""t"":""Россия\\n\\n\\n\\nРоссия\\n\\n\\nРоссия\\n\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":6,""t"":""а/м Ситроен С5\\n(собственность)\\n\\n""},{""mc"":1,""mr"":1,""r"":61,""c"":7,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":62,""c"":0,""t"":""Данжинов \\nБаатр \\nПурвеевич\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":1,""t"":""Руководитель - главный эксперт по медико-социальной экспертизе\\nФКУ \\""ГБ МСЭ по Республике Калмыкия\\"" Минтруда России \\n""},{""mc"":1,""mr"":1,""r"":62,""c"":2,""t"":""1 053 843,68\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":3,""t"":""Дом жилой (собственность)\\n\\nЗемельный участок (аренда)\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":4,""t"":""197,6\\n\\n\\n691,0\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":5,""t"":""Россия\\n\\n\\nРоссия\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":62,""c"":7,""t"":""-\\n""}]]}"\t"{""persons"":[{""incomes"":[{""relative"":null,""size_raw"":""3 260 700,05""}],""person"":{""name_raw"":""Гаркуша Людмила Генриховна"",""role"":""И.о. руководителя - главного эксперта по медико-социальной экспертизе ФКУ \\""ГБ МСЭ по Иркутской области\\"" Минтруда России""},""real_estates"":[{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""1204,0"",""text"":""Земельный участок под ИЖС (собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""1339,0"",""text"":""Земельный участок дачный(собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""143000,0"",""text"":""Земельный участок для ведения ЛПХ (собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""19,4"",""text"":""Гараж-бокс (собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""25,0"",""text"":""Дом дачный (собственность)""},{""country_raw"":""Россия"",""own_type_by_column"":null,""relative"":null,""square_raw"":""59,2"",""text"":""Квартира (собственность)""}],""real_estates_count"":6,""year"":""2012""}],""document"":{}}"\tЭто довольно редкий тип файла, но он есть. У Гаркуши - шесть отдельных квартир в смешанной колонке, приходится копировать части текста из ячеек, а не полностью всю ячейку. Каждому объекту надо сопоставить площадь.  Очень осторожно выделяйте, включая  подтип владения и нажимайте кнопку \'Недвижимость\'.   Год - 2012, а не 2013';
//let tsvLine = '6dc4867982c786a1210ee62c02a380f5__138_158\t"{""Title"":"" Сведения\\nо доходах, расходах, об имуществе и обязательствах имущественного характера\\nлиц, замещающих отдельные должности в организациях, созданных для выполнения задач, \\nпоставленных перед Минкультуры России, их супруг (супругов) и несовершеннолетних детей\\nза период с 1 января 2016 г. по 31 декабря 2016 г.\\n"",""InputFileName"":""documents/56884.docx"",""DataStart"":138,""DataEnd"":158,""Header"":[[{""mc"":1,""mr"":2,""r"":0,""c"":0,""t"":""№\\nп/п\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":1,""t"":""Фамилия и инициалы лица, чьи сведения размещаются\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":2,""t"":""Должность\\n""},{""mc"":4,""mr"":1,""r"":0,""c"":3,""t"":""Объекты недвижимости, находящиеся в собственности\\n""},{""mc"":3,""mr"":1,""r"":0,""c"":7,""t"":""Объекты недвижимости, находящиеся в пользовании\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":10,""t"":""Транспортные средства\\n(вид, марка)\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":11,""t"":""Декларированный годовой доход (руб.)\\n""},{""mc"":1,""mr"":2,""r"":0,""c"":12,""t"":""Сведения об источниках получения средств, за счет которых совершена сделка (вид приобретенного имущества, источники)\\n""}],[{""mc"":1,""mr"":1,""r"":1,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":3,""t"":""Вид объекта     \\n""},{""mc"":1,""mr"":1,""r"":1,""c"":4,""t"":""Вид собственности           \\n""},{""mc"":1,""mr"":1,""r"":1,""c"":5,""t"":""Площадь\\n(кв.м)\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":6,""t"":""Страна расположения\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":7,""t"":""Вид объекта\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":8,""t"":""Площадь\\n(кв.м)\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":9,""t"":""Страна расположения\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":10,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":1,""c"":12,""t"":""\\n""}]],""Section"":[],""Data"":[[{""mc"":1,""mr"":1,""r"":138,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":3,""t"":""Жилой дом\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":4,""t"":""Общая долевая, 1/2\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":5,""t"":""118,1\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":7,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":8,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":9,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":10,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":138,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":139,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":3,""t"":""квартира\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":4,""t"":""Общая долевая, 1/2\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":5,""t"":""60,1\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":7,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":8,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":9,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":10,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":139,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":140,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":1,""t"":""супруг\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":3,""t"":""Дачный земельный участок\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":4,""t"":""Общая долевая, 1/2\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":5,""t"":""616,0\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":7,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":8,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":9,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":10,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":11,""t"":""383940,00\\n""},{""mc"":1,""mr"":1,""r"":140,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":141,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":3,""t"":""Жилой дом\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":4,""t"":""Общая долевая, 1/2\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":5,""t"":""118,1\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":7,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":8,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":9,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":10,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":141,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":142,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":3,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":4,""t"":""Общая долевая, 1/2\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":5,""t"":""60,1\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":7,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":8,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":9,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":10,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":142,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":143,""c"":0,""t"":""5\\n""},{""mc"":12,""mr"":1,""r"":143,""c"":1,""t"":""Федеральное государственное бюджетное учреждение культуры «Екатеринбургский государственный академический театр оперы и балета»\\n""}],[{""mc"":1,""mr"":1,""r"":144,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":1,""t"":""Шишкин А.Г.\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":2,""t"":""Директор\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":3,""t"":""Квартира\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":5,""t"":""83,1\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":6,""t"":""Россия\\n\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":7,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":8,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":9,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":10,""t"":""а/м легковой Мерседес Бенц GL 350 Bluetec 4matic\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":11,""t"":""13 597 263,73\\n""},{""mc"":1,""mr"":1,""r"":144,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":145,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":3,""t"":""Квартира\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":5,""t"":""73,0\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":7,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":8,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":9,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":10,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":145,""c"":12,""t"":""\\n""}],[{""mc"":1,""mr"":1,""r"":146,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":3,""t"":""Квартира\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":5,""t"":""48,9\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":7,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":8,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":9,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":10,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":146,""c"":12,""t"":""\\n""}],[{""mc"":1,""mr"":1,""r"":147,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":3,""t"":""Квартира\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":5,""t"":""42,9\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":7,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":8,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":9,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":10,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":147,""c"":12,""t"":""\\n""}],[{""mc"":1,""mr"":1,""r"":148,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":3,""t"":""Квартира\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":5,""t"":""35,7\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":7,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":8,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":9,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":10,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":148,""c"":12,""t"":""\\n""}],[{""mc"":1,""mr"":1,""r"":149,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":3,""t"":""Квартира\\n\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":5,""t"":""35,6\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":7,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":8,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":9,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":10,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":149,""c"":12,""t"":""\\n""}],[{""mc"":1,""mr"":1,""r"":150,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":3,""t"":""Квартира\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":5,""t"":""41,6\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":7,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":8,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":9,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":10,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":150,""c"":12,""t"":""\\n""}],[{""mc"":1,""mr"":1,""r"":151,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":1,""t"":""Супруга\\n\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":3,""t"":""Квартира\\n\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":5,""t"":""43,1\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":7,""t"":""Квартира\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":8,""t"":""83,1\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":9,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":10,""t"":""а/м легковой Киа Рио\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":11,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":151,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":152,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":1,""t"":""Несовершеннолетний ребенок\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":3,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":4,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":5,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":7,""t"":""Квартира\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":8,""t"":""32,0\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":9,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":10,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":11,""t"":""711 263,56\\n""},{""mc"":1,""mr"":1,""r"":152,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":153,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":153,""c"":1,""t"":""Лобанова Л.Г.\\n""},{""mc"":1,""mr"":1,""r"":153,""c"":2,""t"":""Главный бухгалтер финансово-экономической службы \\n""},{""mc"":1,""mr"":1,""r"":153,""c"":3,""t"":""Земельный участок \\n""},{""mc"":1,""mr"":1,""r"":153,""c"":4,""t"":""Индивидуальная \\n""},{""mc"":1,""mr"":1,""r"":153,""c"":5,""t"":""1024\\n\\n\\n\\n\\n\\n\\n\\n""},{""mc"":1,""mr"":1,""r"":153,""c"":6,""t"":""\\nРоссия\\n\\n\\n\\n\\n\\n\\n\\n""},{""mc"":1,""mr"":1,""r"":153,""c"":7,""t"":""\\n-\\n""},{""mc"":1,""mr"":1,""r"":153,""c"":8,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":153,""c"":9,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":153,""c"":10,""t"":""-\\n\\n""},{""mc"":1,""mr"":1,""r"":153,""c"":11,""t"":""7 916 992\\n""},{""mc"":1,""mr"":1,""r"":153,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":154,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":3,""t"":""жилой дом \\n\\n\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":5,""t"":""147,8\\n\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":7,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":8,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":9,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":10,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":154,""c"":12,""t"":""\\n""}],[{""mc"":1,""mr"":1,""r"":155,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":1,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":3,""t"":""баня\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":4,""t"":""Индивидуальная\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":5,""t"":""60\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":7,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":8,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":9,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":10,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":11,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":155,""c"":12,""t"":""\\n""}],[{""mc"":1,""mr"":1,""r"":156,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":1,""t"":""Супруг \\n""},{""mc"":1,""mr"":1,""r"":156,""c"":2,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":3,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":4,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":5,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":6,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":7,""t"":""жилой дом\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":8,""t"":""147,8\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":9,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":10,""t"":""Легковой автомобиль INFINITI QX 80 \\n""},{""mc"":1,""mr"":1,""r"":156,""c"":11,""t"":""765 516\\n""},{""mc"":1,""mr"":1,""r"":156,""c"":12,""t"":""-\\n""}],[{""mc"":1,""mr"":1,""r"":157,""c"":0,""t"":""\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":1,""t"":""Романова И.В.\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":2,""t"":""Заместитель директора по маркетингу \\n""},{""mc"":1,""mr"":1,""r"":157,""c"":3,""t"":""Квартиры\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":4,""t"":""Общая\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":5,""t"":""33,8\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":6,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":7,""t"":""квартира\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":8,""t"":""53,4\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":9,""t"":""Россия\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":10,""t"":""-\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":11,""t"":""2397316,62\\n""},{""mc"":1,""mr"":1,""r"":157,""c"":12,""t"":""-\\n""}]]}"\t"{""persons"":[{""incomes"":[{""relative"":null,""size_raw"":""13 597 263,73""},{""relative"":""Ребенок"",""size_raw"":""711 263,56""}],""person"":{""department"":""Федеральное государственное бюджетное учреждение культуры «Екатеринбургский государственный академический театр оперы и балета»"",""name_raw"":""Шишкин А.Г."",""role"":""Директор""},""real_estates"":[{""country_raw"":""Россия"",""own_type_by_column"":""В собственности"",""own_type_raw"":""Индивидуальная"",""relative"":null,""square_raw"":""35,6"",""text"":""Квартира"",""type_raw"":""Квартира""},{""country_raw"":""Россия"",""own_type_by_column"":""В собственности"",""own_type_raw"":""Индивидуальная"",""relative"":null,""square_raw"":""35,7"",""text"":""Квартира"",""type_raw"":""Квартира""},{""country_raw"":""Россия"",""own_type_by_column"":""В собственности"",""own_type_raw"":""Индивидуальная"",""relative"":null,""square_raw"":""41,6"",""text"":""Квартира"",""type_raw"":""Квартира""},{""country_raw"":""Россия"",""own_type_by_column"":""В собственности"",""own_type_raw"":""Индивидуальная"",""relative"":null,""square_raw"":""42,9"",""text"":""Квартира"",""type_raw"":""Квартира""},{""country_raw"":""Россия"",""own_type_by_column"":""В собственности"",""own_type_raw"":""Индивидуальная"",""relative"":null,""square_raw"":""48,9"",""text"":""Квартира"",""type_raw"":""Квартира""},{""country_raw"":""Россия"",""own_type_by_column"":""В собственности"",""own_type_raw"":""Индивидуальная"",""relative"":null,""square_raw"":""73,0"",""text"":""Квартира"",""type_raw"":""Квартира""},{""country_raw"":""Россия"",""own_type_by_column"":""В собственности"",""own_type_raw"":""Индивидуальная"",""relative"":null,""square_raw"":""83,1"",""text"":""Квартира"",""type_raw"":""Квартира""},{""country_raw"":""Россия"",""own_type_by_column"":""В пользовании"",""relative"":""Ребенок"",""square_raw"":""32,0"",""text"":""Квартира""},{""country_raw"":""Россия"",""own_type_by_column"":""В пользовании"",""relative"":""Супруг(а)"",""square_raw"":""83,1"",""text"":""Квартира""},{""country_raw"":""Россия"",""own_type_by_column"":""В собственности"",""own_type_raw"":""Индивидуальная"",""relative"":""Супруг(а)"",""square_raw"":""43,1"",""text"":""Квартира"",""type_raw"":""Квартира""}],""real_estates_count"":10,""vehicles"":[{""relative"":null,""text"":""а/м легковой Мерседес Бенц GL 350 Bluetec 4matic""},{""relative"":""Супруг(а)"",""text"":""а/м легковой Киа Рио""}],""year"":""2016""}],""document"":{}}"\tУ него 10 квартир, есть поле департамента (кнопка \'Отдел\'), осторожно! второй доход приписан ребенку (так и надо перенести, хотя, скорее всего, это доход супруги, мы не имеем право это менять).';
let tsvLine = '27738e9c4a686e76f468ea507857784f__17_37\t"{""Title"":""Сведения о доходах, расходах, об имуществе и обязательствах имущественного характера федеральных государственных гражданских служащих \\nМинистерства сельского хозяйства Российской Федерации и членов их семей \\nза период с 1 января 2017 г. по 31 декабря 2017 г."",""InputFileName"":""documents/59562.xls"",""DataStart"":17,""DataEnd"":37,""Header"":[[{""mc"":1,""mr"":2,""r"":3,""c"":0,""t"":""№\\nп/п""},{""mc"":1,""mr"":2,""r"":3,""c"":1,""t"":""Фамилия и инициалы лица, чьи сведения размещаются""},{""mc"":1,""mr"":2,""r"":3,""c"":2,""t"":""Должность""},{""mc"":4,""mr"":1,""r"":3,""c"":3,""t"":""Объекты недвижимости, находящиеся в собственности""},{""mc"":3,""mr"":1,""r"":3,""c"":7,""t"":""Объекты недвижимости находящиеся в пользовании""},{""mc"":1,""mr"":2,""r"":3,""c"":10,""t"":""Транспортные средства \\n(вид, марка)""},{""mc"":1,""mr"":2,""r"":3,""c"":11,""t"":""Декларированный годовой доход (руб.)""}],[{""mc"":1,""mr"":2,""r"":4,""c"":0,""t"":""""},{""mc"":1,""mr"":2,""r"":4,""c"":1,""t"":""""},{""mc"":1,""mr"":2,""r"":4,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":4,""c"":3,""t"":""вид объекта""},{""mc"":1,""mr"":1,""r"":4,""c"":4,""t"":""вид собственности""},{""mc"":1,""mr"":1,""r"":4,""c"":5,""t"":""площадь (кв. м)""},{""mc"":1,""mr"":1,""r"":4,""c"":6,""t"":""страна расположения""},{""mc"":1,""mr"":1,""r"":4,""c"":7,""t"":""вид объекта""},{""mc"":1,""mr"":1,""r"":4,""c"":8,""t"":""площадь (кв.м)""},{""mc"":1,""mr"":1,""r"":4,""c"":9,""t"":""страна расположения""},{""mc"":1,""mr"":2,""r"":4,""c"":10,""t"":""""},{""mc"":1,""mr"":2,""r"":4,""c"":11,""t"":""""}]],""Section"":[],""Data"":[[{""mc"":1,""mr"":38,""r"":17,""c"":0,""t"":""""},{""mc"":1,""mr"":2,""r"":17,""c"":1,""t"":""""},{""mc"":1,""mr"":2,""r"":17,""c"":2,""t"":""""},{""mc"":1,""mr"":2,""r"":17,""c"":3,""t"":""Квартира""},{""mc"":1,""mr"":2,""r"":17,""c"":4,""t"":""Долевая, 1/8 доля""},{""mc"":1,""mr"":2,""r"":17,""c"":5,""t"":""196,4""},{""mc"":1,""mr"":2,""r"":17,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":1,""r"":17,""c"":7,""t"":""Жилой дом""},{""mc"":1,""mr"":1,""r"":17,""c"":8,""t"":""555,6""},{""mc"":1,""mr"":1,""r"":17,""c"":9,""t"":""Россия""},{""mc"":1,""mr"":3,""r"":17,""c"":10,""t"":""""},{""mc"":1,""mr"":3,""r"":17,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":18,""c"":0,""t"":""""},{""mc"":1,""mr"":1,""r"":18,""c"":1,""t"":""""},{""mc"":1,""mr"":1,""r"":18,""c"":2,""t"":""""},{""mc"":1,""mr"":2,""r"":18,""c"":3,""t"":""""},{""mc"":1,""mr"":2,""r"":18,""c"":4,""t"":""""},{""mc"":1,""mr"":2,""r"":18,""c"":5,""t"":""""},{""mc"":1,""mr"":2,""r"":18,""c"":6,""t"":""""},{""mc"":1,""mr"":1,""r"":18,""c"":7,""t"":""Земельный участок""},{""mc"":1,""mr"":1,""r"":18,""c"":8,""t"":""1667""},{""mc"":1,""mr"":1,""r"":18,""c"":9,""t"":""Россия""},{""mc"":1,""mr"":3,""r"":18,""c"":10,""t"":""""},{""mc"":1,""mr"":3,""r"":18,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":19,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":19,""c"":1,""t"":""Супруга""},{""mc"":1,""mr"":27,""r"":19,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":19,""c"":3,""t"":""Земельный участок""},{""mc"":1,""mr"":1,""r"":19,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":19,""c"":5,""t"":""145""},{""mc"":1,""mr"":1,""r"":19,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":1,""r"":19,""c"":7,""t"":""Жилой дом""},{""mc"":1,""mr"":1,""r"":19,""c"":8,""t"":""555,6""},{""mc"":1,""mr"":1,""r"":19,""c"":9,""t"":""Россия""},{""mc"":1,""mr"":27,""r"":19,""c"":10,""t"":""Автомобиль легковой \\nВАЗ 2121""},{""mc"":1,""mr"":27,""r"":19,""c"":11,""t"":""10 507 754, 79""}],[{""mc"":1,""mr"":38,""r"":20,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":20,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":20,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":20,""c"":3,""t"":""Земельный участок""},{""mc"":1,""mr"":1,""r"":20,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":20,""c"":5,""t"":""98""},{""mc"":1,""mr"":1,""r"":20,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":1,""r"":20,""c"":7,""t"":""Квартира""},{""mc"":1,""mr"":1,""r"":20,""c"":8,""t"":""138,5""},{""mc"":1,""mr"":1,""r"":20,""c"":9,""t"":""Россия""},{""mc"":1,""mr"":27,""r"":20,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":20,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":21,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":21,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":21,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":21,""c"":3,""t"":""Земельный участок""},{""mc"":1,""mr"":1,""r"":21,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":21,""c"":5,""t"":""340""},{""mc"":1,""mr"":1,""r"":21,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":1,""r"":21,""c"":7,""t"":""Земельный участок""},{""mc"":1,""mr"":1,""r"":21,""c"":8,""t"":""1667""},{""mc"":1,""mr"":1,""r"":21,""c"":9,""t"":""Россия""},{""mc"":1,""mr"":27,""r"":21,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":21,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":22,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":22,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":22,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":22,""c"":3,""t"":""Земельный участок""},{""mc"":1,""mr"":1,""r"":22,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":22,""c"":5,""t"":""260""},{""mc"":1,""mr"":1,""r"":22,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":22,""c"":7,""t"":""Квартира""},{""mc"":1,""mr"":24,""r"":22,""c"":8,""t"":""196,4""},{""mc"":1,""mr"":24,""r"":22,""c"":9,""t"":""Россия""},{""mc"":1,""mr"":27,""r"":22,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":22,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":23,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":23,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":23,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":23,""c"":3,""t"":""Земельный участок""},{""mc"":1,""mr"":1,""r"":23,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":23,""c"":5,""t"":""9529""},{""mc"":1,""mr"":1,""r"":23,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":23,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":23,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":23,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":23,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":23,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":24,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":24,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":24,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":24,""c"":3,""t"":""Земельный участок""},{""mc"":1,""mr"":1,""r"":24,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":24,""c"":5,""t"":""1000""},{""mc"":1,""mr"":1,""r"":24,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":24,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":24,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":24,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":24,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":24,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":25,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":25,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":25,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":25,""c"":3,""t"":""Садовый дом""},{""mc"":1,""mr"":1,""r"":25,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":25,""c"":5,""t"":""115,3""},{""mc"":1,""mr"":1,""r"":25,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":25,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":25,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":25,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":25,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":25,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":26,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":26,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":26,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":26,""c"":3,""t"":""Гараж""},{""mc"":1,""mr"":1,""r"":26,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":26,""c"":5,""t"":""49""},{""mc"":1,""mr"":1,""r"":26,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":26,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":26,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":26,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":26,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":26,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":27,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":27,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":27,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":27,""c"":3,""t"":""Дом бригадный""},{""mc"":1,""mr"":1,""r"":27,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":27,""c"":5,""t"":""76,7""},{""mc"":1,""mr"":1,""r"":27,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":27,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":27,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":27,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":27,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":27,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":28,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":28,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":28,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":28,""c"":3,""t"":""Склад химикатов""},{""mc"":1,""mr"":1,""r"":28,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":28,""c"":5,""t"":""32,6""},{""mc"":1,""mr"":1,""r"":28,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":28,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":28,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":28,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":28,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":28,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":29,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":29,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":29,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":29,""c"":3,""t"":""Склад""},{""mc"":1,""mr"":1,""r"":29,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":29,""c"":5,""t"":""55,5""},{""mc"":1,""mr"":1,""r"":29,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":29,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":29,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":29,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":29,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":29,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":30,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":30,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":30,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":30,""c"":3,""t"":""Склад материалов""},{""mc"":1,""mr"":1,""r"":30,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":30,""c"":5,""t"":""56,1""},{""mc"":1,""mr"":1,""r"":30,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":30,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":30,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":30,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":30,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":30,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":31,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":31,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":31,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":31,""c"":3,""t"":""Пруд зимовальный""},{""mc"":1,""mr"":1,""r"":31,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":31,""c"":5,""t"":""2 596,5""},{""mc"":1,""mr"":1,""r"":31,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":31,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":31,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":31,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":31,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":31,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":32,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":32,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":32,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":32,""c"":3,""t"":""Пруд выростной""},{""mc"":1,""mr"":1,""r"":32,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":32,""c"":5,""t"":""7 446,7""},{""mc"":1,""mr"":1,""r"":32,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":32,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":32,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":32,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":32,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":32,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":33,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":33,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":33,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":33,""c"":3,""t"":""Пруд зимовальный""},{""mc"":1,""mr"":1,""r"":33,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":33,""c"":5,""t"":""4 050,8""},{""mc"":1,""mr"":1,""r"":33,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":33,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":33,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":33,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":33,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":33,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":34,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":34,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":34,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":34,""c"":3,""t"":""Пруд зимовальный""},{""mc"":1,""mr"":1,""r"":34,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":34,""c"":5,""t"":""3 694,2""},{""mc"":1,""mr"":1,""r"":34,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":34,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":34,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":34,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":34,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":34,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":35,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":35,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":35,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":35,""c"":3,""t"":""Пруд зимовальный""},{""mc"":1,""mr"":1,""r"":35,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":35,""c"":5,""t"":""5 770,2""},{""mc"":1,""mr"":1,""r"":35,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":35,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":35,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":35,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":35,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":35,""c"":11,""t"":""""}],[{""mc"":1,""mr"":38,""r"":36,""c"":0,""t"":""""},{""mc"":1,""mr"":27,""r"":36,""c"":1,""t"":""""},{""mc"":1,""mr"":27,""r"":36,""c"":2,""t"":""""},{""mc"":1,""mr"":1,""r"":36,""c"":3,""t"":""Пруд выростной""},{""mc"":1,""mr"":1,""r"":36,""c"":4,""t"":""Индивидуальная""},{""mc"":1,""mr"":1,""r"":36,""c"":5,""t"":""9 587,3""},{""mc"":1,""mr"":1,""r"":36,""c"":6,""t"":""Россия""},{""mc"":1,""mr"":24,""r"":36,""c"":7,""t"":""""},{""mc"":1,""mr"":24,""r"":36,""c"":8,""t"":""""},{""mc"":1,""mr"":24,""r"":36,""c"":9,""t"":""""},{""mc"":1,""mr"":27,""r"":36,""c"":10,""t"":""""},{""mc"":1,""mr"":27,""r"":36,""c"":11,""t"":""""}]]}"\t"{""persons_empty"":1,""persons"":[],""document"":{}}"\t';
let jsonStr = tsvLine.split("\t")[1];
jsonStr = jsonStr.replace(/""/g, '"');
jsonStr = jsonStr.replace(/^"/, '');
jsonStr = jsonStr.replace(/"$/, '');
let context = {input_id: "1", input_json: jsonStr, declaration_json:"hkfhggkfjhgfk"};
let html  = handleBarsTemplate(context);
taskSource.innerHTML = html;

let button = document.createElement("button");
button.onclick = on_toloka_validate;
button.innerHTML = "<h1>Next Task</h1>";
let body = document. getElementsByTagName("body")[0];
body.appendChild(button);
