using System;

namespace TI.Declarator.ParserCommon
{
    public static class HeaderHelpers
    {
        public static DeclarationField GetField(string str)
        {
            if (str.IsNumber()) { return DeclarationField.Number; }
            if (str.IsNameOrRelativeType()) { return DeclarationField.NameOrRelativeType; }
            if (str.IsOccupation()) { return DeclarationField.Occupation; }
            if (str.IsRealEstateType()) { return DeclarationField.RealEstateType; }
            if (str.IsRealEstateArea()) { return DeclarationField.RealEstateArea; }
            if (str.IsRealEstateCountry()) { return DeclarationField.RealEstateCountry; }
            if (str.IsRealEstateOwnershipType()) { return DeclarationField.RealEstateOwnershipType; }
            if (str.IsOwnedRealEstateType()) { return DeclarationField.OwnedRealEstateType; }
            if (str.IsOwnedRealEstateOwnershipType()) { return DeclarationField.OwnedRealEstateOwnershipType; }
            if (str.IsOwnedRealEstateArea()) { return DeclarationField.OwnedRealEstateArea; }
            if (str.IsOwnedRealEstateCountry()) { return DeclarationField.OwnedRealEstateCountry; }
            if (str.IsStatePropertyType()) { return DeclarationField.StatePropertyType; }
            if (str.IsStatePropertyArea()) { return DeclarationField.StatePropertyArea; }
            if (str.IsStatePropertyCountry()) { return DeclarationField.StatePropertyCountry; }           
            if (str.IsVehicle()) { return DeclarationField.Vehicle; }
            if (str.IsDeclaredYearlyIncome()) { return DeclarationField.DeclaredYearlyIncome; }
            if (str.IsDataSources()) { return DeclarationField.DataSources; }

            throw new Exception($"Could not determine column type for header {str}.");
        }

        private static bool IsNumber(this string str)
        {
            return str.Contains("№") || str.Contains("N п/п");
        }

        private static bool IsNameOrRelativeType(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("фамилия") ||
                    strLower.Contains("фио") ||
                    strLower.Contains("ф.и.о"));
        }

        private static bool IsOccupation(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("должность"));
        }

        private static bool IsRealEstateType(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("собственности") &&
                    strLower.Contains("пользовании") &&
                    (strLower.Contains("вид объекта") || strLower.Contains("вид объектов") ||
                     strLower.Contains("вид и наименование имущества")));
        }

        private static bool IsRealEstateArea(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("собственности") &&
                    strLower.Contains("пользовании") &&
                    strLower.Contains("площадь"));
        }

        private static bool IsRealEstateCountry(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("собственности") &&
                    strLower.Contains("пользовании") &&
                    strLower.Contains("страна"));
        }

        private static bool IsRealEstateOwnershipType(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("праве собственности") &&
                    strLower.Contains("пользовании") &&
                    strLower.Contains("вид собственности"));
        }

        private static bool IsOwnedRealEstateType(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("собственности") &&
                    (strLower.Contains("вид объекта") || strLower.Contains("вид объектов")));
        }

        private static bool IsOwnedRealEstateOwnershipType(this string str)
        {
            string strLower = str.ToLower();
            return (!strLower.Contains("пользовании") && strLower.Contains("вид собственности"));
        }

        private static bool IsOwnedRealEstateArea(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("собственности") && strLower.Contains("площадь"));
        }

        private static bool IsOwnedRealEstateCountry(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("собственности") && strLower.Contains("страна"));
        }

        private static bool IsStatePropertyType(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("пользовании") &&
                    (strLower.Contains("вид объекта") || strLower.Contains("вид объектов")));
        }

        private static bool IsStatePropertyArea(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("пользовании") && strLower.Contains("площадь"));
        }

        private static bool IsStatePropertyCountry(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("пользовании") && strLower.Contains("страна"));
        }

        private static bool IsVehicle(this string str)
        {
            string strLower = str.ToLower();
            return ((strLower.Contains("транспорт") || strLower.Contains("движимое имущество")) &&
                    (!str.Contains("источник")));
        }

        private static bool IsDeclaredYearlyIncome(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("годовой доход") || strLower.Contains("годового дохода") ||
                    strLower.Contains("сумма дохода") || strLower.Contains("декларированный доход"));
        }

        private static bool IsDataSources(this string str)
        {
            string strLower = str.ToLower();
            return strLower.Contains("сведен");
        }
    }
}
