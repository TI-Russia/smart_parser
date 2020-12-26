function compareValues(a, b) {
    if (a.indexOf(".") != -1 && b.indexOf(".") != -1) {
        a = parseFloat(a);
        b = parseFloat(b);
    }
    else if (!isNaN(+a) && !isNaN(+b)) {
        a = +a;
        b = +b;
    }
    return (a<b) ? -1 : (a>b) ? 1 : 0;
}

function sortTable(colnum) {
  // get all the rows in this table:
  let rows = Array.from(table.querySelectorAll(`tr`));

  // but ignore the heading row:
  rows = rows.slice(1);

  // set up the queryselector for getting the indicated
  // column from a row, so we can compare using its value:
  let qs = `td:nth-child(${colnum}`;

  // and then just... sort the rows:
  rows.sort( (r1,r2) => {
    // get each row's relevant column
    let t1 = r1.querySelector(qs);
    let t2 = r2.querySelector(qs);

    // and then effect sorting by comparing their content:
    return compareValues(t1.textContent,t2.textContent);
  });

  // and then the magic part that makes the sorting appear on-page:
  rows.forEach(row => table.appendChild(row));
}