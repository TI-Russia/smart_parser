var INC_ORDER = "↑";
var DEC_ORDER = "↓";

function compareValues(a, b, order_id) {
    if (a.indexOf(".") != -1 && b.indexOf(".") != -1) {
        a = parseFloat(a);
        b = parseFloat(b);
    }
    else if (!isNaN(+a) && !isNaN(+b)) {
        a = +a;
        b = +b;
    }
    if (order_id == DEC_ORDER) {
        return (a>b) ? -1 : (a<b) ? 1 : 0; // decrease
    }
    else {
        return (a<b) ? -1 : (a>b) ? 1 : 0; // increase
    }
}

function get_reverse_order(colnum) {
  s = table.rows[0].cells[colnum - 1].textContent

  if (s[s.length - 1] == INC_ORDER) {
    return DEC_ORDER;
  }
  else {
    return INC_ORDER;
  }
}

function set_order_char(colnum, order_id) {
    s = table.rows[0].cells[colnum - 1].textContent;
    while (s.length > 0 && (s[s.length - 1] == DEC_ORDER|| s[s.length - 1] == INC_ORDER) ) {
        s = s.substring(0, s.length - 1);
    }
    table.rows[0].cells[colnum - 1].innerHTML  = "<div class=\"clickable\">" + s + order_id + "<div>"
}

function sortTable(colnum) {
  // get all the rows in this table:
  let rows = Array.from(table.querySelectorAll(`tr`));

  // but ignore the heading row:
  rows = rows.slice(1);

  // set up the queryselector for getting the indicated
  // column from a row, so we can compare using its value:
  let qs = `td:nth-child(${colnum}`;
  let order_id = get_reverse_order(colnum);

  // and then just... sort the rows:
  rows.sort( (r1,r2) => {
    // get each row's relevant column
    let t1 = r1.querySelector(qs);
    let t2 = r2.querySelector(qs);

    // and then effect sorting by comparing their content:
    return compareValues(t1.textContent, t2.textContent, order_id);
  });

  // and then the magic part that makes the sorting appear on-page:
  rows.forEach(row => table.appendChild(row));
  set_order_char(colnum, order_id)
}