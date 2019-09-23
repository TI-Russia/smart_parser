using System;

namespace TI.Declarator.ParserCommon
{

    public enum DeclarationField : short
    {
        None = 0,
        Number,
        RelativeTypeStrict,
        NameOrRelativeType,
        NameAndOccupationOrRelativeType,
        Occupation,
        Department,

        // Для случая, когда один и тот же набор колонок содержит сведения и о частной, и о государственной собственности
        MixedRealEstateType,
        MixedRealEstateSquare,
        MixedRealEstateCountry,
        MixedRealEstateOwnershipType,
        MixedColumnWithNaturalText,

        OwnedRealEstateType,
        OwnedRealEstateOwnershipType,
        OwnedRealEstateSquare,
        OwnedRealEstateCountry,
        OwnedColumnWithNaturalText,

        StatePropertyType,
        StatePropertySquare,
        StatePropertyCountry,
        StatePropertyOwnershipType,
        StateColumnWithNaturalText,

        Vehicle,
        DeclaredYearlyIncome,
        DeclaredYearlyIncomeThousands,
        DataSources,
        VehicleType,
        VehicleModel,
    }

}
