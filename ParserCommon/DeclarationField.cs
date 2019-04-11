using System;

namespace TI.Declarator.ParserCommon
{
    public enum DeclarationField : short
    {
        None = 0,
        Number,
        NameOrRelativeType,
        Occupation,

        // Для случая, когда один и тот же набор колонок содержит сведения и о частной, и о государственной собственности
        MixedRealEstateType,
        MixedRealEstateArea,
        MixedRealEstateCountry,
        MixedRealEstateOwnershipType,

        OwnedRealEstateType,
        OwnedRealEstateOwnershipType,
        OwnedRealEstateArea,
        OwnedRealEstateCountry,

        StatePropertyType,
        StatePropertyArea,
        StatePropertyCountry,

        Vehicle,
        DeclaredYearlyIncome,
        DataSources,
        VehicleType,
        VehicleModel,
    }
}
