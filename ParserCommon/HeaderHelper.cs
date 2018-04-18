using System;

namespace TI.Declarator.ParserCommon
{
    public static class HeaderHelpers
    {
        public static Field GetField(string str)
        {
            if (str.IsNumber()) { return Field.Number; }
            if (str.IsNameOrRelativeType()) { return Field.NameOrRelativeType; }
            if (str.IsOccupation()) { return Field.Occupation; }
            if (str.IsOwnedRealEstateType()) { return Field.OwnedRealEstateType; }
            if (str.IsRealEstateOwnershipType()) { return Field.RealEstateOwnershipType; }
            if (str.IsOwnedRealEstateArea()) { return Field.OwnedRealEstateArea; }
            if (str.IsOwnedRealEstateCountry()) { return Field.OwnedRealEstateCountry; }
            if (str.IsStatePropertyType()) { return Field.StatePropertyType; }
            if (str.IsStatePropertyArea()) { return Field.StatePropertyArea; }
            if (str.IsStatePropertyCountry()) { return Field.StatePropertyCountry; }
            if (str.IsVehicle()) { return Field.Vehicle; }
            if (str.IsDeclaredYearlyIncome()) { return Field.DeclaredYearlyIncome; }
            if (str.IsDataSources()) { return Field.DataSources; }

            throw new Exception("Could not determine column type.");
        }

        private static bool IsNumber(this string str)
        {
            return str.Contains("№");
        }

        private static bool IsNameOrRelativeType(this string str)
        {
            return (str.Contains("Фамилия") || str.Contains("ФИО"));
        }

        private static bool IsOccupation(this string str)
        {
            return str.Contains("Должность");
        }

        private static bool IsOwnedRealEstateType(this string str)
        {
            return (str.Contains("собственности") && str.Contains("вид объекта"));
        }

        private static bool IsRealEstateOwnershipType(this string str)
        {
            return (str.Contains("вид собственности"));
        }

        private static bool IsOwnedRealEstateArea(this string str)
        {
            return (str.Contains("собственности") && str.Contains("площадь"));
        }

        private static bool IsOwnedRealEstateCountry(this string str)
        {
            return (str.Contains("собственности") && str.Contains("страна"));
        }

        private static bool IsStatePropertyType(this string str)
        {
            return (str.Contains("пользовании") && str.Contains("вид объекта"));
        }

        private static bool IsStatePropertyArea(this string str)
        {
            return (str.Contains("пользовании") && str.Contains("площадь"));
        }

        private static bool IsStatePropertyCountry(this string str)
        {
            return (str.Contains("пользовании") && str.Contains("страна"));
        }

        private static bool IsVehicle(this string str)
        {
            return str.Contains("Транспорт");
        }

        private static bool IsDeclaredYearlyIncome(this string str)
        {
            return str.Contains("годовой доход");
        }

        private static bool IsDataSources(this string str)
        {
            return str.Contains("Сведения");
        }
    }
}
