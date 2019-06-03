using System;

namespace TI.Declarator.ParserCommon
{
    /*
     Объекты недвижимости, находящиеся в пользовании 
     */
    public static class HeaderHelpers
    {
        public static bool IsSecondLevelHeader(string str)
        {
            string strLower = str.ToLower();
            return (strLower.Contains("объекты") ||
                    strLower.Contains("недвижимости"));
        }
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
            str = NormalizeString(str);
            if (str.IsNumber()) { return DeclarationField.Number; }
            if (str.IsNameOrRelativeType()) { return DeclarationField.NameOrRelativeType; }
            if (str.IsOccupation()) { return DeclarationField.Occupation; }

            if (str.IsMixedRealEstateType()) { return DeclarationField.MixedRealEstateType; }
            if (str.IsMixedRealEstateSquare()) { return DeclarationField.MixedRealEstateSquare; }
            if (str.IsMixedRealEstateCountry()) { return DeclarationField.MixedRealEstateCountry; }
            if (str.IsMixedRealEstateOwnershipType()) { return DeclarationField.MixedRealEstateOwnershipType; }

            if (str.IsOwnedRealEstateType()) { return DeclarationField.OwnedRealEstateType; }
            if (str.IsOwnedRealEstateOwnershipType()) { return DeclarationField.OwnedRealEstateOwnershipType; }
            if (str.IsOwnedRealEstateSquare()) { return DeclarationField.OwnedRealEstateSquare; }
            if (str.IsOwnedRealEstateCountry()) { return DeclarationField.OwnedRealEstateCountry; }
            if (str.IsStatePropertyType()) { return DeclarationField.StatePropertyType; }
            if (str.IsStatePropertySquare()) { return DeclarationField.StatePropertySquare; }
            if (str.IsStatePropertyCountry()) { return DeclarationField.StatePropertyCountry; }
            if (str.IsVehicleType()) { return DeclarationField.VehicleType; }
            if (str.IsVehicleModel()) { return DeclarationField.VehicleModel; }
            if (str.IsVehicle()) { return DeclarationField.Vehicle; }
            if (str.IsDeclaredYearlyIncomeThousands()) { return DeclarationField.DeclaredYearlyIncomeThousands; }
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

        private static bool IsNameOrRelativeType(this string s)
        {
            return (s.Contains("фамилия") ||
                    s.Contains("фио") ||
                    s.Contains("ф.и.о"));
        }

        private static bool IsOccupation(this string s)
        {
            return (s.Contains("должность") || 
                    s.Contains("должностей"));
        }


        private static bool IsMixedRealEstateOwnershipType(this string s)
        {
            return (s.Contains("праве собственности") &&
                    s.Contains("пользовании") &&
                    s.Contains("вид собственности"));
        }

        private static bool HasRealEstateTypeStr(this string s)
        {
            return (s.Contains("вид объекта") ||
             s.Contains("вид объектов") ||
             s.Contains("виды объектов") ||
             s.Contains("виды недвижимости") ||
             s.Contains("вид и наименование имущества") ||
             s.Contains("вид недвижимости"));
        }
        private static bool HasStateString(this string s)
        {
            return s.Contains("пользовании");
        }
        private static bool HasOwnedString(this string s)
        {
            return s.Contains("собственности");
        }
        private static bool HasSquareString(this string s)
        {
            return s.Contains("площадь");
        }

        private static bool HasCountryString(this string s)
        {
            return s.Contains("страна");
        }
        
        private static bool IsStateColumn(this string s)
        {
            return    !HasOwnedString(s)
                    && HasStateString(s);
        }

        private static bool IsOwnedColumn(this string s)
        {
            return       HasOwnedString(s)
                    &&  !HasStateString(s);
        }

        private static bool IsMixedColumn(this string s)
        {
            return     HasOwnedString(s)
                    && HasStateString(s);
        }

        private static bool IsOwnedRealEstateType(this string s)
        {
            return IsOwnedColumn(s) && HasRealEstateTypeStr(s);
        }

        private static bool IsOwnedRealEstateOwnershipType(this string s)
        {
            return IsOwnedColumn(s) && s.Contains("вид собственности");
        }

        private static bool IsOwnedRealEstateSquare(this string s)
        {
            return IsOwnedColumn(s) &&  HasSquareString(s);
        }

        private static bool IsOwnedRealEstateCountry(this string s)
        {
            return IsOwnedColumn(s) && HasCountryString(s);
        }

        private static bool IsStatePropertyType(this string s)
        {
            return IsStateColumn(s) && HasRealEstateTypeStr(s);
        }

        private static bool IsStatePropertySquare(this string s)
        {
            return IsStateColumn(s) && HasSquareString(s);
        }

        private static bool IsStatePropertyCountry(this string s)
        {
            return IsStateColumn(s) && HasCountryString(s);
        }

        private static bool IsMixedRealEstateType(this string s)
        {
            return IsMixedColumn(s) && HasRealEstateTypeStr(s);
        }

        private static bool IsMixedRealEstateSquare(this string s)
        {
            return IsMixedColumn(s) && HasSquareString(s);
        }

        private static bool IsMixedRealEstateCountry(this string s)
        {
            return IsMixedColumn(s) && HasCountryString(s);
        }

        private static bool IsVehicle(this string s)
        {
            return ((s.Contains("транспорт") || s.Contains("движимое имущество")) &&
                    (!s.Contains("источник")));
        }

        private static bool IsVehicleType(this string s)
        {
            return ((s.Contains("транспорт") || s.Contains("движимое имущество")) &&
                    ((s.Contains("вид") && !s.Contains("марк"))));
        }

        private static bool IsVehicleModel(this string s)
        {
            return ((s.Contains("транспорт") || s.Contains("движимое имущество")) &&
                    ((s.Contains("марка") && !s.Contains("вид"))));
        }

        private static bool IsDeclaredYearlyIncome(this string str)
        {
            string strLower = str.Replace(" ", "").Replace("-", "");
            return (strLower.Contains("годовойдоход") 
                    || strLower.Contains("годовогодохода")
                    || strLower.Contains("суммадохода") 
                    || strLower.Contains("декларированныйдоход")
                    || strLower.Contains("декларированногодохода")
                   );
        }

        private static bool IsDeclaredYearlyIncomeThousands(this string s)
        {
            return s.IsDeclaredYearlyIncome() && s.Contains("тыс.");
        }

        private static bool IsDataSources(this string s)
        {
            return s.Contains("сведен");
        }
    }
}
