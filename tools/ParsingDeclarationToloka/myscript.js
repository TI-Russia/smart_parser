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
        cell.innerHTML = inputList[k].t.replace("\n", "<br/>");
        cell.colSpan = inputList[k].mc;
    }
}

function input_json_to_html_table(jsonStr){
    jsonStr = jsonStr.replace(/\n/g, '<br/>')
    let data = JSON.parse(jsonStr);
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
    for (let i = 0; i < data.Data.length; ++i) {
        add_html_table_row(data.Data[i], tbody);
    }
    tbl.appendChild(tbody);
    res += tbl.outerHTML;
    return res;
}

Handlebars.registerHelper('convert_json_to_html_helper', function(jsonStr) {
    return input_json_to_html_table(jsonStr);
});


Handlebars.registerHelper('owner_types', function(radio_button_name, image_div_name ) {
    let ownerTypeTemplate =  "<label> <input type=\"radio\" name={{name}}  value=\"{{value}}\" " +
        "                           onclick=\"window.show_icon('{{image}}', '{{image_div_name}}')\"\n" +
        "                           {{#if checked}} checked {{/if}}\" /> {{title}}</label> <br/><br/>";
    let ownerTypes = [
        {'value': "", title:"Декларант", image:"http://aot.ru/images/declarant.png", "checked":"checked"},
        {'value': "Супруг(а)", title:"Супруг(а)", image:"http://aot.ru/images/spouse.png"},
        {'value': "Ребенок", title:"Ребенок", image:"http://aot.ru/images/child.png"}
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
    if ( !('person' in person) ) {
        throw_and_log ( new Error("У декларанта нет ФИО (нет зоны person c полем 'name_raw')"));
    };
    if ( !('name_raw' in person.person) ) {
        throw_and_log ( new Error("У декларанта нет ФИО (поле 'name_raw')"));
    };
    return person;
}

function is_empty_or_number(s){
    return ((s.length == 0) || ('0123456789'.indexOf(s[0]) !== -1 ));
}

function add_declarant() {
    let djson = read_main_json();
    if (!('persons' in djson) || (djson.persons.length == 0)) {
        throw_and_log("Сначала надо обрезать таблицу (кнопка 'Обрезать')");
    }
    let text = get_new_value("Введите ФИО");
    if (text.length > 50) {
        throw_and_log("ФИО слишком длинное (>50 символов)");
    }
    if (text.indexOf(" ") == -1 && text.indexOf(".") == -1) {
        throw_and_log("Однословных ФИО не бывает");
    }
    if (is_empty_or_number(text)) {
        throw_and_log("Недопустимый или пустой ФИО");
    }

    if (text != "") {
        if (djson.persons.length > 0) {
            if (!('person'  in djson.persons[0])) {
                djson.persons[0].person = {};
            }
            djson.persons[0].person.name_raw = text;
        }
        else {
            djson.persons.push({'person': {'name_raw': text}});
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
        if (is_empty_or_number(text)) {
            throw_and_log("плохой или пустой тип недвижимости: " + text);
        }
        person.person.role = text;
        write_main_json(djson);
    }
}
window.add_declarant_role = add_declarant_role;

function add_realties_number() {
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
        let type_raw = document.getElementById('realty_type').value;
        if (is_empty_or_number(type_raw)) {
            throw_and_log("плохой или пустой тип недвижимости: " + type_raw);
        }
        let real_estate = {
            'type_raw': type_raw,
            "own_type_by_column":   get_radio_button_value ('realty_own_type_by_column'),
            "relative":   get_radio_button_value ( 'realty_owner_type'),
            "country_raw": 'Россия'
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
    add_realty_property ('square_raw', "Введите площадь:");
}
window.add_square = add_square;

function add_own_type() {
    add_realty_property ('own_type_raw', "Введите вид владения:");
}
window.add_own_type = add_own_type;


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
            'size_raw': document.getElementById('income_value').value,
            "relative":   get_radio_button_value ('income_owner_type')
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

function save_person_offsets(start, last) {
    let djson = read_main_json();
    let table_row_range = {'begin_row': start, 'last_row': last };
    if (!djson.persons.length) {
        let person = {'table_row_range': table_row_range}
        djson.persons.push(person);
    } else {
        let person = get_last_person(djson)
        person['table_row_range'] = table_row_range;
    }
    write_main_json(djson, false);
}

function cut_by_selection() {
    if (typeof window.getSelection == "undefined") {
        return;
    }
    let obj = window.getSelection();
    let start_row = get_selected_row (obj.anchorNode, "Не выделена ячейка таблицы");
    let last_row = get_selected_row (obj.focusNode, "Выделение выхоодит за пределы таблицы");
    let tbody = start_row.parentNode;
    let table = tbody.parentNode;
    let headerSize = table.tHead.rows.length;
    save_person_offsets( start_row.rowIndex, last_row.rowIndex);
    // modify table after save_undo_version
    delete_table_rows_after(tbody, last_row.rowIndex + 1 - headerSize);
    delete_table_rows_before(tbody, start_row.rowIndex - headerSize);

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
            "relative":   get_radio_button_value ('vehicle_owner_type')
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
    let values = get_radio_button_values('vehicle_owner_type')
    for (let i = 0; i < field.length; i++) {
        if  ( (field[i].relative != null)  && (values.indexOf(field[i].relative) == -1)){
            throw_and_log("bad relative in " + JSON.stringify(field[i], ""));
        };
    }
}

function check_real_estate_records(person) {
    check_real_estates_count(person);

    if (typeof person.real_estates == "undefined") return;

    let values = get_radio_button_values('realty_own_type_by_column')
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

        if (r.own_type_raw != null && is_empty_or_number(r.own_type_raw)) {
            throw_and_log("плохой или пустой тип недвижимости: " + r.own_type_raw);
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
    return sort_json_by_keys(person);
}

function check_mandatory_fields(successMessage=true)
{
    let djson = read_main_json();
    if ('persons_empty' in djson) {
        djson.persons = [];
        djson.document = {};
        write_main_json(djson, false);
        return;
    }

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
    djson.persons[0] = sort_declaration_json(person);
    write_main_json(djson, false);
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
    if ((e.key == "П") || (e.key == "п") || (e.key == "G") || (e.key == "g")) {
        window.add_square();
    }
    if ((e.key == "О") || (e.key == "о") || (e.key == "J") || (e.key == "j")) {
        window.cut_by_selection();
    }
    if ((e.key == "Е") || (e.key == "е") || (e.key == "T") || (e.key == "t")) {
        window.add_department();
    }
    if ((e.key == "В") || (e.key == "в") || (e.key == "D") || (e.key == "d")) {
        window.add_own_type();
    }
    if ((e.key == "К") || (e.key == "к") || (e.key == "R") || (e.key == "r")) {
        window.add_realties_number();
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
    let djson = read_main_json();
    let person = get_last_person(djson);
    let text = get_new_value("Введите отдел (организацию)");
    if (text != "") {
        person.person.department = text;
        write_main_json(djson);
    }
}
window.add_department = add_department;

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
let inputJson ='{"Title":"СВЕДЕНИЯ о доходах, расходах, об имуществе и обязательствах имущественного характера  лиц, замещающих отдельные должности на основании \nтрудового договора в организациях, находящихся в ведении Министерства финансов Российской Федерации, а также сведения о доходах, \nрасходах, об имуществе и обязательствах имущественного характера  их  супруг (супругов) и несовершеннолетних детей   за период с 1 января 2017 г. по 31 декабря 2017 г. \n \n \n","InputFileName":"documents/59397.pdf","DataStart":103,"DataEnd":123,"Header":[[{"mc":1,"t":"№ \nп/п \n"},{"mc":1,"t":"Фамилия и инициалы лица, чьи сведения размещаются \n"},{"mc":1,"t":"Должность \n"},{"mc":4,"t":"Объекты недвижимости, находящиеся в собственности \n"},{"mc":3,"t":"Объекты недвижимости, находящиеся в пользовании \n"},{"mc":1,"t":"Транспортные средства (вид, марка) \n"},{"mc":1,"t":"Декларированный годовой доход \n(руб.) \n"},{"mc":1,"t":"Сведения об источниках \nполучения средств, за счет которых \nсовершена сделка \n(вид приобретенного имущества, источники) \n"}],[{"mc":1,"t":"\n"},{"mc":1,"t":"\n"},{"mc":1,"t":"\n"},{"mc":1,"t":"вид объекта\n"},{"mc":1,"t":"  вид   собственности\n"},{"mc":1,"t":"площадь \n(кв. м) \n"},{"mc":1,"t":"страна \nрасположения \n"},{"mc":1,"t":"вид объекта \n"},{"mc":1,"t":"площадь \n(кв. м) \n"},{"mc":1,"t":"страна \nрасположен ия \n"},{"mc":1,"t":"\n"},{"mc":1,"t":"\n"},{"mc":1,"t":"\n"}]],"Section":[[{"mc":14,"t":"Федеральное государственное бюджетное учреждение «Научно-исследовательский финансовый институт» \n"}]],"Data":[[{"mc":1,"t":" \n"},{"mc":1,"t":"Супруг (супруга)          \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Земельный участок \n"},{"mc":1,"t":"Общая долевая \n(1/2) \n"},{"mc":1,"t":"901,00 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"Земельный участок \n"},{"mc":2,"t":"600,00 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"365301,13 \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Жилой дом \n"},{"mc":1,"t":"Общая долевая \n(1/2) \n"},{"mc":1,"t":"47,2 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":"    \n"},{"mc":1,"t":"                                    \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Квартира \n"},{"mc":1,"t":"общая \nсовместная  \n"},{"mc":1,"t":"110,20 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":"    \n"},{"mc":1,"t":"                                    \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Квартира \n"},{"mc":1,"t":"Общая долевая \n(2/3) \n"},{"mc":1,"t":"69,80 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":14,"t":"Федеральное казенное учреждение «Государственное учреждение по эксплуатации административных зданий и дачного хозяйства Министерства финансов Российской Федерации» \n"}],[{"mc":1,"t":"1    \n"},{"mc":1,"t":"                                    \nЛесовой Н.А.              \n"},{"mc":1,"t":"Заместитель директора \n"},{"mc":1,"t":"Земельный участок \n"},{"mc":1,"t":"индивидуальная \n"},{"mc":1,"t":"802,00 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"Гараж  \n"},{"mc":2,"t":"18,5 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"Автомобиль легковой:  \nТойота лексус RX \n"},{"mc":1,"t":"2485332,80 \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":"    \n"},{"mc":1,"t":"                                   \n"},{"mc":1,"t":"    \n"},{"mc":1,"t":"Земельный участок \n"},{"mc":1,"t":"индивидуальная \n"},{"mc":1,"t":"1200,00 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":"    \n"},{"mc":1,"t":"                                   \n"},{"mc":1,"t":"    \n"},{"mc":1,"t":"Жилой дом \n"},{"mc":1,"t":"индивидуальная \n"},{"mc":1,"t":"135,80 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Квартира \n"},{"mc":1,"t":"общая долевая, \n1/4 \n"},{"mc":1,"t":"87,80 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Хозяйственное строение \n"},{"mc":1,"t":"индивидуальная \n"},{"mc":1,"t":"24,00 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Нежилое помещение \n"},{"mc":1,"t":"индивидуальная \n"},{"mc":1,"t":"285,20 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":"    \n"},{"mc":1,"t":"                                  \n \nСупруг (супруга)          \n"},{"mc":1,"t":"  \n \n"},{"mc":1,"t":"Квартира \n"},{"mc":1,"t":"общая долевая, \n1/4 \n"},{"mc":1,"t":"43,30 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"Квартира \n"},{"mc":2,"t":"87,80 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"2299534,62 \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":"2 \n"},{"mc":1,"t":"Листиков М.В. \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Квартира \n"},{"mc":1,"t":"индивидуальная \n"},{"mc":1,"t":"63,60 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"Автомобиль легковой:  \nФиат Добло \n"},{"mc":1,"t":"1037015,65 \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Гараж  \n"},{"mc":1,"t":"индивидуальная \n"},{"mc":1,"t":"18,00 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"Автомобиль легковой:  \nДэу Матиз \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"Автомобиль грузовой:  \nБАУ 1044 \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":"Супруг (супруга)          \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Земельный участок \n"},{"mc":1,"t":"индивидуальная \n"},{"mc":1,"t":"600,00 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":" \n"},{"mc":2,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Автомобиль легковой:  \nДэу Матиз \n"},{"mc":1,"t":"238687,09 \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":" \n"},{"mc":1,"t":"Садовый дом \n"},{"mc":1,"t":"индивидуальная \n"},{"mc":1,"t":"105,30 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":2,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":"3 \n"},{"mc":1,"t":"                                    \nОвсюк Л.А.                 \n"},{"mc":1,"t":"Главный   бухгалтер \n"},{"mc":1,"t":"Квартира \n"},{"mc":1,"t":"общая долевая, \n1/4 \n"},{"mc":1,"t":"59,00 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"Квартира \n"},{"mc":2,"t":"56,60 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"1798404,52 \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":"                                  \nНесовершеннолетний \nребенок                  \n"},{"mc":1,"t":"  \n \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"Квартира \n"},{"mc":2,"t":"56,60 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"0,00 \n"},{"mc":1,"t":"- \n"}],[{"mc":1,"t":" \n"},{"mc":1,"t":"                                  \nНесовершеннолетний \nребенок                  \n"},{"mc":1,"t":"  \n \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"Квартира \n"},{"mc":2,"t":"56,60 \n"},{"mc":1,"t":"Россия \n"},{"mc":1,"t":"- \n"},{"mc":1,"t":"0,00 \n"},{"mc":1,"t":"- \n"}]]}';
let context = {input_id: "1", input_json: inputJson, declaration_json:"hkfhggkfjhgfk"};
let html  = handleBarsTemplate(context);
taskSource.innerHTML = html;

