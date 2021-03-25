if (typeof window.run_under_webstorm == 'undefined') {

    exports.Task = extend(TolokaHandlebarsTask, function (options) {
        TolokaHandlebarsTask.call(this, options);
    }, {
        onRender: function () {
            // DOM-элемент задания сформирован (доступен через #getDOMElement())
            ShowDifferences(this.getDOMElement());
        },
        onDestroy: function () {
            // Задание завершено, можно освобождать (если были использованы) глобальные ресурсы
        }
    });

}

function extend(ParentClass, constructorFunction, prototypeHash) {

    constructorFunction = constructorFunction || function () {
    };
    prototypeHash = prototypeHash || {};
    if (ParentClass) {
        constructorFunction.prototype = Object.create(ParentClass.prototype);
    }
    for (var i in prototypeHash) {
        constructorFunction.prototype[i] = prototypeHash[i];
    }
    return constructorFunction;
}

Handlebars.registerHelper('get_relatives', function () {
    // поддерживаем оба формата (title case и lower case)
    return [null, "Супруг(а)", "Ребенок", "супруг(а)", "ребенок", "иное"]
})

Handlebars.registerHelper('get_income', function (section, relative) {
    if (typeof section.incomes == 'undefined') {
        return "";
    }

    for (let i = 0; i < section.incomes.length; i++) {
        if (section.incomes[i].relative == relative) {
            let income = section.incomes[i].size;
            return Math.round( income).toLocaleString('ru-RU');
        }
    }
    return "";
});


Handlebars.registerHelper('get_vehicles', function (section, relative) {
    if (typeof section.vehicles == 'undefined') {
        return "";
    }
    let values = [];
    for (let i = 0; i < section.vehicles.length; i++) {
        if (section.vehicles[i].relative == relative) {
            values.push(section.vehicles[i].text);
        }
    }
    return values.join("; ");
});

Handlebars.registerHelper('get_realty', function (section, relative) {
    if (typeof section.real_estates == 'undefined') {
        return "";
    }
    let values = [];
    for (let i = 0; i < section.real_estates.length; i++) {
        if (section.real_estates[i].relative == relative) {
            let r = section.real_estates[i];
            let text = "";
            if (typeof r.type_raw !== 'undefined') {
                text += r.type_raw.toLowerCase()
            }
            if (typeof r.text!== 'undefined') {
                text += r.text
            }
            if (typeof r.square !== 'undefined') {
                text += "&nbsp;" + r.square + " м<sup>2</sup>";
            }
            if (typeof r.owntype_raw !== 'undefined') {
                text += " (" + r.owntype_raw.toLowerCase() + ")";
            }

            values.push(text);
        }
    }
    return values.join("<br/>");
});


function collect_cell_values(row, start, end) {
    var values= new Set();
    for (let j=start; j < end; j++) {
        let v = row.cells[j].innerText.toLowerCase().trim();
        if (v !== "") {
            values.add(v);
        }
    }
    return values;
}

function isSuperset(set, subset) {
    for (var elem of subset) {
        if (!set.has(elem)) {
            return false;
        }
    }
    return true;
}
function equal_sets(s1, s2){
    return isSuperset(s1, s2) && isSuperset(s2, s1);
}
function ShowDifferences(task_element) {
    let tables = task_element.getElementsByClassName("main_task_table");
    for (let i = 0; i < tables.length; i++) {
        let emptyRowstoRemove = []
        for (let k = 0; k < tables[i].rows.length; k++) {
            let row = tables[i].rows[k];
            if (row.parentElement.tagName !== "TBODY") {
                continue;
            }
            let center = 0;
            for (let j=0; j < row.cells.length; j++) {
                if (row.cells[j].classList.contains('central_cell')) {
                    center = j;
                    break;
                }
            }
            var leftSet = collect_cell_values(row, 1, center);
            var rightSet = collect_cell_values(row, center + 1, row.cells.length);
            if (leftSet.size == 0 && rightSet.size == 0) {
                emptyRowstoRemove.push(row);
            }
            else
            if (equal_sets(leftSet,rightSet)) {
                row.style.color = "#ccc";
            }
        }
        for (let k=0; k < emptyRowstoRemove.length; k++) {
            emptyRowstoRemove[k].parentElement.removeChild(emptyRowstoRemove[k]);
        }
    }
}
