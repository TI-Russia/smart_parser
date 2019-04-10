using System;

namespace TI.Declarator.ParserCommon
{
    /*
     Объекты недвижимости, находящиеся в пользовании 
     */
    public static class HeaderHelpers
    {
        public static DeclarationField GetField(string str)
        {
            DeclarationField field = TryGetField(str);
            if (field == DeclarationField.None)
            {
                throw new Exception($"Could not determine column type for header {str}.");
            }
            return field;
        }

        public static DeclarationField TryGetField(string str)
        {
            if (str.IsNumber()) { return DeclarationField.Number; }
            if (str.IsNameOrRelativeType()) { return DeclarationField.NameOrRelativeType; }
            if (str.IsOccupation()) { return DeclarationField.Occupation; }

            if (str.IsMixedRealEstateType()) { return DeclarationField.MixedRealEstateType; }
            if (str.IsMixedRealEstateArea()) { return DeclarationField.MixedRealEstateArea; }
            if (str.IsMixedRealEstateCountry()) { return DeclarationField.MixedRealEstateCountry; }
            if (str.IsMixedRealEstateOwnershipType()) { return DeclarationField.MixedRealEstateOwnershipType; }

            if (str.IsOwnedRealEstateType()) { return DeclarationField.OwnedRealEstateType; }
            if (str.IsOwnedRealEstateOwnershipType()) { return DeclarationField.OwnedRealEstateOwnershipType; }
            if (str.IsOwnedRealEstateArea()) { return DeclarationField.OwnedRealEstateArea; }
            if (str.IsOwnedRealEstateCountry()) { return DeclarationField.OwnedRealEstateCountry; }
            if (str.IsStatePropertyType()) { return DeclarationField.StatePropertyType; }
            if (str.IsStatePropertyArea()) { return DeclarationField.StatePropertyArea; }
            if (str.IsStatePropertyCountry()) { return DeclarationField.StatePropertyCountry; }
            if (str.IsVehicleType()) { return DeclarationField.VehicleType; }
            if (str.IsVehicleModel()) { return DeclarationField.VehicleModel; }
            if (str.IsVehicle()) { return DeclarationField.Vehicle; }
            if (str.IsDeclaredYearlyIncome()) { return DeclarationField.DeclaredYearlyIncome; }
            if (str.IsDataSources()) { return DeclarationField.DataSources; }

            return DeclarationField.None;
            //throw new Exception($"Could not determine column type for header {str}.");
        }

        private static string NormalizeString(string str)
        {
            return string.Join(" ", str.ToLower().Split(new char[] {' ', '\n', '\t'}, StringSplitOptions.RemoveEmptyEntries));
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
            return (strLower.Contains("должность") || 
                    strLower.Contains("должностей"));
        }

        private static bool IsMixedRealEstateType(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("собственности") &&
                    strLower.Contains("пользовании") &&
                    (strLower.Contains("вид объекта") || strLower.Contains("вид объектов") ||
                     strLower.Contains("вид и наименование имущества")));
        }

        private static bool IsMixedRealEstateArea(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("собственности") &&
                    strLower.Contains("пользовании") &&
                    strLower.Contains("площадь"));
        }

        private static bool IsMixedRealEstateCountry(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("собственности") &&
                    strLower.Contains("пользовании") &&
                    strLower.Contains("страна"));
        }

        private static bool IsMixedRealEstateOwnershipType(this string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("праве собственности") &&
                    strLower.Contains("пользовании") &&
                    strLower.Contains("вид собственности"));
        }

        private static bool IsOwnedRealEstateType(this string str)
        {
            string strLower = NormalizeString(str);//str.ToLower();

            return (strLower.Contains("собственности") &&
                    (strLower.Contains("вид объекта") || 
                     strLower.Contains("вид объектов") ||
                     strLower.Contains("вид недвижимости") ));
        }

        private static bool IsOwnedRealEstateOwnershipType(this string str)
        {
            string strLower = str.Replace("  ", " ").ToLower();
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
            string strLower = NormalizeString(str);//str.ToLower();

            return (strLower.Contains("пользовании") &&
                    (strLower.Contains("вид объекта") ||
                     strLower.Contains("вид объектов") ||
                     strLower.Contains("вид недвижимости") ));
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

        private static bool IsVehicleType(this string str)
        {
            string strLower = str.ToLower();
            return ((strLower.Contains("транспорт") || strLower.Contains("движимое имущество")) &&
                    ((str.Contains("вид") && !str.Contains("марк"))));
        }

        private static bool IsVehicleModel(this string str)
        {
            string strLower = str.ToLower();
            return ((strLower.Contains("транспорт") || strLower.Contains("движимое имущество")) &&
                    ((str.Contains("марка") && !str.Contains("вид"))));
        }

        private static bool IsDeclaredYearlyIncome(this string str)
        {
            string strLower = NormalizeString(str);
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
