using System;

namespace TI.Declarator.ParserCommon
{
    public enum DeclarationField : short
    {
        None = 0,
        Number,
        RelativeTypeStrict,
        NameOrRelativeType,
        Occupation,

        // Для случая, когда один и тот же набор колонок содержит сведения и о частной, и о государственной собственности
        MixedRealEstateType,
        MixedRealEstateSquare,
        MixedRealEstateCountry,
        MixedRealEstateOwnershipType,

        OwnedRealEstateType,
        OwnedRealEstateOwnershipType,
        OwnedRealEstateSquare,
        OwnedRealEstateCountry,

        StatePropertyType,
        StatePropertySquare,
        StatePropertyCountry,

        Vehicle,
        DeclaredYearlyIncome,
        DeclaredYearlyIncomeThousands,
        DataSources,
        VehicleType,
        VehicleModel,
    }
}
