using System;
using System.Collections.Generic;

namespace TI.Declarator.ParserCommon
{
    public enum DeclarationField 
    {
        StartsWithDigitMask = 0b00000001_00000000,
        CountryMask =         0b00000010_00000000,  // Россия, Украина
        RealtyTypeMask =      0b00000100_00000000, // квартира,  дача
        SquareMask =          0b00001000_00000000 | StartsWithDigitMask,
        OwnershipTypeMask =   0b00010000_00000000, //индивидуальная
        NaturalText =         0b00100000_00000000,
        Owned =               0b01000000_00000000,
        State =               0b10000000_00000000,
        Mixed =               Owned | State,
        AllOwnTypes =         Mixed | Owned | State,

        None = 0,
        Number = 1 | StartsWithDigitMask,
        RelativeTypeStrict = 2,
        NameOrRelativeType = 3,
        NameAndOccupationOrRelativeType = 4,
        Occupation = 5,
        Department = 6,

        Vehicle = 7,
        VehicleType =  8,
        VehicleModel =  9,

        DeclaredYearlyIncome = 10 | StartsWithDigitMask,
        DeclaredYearlyIncomeThousands = 11 | StartsWithDigitMask,
        DataSources = 12,

        // Для случая, когда один и тот же набор колонок содержит сведения и о частной, и о государственной собственности
        MixedRealEstateType = Mixed | RealtyTypeMask,
        MixedRealEstateSquare = Mixed | SquareMask,
        MixedRealEstateCountry = Mixed | CountryMask,
        MixedRealEstateOwnershipType = Mixed | OwnershipTypeMask,
        MixedColumnWithNaturalText = Mixed | NaturalText,

        OwnedRealEstateType = Owned | RealtyTypeMask,
        OwnedRealEstateOwnershipType  = Owned | OwnershipTypeMask,
        OwnedRealEstateSquare = Owned | SquareMask,
        OwnedRealEstateCountry = Owned | CountryMask,
        OwnedColumnWithNaturalText = Owned | NaturalText,

        StatePropertyType = State | RealtyTypeMask,
        StatePropertySquare = State | SquareMask,
        StatePropertyCountry = State | CountryMask,
        StatePropertyOwnershipType = State | OwnershipTypeMask,
        StateColumnWithNaturalText = State | NaturalText,

        // Поля, которые мы собираем, но пока не сохраняем в JSON
        AcquiredProperty = 101,
        MoneySources = 102,
        Comments = 103,
    }

}
