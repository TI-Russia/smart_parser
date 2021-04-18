
function menuCreate() {
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

menuCreate();

