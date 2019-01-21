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
        //Undefined = 0,
        //GardenPlot = 1, //-
        //Building = 2, // -
        //UnfinishedBuilding = 3, // -
        //ParkingSpace = 4, // -
        //Rooms = 5, //-
        //Room = 6, //-
        Apartment = 7, //
        Other = 8, //
        PlotOfLand = 9, //
        //HabitableHouse = 10, // ->ResidentialHouse
        //HabitableBuilding = 11,
        //HabitableSpace = 12,
        //House = 13, // ->ResidentialHouse
        //DachaHouse = 14, // -
        //DachaBuilding = 15, // -
        Dacha = 16, //
        Garage = 17, //
        LinearObject, //
        //IndustrialPlot = 1001, // -
        ResidentialHouse
    }
}
