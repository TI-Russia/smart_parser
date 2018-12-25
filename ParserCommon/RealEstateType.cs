using System;

namespace TI.Declarator.ParserCommon
{
    /*
    База данных делит объекты недвижимости на 5 типов: 
        гараж; земельный участок; дача; дом; квартира; линейный объект.Также присутствует тип “иное” 

    */
    public enum RealEstateType
    {
        Undefined = 0,
        GardenPlot = 1,
        Building = 2,
        UnfinishedBuilding = 3,
        ParkingSpace = 4,
        Rooms = 5,
        Room = 6,
        Apartment = 7,
        Other = 8,
        PlotOfLand = 9,
        HabitableHouse = 10,
        HabitableBuilding = 11,
        HabitableSpace = 12,
        House = 13,
        DachaHouse = 14,
        DachaBuilding = 15,
        Dacha = 16,
        Garage = 17,
        IndustrialPlot = 1001
    }
}
