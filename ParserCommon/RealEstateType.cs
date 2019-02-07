using System;

namespace TI.Declarator.ParserCommon
{
/*
https://declarator.org/api/realestate-type/

"name": "Land plot" "Земельный участок"
"name": "Garage", "Гараж" "Иное"
"name": "Residential house", "Жилой дом"
"name": "Apartment" "Квартира"
"name": "Dacha", "Дача"
"name": "Other", 
"name": "Linear object", "Линейный объект"
*/

    public enum RealEstateType
    {
        PlotOfLand = 1,
        Garage = 2,
        ResidentialHouse = 3,
        Apartment = 4, 
        Dacha = 5,
        Other = 6,
        InfrastructureFacility = 7,
    }
}