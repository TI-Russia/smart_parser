using System;
using System.Collections.Generic;

namespace SmartParser.Lib
{
    public enum DeclarationField : UInt32
    {
        // the second byte
        StartsWithDigitMask = 0b00000001_00000000,
        CountryMask = 0b00000010_00000000,  // Россия, Украина
        RealtyTypeMask = 0b00000100_00000000, // квартира,  дача
        SquareMask = 0b00001000_00000000 | StartsWithDigitMask,
        OwnershipTypeMask = 0b00010000_00000000, //индивидуальная
        NaturalText = 0b00100000_00000000,
        Owned = 0b01000000_00000000,
        State = 0b10000000_00000000,
        Mixed = Owned | State,
        AllOwnTypes = Mixed | Owned | State,

        // the third byte
        MainDeclarant = 0b00000001_00000000_00000000,
        DeclarantSpouse = 0b00000010_00000000_00000000,
        DeclarantChild = 0b00000100_00000000_00000000,
        LandArea = 0b00001000_00000000_00000000,
        LivingHouse = 0b00010000_00000000_00000000,
        Appartment = 0b00100000_00000000_00000000,
        SummerHouse = 0b01000000_00000000_00000000,
        Garage = 0b10000000_00000000_00000000,

        //the first byte
        None = 0,
        DeclarantIndex = 1 | StartsWithDigitMask,
        RelativeTypeStrict = 2,
        NameOrRelativeType = 3,
        NameAndOccupationOrRelativeType = 4,
        Occupation = 5,
        Department = 6,

        Vehicle = 7,
        VehicleType = 8,
        VehicleModel = 9,

        DeclaredYearlyIncomeMask = 10,
        DeclaredYearlyIncome = DeclaredYearlyIncomeMask | StartsWithDigitMask,
        DeclaredYearlyIncomeThousandsMask = 11,
        DeclaredYearlyIncomeThousands = DeclaredYearlyIncomeThousandsMask | StartsWithDigitMask,
        DataSources = 12,
        VehicleYear = 13,
        IncomeYear = 14,
        OccupationOrRelativeType = 15,
        DeclaredYearlyOtherIncome = 16 | StartsWithDigitMask,
        DeclarantIndexAndName = 17 | StartsWithDigitMask,

        // Для случая, когда один и тот же набор колонок содержит сведения и о частной, и о государственной собственности
        MixedRealEstateType = Mixed | RealtyTypeMask,
        MixedRealEstateSquare = Mixed | SquareMask,
        MixedRealEstateCountry = Mixed | CountryMask,
        MixedRealEstateOwnershipType = Mixed | OwnershipTypeMask,
        MixedColumnWithNaturalText = Mixed | NaturalText,
        MixedLandAreaSquare = Mixed | SquareMask | LandArea,
        MixedLivingHouseSquare = Mixed | SquareMask | LivingHouse,
        MixedAppartmentSquare = Mixed | SquareMask | Appartment,
        MixedSummerHouseSquare = Mixed | SquareMask | SummerHouse,
        MixedGarageSquare = Mixed | SquareMask | Garage,

        // see 30429.docx for these columns
        DeclarantMixedColumnWithNaturalText = MainDeclarant | Mixed | NaturalText,
        SpouseMixedColumnWithNaturalText = DeclarantSpouse | Mixed | NaturalText,
        ChildMixedColumnWithNaturalText = DeclarantChild | Mixed | NaturalText,

        DeclarantVehicle = MainDeclarant | Vehicle,
        SpouseVehicle = DeclarantSpouse | Vehicle,
        ChildVehicle = DeclarantChild | Vehicle,

        DeclarantIncome = MainDeclarant | DeclaredYearlyIncome,
        SpouseIncome = DeclarantSpouse | DeclaredYearlyIncome,
        ChildIncome = DeclarantChild | DeclaredYearlyIncome,

        DeclarantIncomeInThousands = MainDeclarant | DeclaredYearlyIncomeThousands,
        SpouseIncomeInThousands = DeclarantSpouse | DeclaredYearlyIncomeThousands,
        ChildIncomeInThousands = DeclarantChild | DeclaredYearlyIncomeThousands,
        //=========

        OwnedRealEstateType = Owned | RealtyTypeMask,
        OwnedRealEstateOwnershipType = Owned | OwnershipTypeMask,
        OwnedRealEstateSquare = Owned | SquareMask,
        OwnedRealEstateCountry = Owned | CountryMask,
        OwnedColumnWithNaturalText = Owned | NaturalText,
        OwnedRealEstateTypeAndCountry = Owned | RealtyTypeMask | CountryMask,

        StatePropertyType = State | RealtyTypeMask,
        StatePropertySquare = State | SquareMask,
        StatePropertyCountry = State | CountryMask,
        StatePropertyOwnershipType = State | OwnershipTypeMask,
        StateColumnWithNaturalText = State | NaturalText,
        StateRealEstateTypeAndCountry = State | RealtyTypeMask | CountryMask,

        // Поля, которые мы собираем, но пока не сохраняем в JSON (first byte)
        AcquiredProperty = 101,
        MoneySources = 102,
        Comments = 103,
        TransactionSubject = 104,
        MoneyOnBankAccounts = 105,
        Securities = 106,
        Stocks = 107,
        MainWorkPositionIncome = 108,
        Spendings = 109

    }

}
