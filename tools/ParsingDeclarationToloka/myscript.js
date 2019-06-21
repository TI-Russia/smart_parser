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
        cell.innerHTML = inputList[k].Text.replace("\n", "<br/>");
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
        {'value': "", title:"Собственная", image:"http://aot.ru/images/declarant.png", "checked":"checked"},
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

function set_radio_button(name, value) {
    let rad = document.getElementsByName(name);
    let values = []
    for (let i=0; i < rad.length; i++) {
        if (rad[i].value == value) {
            rad[i].focus();
            rad[i].checked = true;
            rad[i].onclick(null);
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

function add_declarant() {
    let djson = read_main_json();
    let text = get_new_value("Введите ФИО");
    if (text.length > 50) {
        throw_and_log("ФИО слишком длинное (>50 символов)");
    }
    if (text.indexOf(" ") == -1 && text.indexOf(".") == -1) {
        throw_and_log("Однословных ФИО не бывает");
    }
    if (text != "") {
        if (djson.persons.length > 0) {
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
        person.person.role = text;
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
            "own_type":   get_radio_button_value ('realty_own_type'),
            "relative":   get_radio_button_value ( 'realty_owner_type'),
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

function check_real_estate_own_type(person) {
    if (typeof person.real_estates == "undefined") return;
    let values = get_radio_button_values('realty_own_type')
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
    if ((e.key == "П") || (e.key == "п") || (e.key == "G") || (e.key == "g")) {
        window.add_square();
    }
    if ((e.key == "О") || (e.key == "о") || (e.key == "J") || (e.key == "j")) {
        window.cut_by_selection();
    }
    if ((e.key == "Е") || (e.key == "е") || (e.key == "T") || (e.key == "t")) {
        window.add_department();
    }
    if ((e.key == "Я") || (e.key == "я") || (e.key == "Z") || (e.key == "z")) {
        window.add_share();
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
let inputJson ='{"Title":"СВЕДЕНИЯ о доходах, расходах, об имуществе и обязательствах имущественного характера  лиц, замещающих отдельные должности на основании \nтрудового договора в организациях, находящихся в ведении Министерства финансов Российской Федерации, а также сведения о доходах, \nрасходах, об имуществе и обязательствах имущественного характера  их  супруг (супругов) и несовершеннолетних детей   за период с 1 января 2017 г. по 31 декабря 2017 г. \n \n \n","InputFileName":"documents/59397.pdf","DataStart":103,"DataEnd":123,"Header":[[{"MergedColsCount":1,"Text":"№ \nп/п \n"},{"MergedColsCount":1,"Text":"Фамилия и инициалы лица, чьи сведения размещаются \n"},{"MergedColsCount":1,"Text":"Должность \n"},{"MergedColsCount":4,"Text":"Объекты недвижимости, находящиеся в собственности \n"},{"MergedColsCount":3,"Text":"Объекты недвижимости, находящиеся в пользовании \n"},{"MergedColsCount":1,"Text":"Транспортные средства (вид, марка) \n"},{"MergedColsCount":1,"Text":"Декларированный годовой доход \n(руб.) \n"},{"MergedColsCount":1,"Text":"Сведения об источниках \nполучения средств, за счет которых \nсовершена сделка \n(вид приобретенного имущества, источники) \n"}],[{"MergedColsCount":1,"Text":"\n"},{"MergedColsCount":1,"Text":"\n"},{"MergedColsCount":1,"Text":"\n"},{"MergedColsCount":1,"Text":"вид объекта\n"},{"MergedColsCount":1,"Text":"  вид   собственности\n"},{"MergedColsCount":1,"Text":"площадь \n(кв. м) \n"},{"MergedColsCount":1,"Text":"страна \nрасположения \n"},{"MergedColsCount":1,"Text":"вид объекта \n"},{"MergedColsCount":1,"Text":"площадь \n(кв. м) \n"},{"MergedColsCount":1,"Text":"страна \nрасположен ия \n"},{"MergedColsCount":1,"Text":"\n"},{"MergedColsCount":1,"Text":"\n"},{"MergedColsCount":1,"Text":"\n"}]],"Section":[[{"MergedColsCount":14,"Text":"Федеральное государственное бюджетное учреждение «Научно-исследовательский финансовый институт» \n"}]],"Data":[[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Супруг (супруга)          \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Земельный участок \n"},{"MergedColsCount":1,"Text":"Общая долевая \n(1/2) \n"},{"MergedColsCount":1,"Text":"901,00 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"Земельный участок \n"},{"MergedColsCount":2,"Text":"600,00 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"365301,13 \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Жилой дом \n"},{"MergedColsCount":1,"Text":"Общая долевая \n(1/2) \n"},{"MergedColsCount":1,"Text":"47,2 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":"    \n"},{"MergedColsCount":1,"Text":"                                    \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":1,"Text":"общая \nсовместная  \n"},{"MergedColsCount":1,"Text":"110,20 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":"    \n"},{"MergedColsCount":1,"Text":"                                    \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":1,"Text":"Общая долевая \n(2/3) \n"},{"MergedColsCount":1,"Text":"69,80 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":14,"Text":"Федеральное казенное учреждение «Государственное учреждение по эксплуатации административных зданий и дачного хозяйства Министерства финансов Российской Федерации» \n"}],[{"MergedColsCount":1,"Text":"1    \n"},{"MergedColsCount":1,"Text":"                                    \nЛесовой Н.А.              \n"},{"MergedColsCount":1,"Text":"Заместитель директора \n"},{"MergedColsCount":1,"Text":"Земельный участок \n"},{"MergedColsCount":1,"Text":"индивидуальная \n"},{"MergedColsCount":1,"Text":"802,00 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"Гараж  \n"},{"MergedColsCount":2,"Text":"18,5 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"Автомобиль легковой:  \nТойота лексус RX \n"},{"MergedColsCount":1,"Text":"2485332,80 \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":"    \n"},{"MergedColsCount":1,"Text":"                                   \n"},{"MergedColsCount":1,"Text":"    \n"},{"MergedColsCount":1,"Text":"Земельный участок \n"},{"MergedColsCount":1,"Text":"индивидуальная \n"},{"MergedColsCount":1,"Text":"1200,00 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":"    \n"},{"MergedColsCount":1,"Text":"                                   \n"},{"MergedColsCount":1,"Text":"    \n"},{"MergedColsCount":1,"Text":"Жилой дом \n"},{"MergedColsCount":1,"Text":"индивидуальная \n"},{"MergedColsCount":1,"Text":"135,80 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":1,"Text":"общая долевая, \n1/4 \n"},{"MergedColsCount":1,"Text":"87,80 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Хозяйственное строение \n"},{"MergedColsCount":1,"Text":"индивидуальная \n"},{"MergedColsCount":1,"Text":"24,00 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Нежилое помещение \n"},{"MergedColsCount":1,"Text":"индивидуальная \n"},{"MergedColsCount":1,"Text":"285,20 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":"    \n"},{"MergedColsCount":1,"Text":"                                  \n \nСупруг (супруга)          \n"},{"MergedColsCount":1,"Text":"  \n \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":1,"Text":"общая долевая, \n1/4 \n"},{"MergedColsCount":1,"Text":"43,30 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":2,"Text":"87,80 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"2299534,62 \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":"2 \n"},{"MergedColsCount":1,"Text":"Листиков М.В. \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":1,"Text":"индивидуальная \n"},{"MergedColsCount":1,"Text":"63,60 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"Автомобиль легковой:  \nФиат Добло \n"},{"MergedColsCount":1,"Text":"1037015,65 \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Гараж  \n"},{"MergedColsCount":1,"Text":"индивидуальная \n"},{"MergedColsCount":1,"Text":"18,00 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"Автомобиль легковой:  \nДэу Матиз \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"Автомобиль грузовой:  \nБАУ 1044 \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Супруг (супруга)          \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Земельный участок \n"},{"MergedColsCount":1,"Text":"индивидуальная \n"},{"MergedColsCount":1,"Text":"600,00 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":2,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Автомобиль легковой:  \nДэу Матиз \n"},{"MergedColsCount":1,"Text":"238687,09 \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"Садовый дом \n"},{"MergedColsCount":1,"Text":"индивидуальная \n"},{"MergedColsCount":1,"Text":"105,30 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":2,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":"3 \n"},{"MergedColsCount":1,"Text":"                                    \nОвсюк Л.А.                 \n"},{"MergedColsCount":1,"Text":"Главный   бухгалтер \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":1,"Text":"общая долевая, \n1/4 \n"},{"MergedColsCount":1,"Text":"59,00 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":2,"Text":"56,60 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"1798404,52 \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"                                  \nНесовершеннолетний \nребенок                  \n"},{"MergedColsCount":1,"Text":"  \n \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":2,"Text":"56,60 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"0,00 \n"},{"MergedColsCount":1,"Text":"- \n"}],[{"MergedColsCount":1,"Text":" \n"},{"MergedColsCount":1,"Text":"                                  \nНесовершеннолетний \nребенок                  \n"},{"MergedColsCount":1,"Text":"  \n \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"Квартира \n"},{"MergedColsCount":2,"Text":"56,60 \n"},{"MergedColsCount":1,"Text":"Россия \n"},{"MergedColsCount":1,"Text":"- \n"},{"MergedColsCount":1,"Text":"0,00 \n"},{"MergedColsCount":1,"Text":"- \n"}]]}';
let context = {input_id: "1", input_json: inputJson, declaration_json:"hkfhggkfjhgfk"};
let html  = handleBarsTemplate(context);
taskSource.innerHTML = html;

