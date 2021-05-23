
function menuCreateDesktop() {
      menu = [{
                "text":"главная",
                "href":"/",
              },
              {
                "text":"о&nbsp;проекте",
                "href":"/about.html",
              },
              {
                "text":"ведомства",
                "href":"/office/",
              },
              {
                "text":"декларанты",
                "href":"/person/",
              },
              {
                "text":"декларации",
                "href":"/section/",
              },
              {
                "text":"документы",
                "href":"/file/",
              },
              {
                "text":"статистика",
                "href":"/statistics/",
              },
             ]

      var menu_div = document.getElementById("menu_div");

      for (var i = 0; i < menu.length; i++) {
          var link = document.createElement('a');
          link.href = menu[i].href;
          link.innerHTML = menu[i].text;

          var spanNode = document.createElement('span');
          if (window.location.pathname == menu[i].href) {
                spanNode.className = "selected_menu";
          } else {
                spanNode.className = "not_selected_menu";
          }
          spanNode.appendChild(link);

          menu_div.appendChild(spanNode);

          var spaceNode = document.createElement('span');
          spaceNode.className = "menu_space";
          menu_div.appendChild(spaceNode);
      }
}

function showMobileMenu() {
  var menu = document.getElementById("mobileMenu");
  var content = document.getElementById("site-wrapper");

  if (menu.style.display === "block") {
    menu.style.display = "none";
    content.style.display = "block";
  } else {
    menu.style.display = "block";
    content.style.display = "none";
  }
};

function disableInput(className) {
    var nodes1 = document.getElementsByClassName(className);
    for(var i = 0; i < nodes1.length; i++) {
        var nodes2 = nodes1[i].getElementsByTagName('*');
        for(var k = 0; k < nodes2.length; k++) {
            nodes2[k].disabled = true;
            nodes2[k].style.display = "none";
        }
    }
}

if (window.matchMedia('(max-device-width: 480px)').matches) {
    if (window.location.pathname == "/") {
        showMobileMenu();
    }
    disableInput("desktop");
}
else {
    menuCreateDesktop();
    disableInput("mobile");
}