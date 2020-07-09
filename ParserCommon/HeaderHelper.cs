using System;
using System.Linq;
using static Algorithms.LevenshteinDistance;

namespace TI.Declarator.ParserCommon
{
    public static class HeaderHelpers
    {
        public static bool HasRealEstateStr(string str)
        {
            string strLower = str.ToLower().Replace("-", "");
            return strLower.Contains("недвижимости")
                || strLower.Contains("недвижимого");
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
            if (str.IsNameAndOccupation()) { return DeclarationField.NameAndOccupationOrRelativeType; }
            if (str.IsName()) { return DeclarationField.NameOrRelativeType; }
            if (str.IsRelativeType()) { return DeclarationField.RelativeTypeStrict; }
            if (str.IsOccupation()) { return DeclarationField.Occupation; }
            if (str.IsDepartment()) { return DeclarationField.Department; }

            if (str.IsMixedRealEstateType()) { return DeclarationField.MixedRealEstateType; }
            if (str.IsMixedRealEstateSquare() && !str.IsMixedRealEstateCountry()) { return DeclarationField.MixedRealEstateSquare; }
            if (str.IsMixedRealEstateCountry() && !str.IsMixedRealEstateSquare() ) { return DeclarationField.MixedRealEstateCountry; }
            if (str.IsMixedRealEstateOwnershipType() && !str.IsMixedRealEstateSquare()) { return DeclarationField.MixedRealEstateOwnershipType; }

            if (str.IsOwnedRealEstateType()) { return DeclarationField.OwnedRealEstateType; }
            if (str.IsOwnedRealEstateOwnershipType()) { return DeclarationField.OwnedRealEstateOwnershipType; }
            if (str.IsOwnedRealEstateSquare()) { return DeclarationField.OwnedRealEstateSquare; }
            if (str.IsOwnedRealEstateCountry()) { return DeclarationField.OwnedRealEstateCountry; }

            if (str.IsStatePropertyType()) { return DeclarationField.StatePropertyType; }
            if (str.IsStatePropertySquare()) { return DeclarationField.StatePropertySquare; }
            if (str.IsStatePropertyCountry()) { return DeclarationField.StatePropertyCountry; }
            if (str.IsStatePropertyOwnershipType()) { return DeclarationField.StatePropertyOwnershipType; }

            if (str.HasChild() && str.IsVehicle() && !(str.HasMainDeclarant() || str.HasSpouse())) {
                return DeclarationField.ChildVehicle; }

            if (str.HasSpouse() && str.IsVehicle() && !(str.HasMainDeclarant() || str.HasChild()))  {
                return DeclarationField.SpouseVehicle; }
            if (str.HasMainDeclarant() && str.IsVehicle()) { return DeclarationField.DeclarantVehicle; }

            if (str.IsVehicleType()) { return DeclarationField.VehicleType; }
            if (str.IsVehicleModel()) { return DeclarationField.VehicleModel; }
            if (str.IsVehicle()) { return DeclarationField.Vehicle; }
            if (str.IsDeclaredYearlyIncomeThousands()) {
                if (str.HasChild()) { return DeclarationField.ChildIncomeInThousands; }
                if (str.HasSpouse()) { return DeclarationField.SpouseIncomeInThousands; }
                if (str.HasMainDeclarant()) { return DeclarationField.DeclarantIncomeInThousands; }
                return DeclarationField.DeclaredYearlyIncomeThousands; 
            }

            if (str.IsDeclaredYearlyIncome())
            {
                if (str.HasChild() && !(str.HasMainDeclarant() || str.HasSpouse())) { return DeclarationField.ChildIncome; }
                if (str.HasSpouse() && !(str.HasMainDeclarant() || str.HasChild())) { return DeclarationField.SpouseIncome; }
                if (str.HasMainDeclarant()) { return DeclarationField.DeclarantIncome; }
                return DeclarationField.DeclaredYearlyIncome;
            }

            if (str.IsDataSources()) { return DeclarationField.DataSources; }
            if (str.IsComments()) { return DeclarationField.Comments; }

            if (str.IsMixedRealEstateDeclarant()) { return DeclarationField.DeclarantMixedColumnWithNaturalText; }
            if (str.IsMixedRealEstateSpouse()) { return DeclarationField.SpouseMixedColumnWithNaturalText; }
            if (str.IsMixedRealEstateChild()) { return DeclarationField.ChildMixedColumnWithNaturalText; }

            if (str.IsMixedRealEstate()) { return DeclarationField.MixedColumnWithNaturalText; }
            if (str.IsOwnedRealEstate()) { return DeclarationField.OwnedColumnWithNaturalText; }
            if (str.IsStateRealEstate()) { return DeclarationField.StateColumnWithNaturalText; }

            if (str.IsAcquiredProperty()) { return DeclarationField.AcquiredProperty; }
            if (str.IsTransactionSubject()) { return DeclarationField.TransactionSubject; }
            if (str.IsMoneySources()) { return DeclarationField.MoneySources; }


            if (HasSquareString(str)) { return DeclarationField.MixedRealEstateSquare; }
            if (HasCountryString(str)) { return DeclarationField.MixedRealEstateCountry; }
            return DeclarationField.None;
        }

        private static string NormalizeString(string str)
        {
            return string.Join(" ", str.ToLower().Split(new char[] {' ', '\n', '\t'}, StringSplitOptions.RemoveEmptyEntries))
                         .RemoveStupidTranslit();
        }

        public static bool IsNumber(this string str)
        {
            str = str.Replace(" ", "");
            return str.StartsWith("№") || 
                   str.ToLower().Contains("nп/п") || 
                   str.ToLower().Replace("\\", "/").Equals("п/п") || 
                   str.ToLower().Contains("nпп");
        }

        public static bool IsName(this string s)
        {
            string clean = s.Replace("-", "").Replace("\n", "").Replace(" ", "").ToLower();
            return (clean.Contains("фамилия") ||
                    clean.Contains("фамилимя") ||
                    clean.Contains("фио") ||
                    clean.Contains(".иф.о.") ||
                    clean.Contains("ф.и.о"));
        }
        public static bool IsNameAndOccupation(this string s)
        {
            return s.IsName() && s.IsOccupation();
        }

        private static bool IsRelativeType(this string s)
        {
            return (s.Contains("члены семьи") || s.Contains("степень родства")) && !s.IsName();
        }

        private static bool IsOccupation(this string s)
        {
            string clean = s.Replace("-", "").Replace(" ", "").ToLower();
            return (clean.Contains("должность") ||
                    clean.Contains("должности") ||
                    clean.Contains("должностей"));
        }

        private static bool IsDepartment(this string s)
        {
            return (s.Contains("наименование организации"));
        }

        private static bool IsMixedRealEstateOwnershipType(this string s)
        {
            return (s.Contains("праве собственности") &&
                    s.Contains("пользовании") &&
                    HasOwnershipTypeString(s));
        }

        private static bool HasRealEstateTypeStr(this string s)
        {
            return (s.Contains("вид объекта") ||
             s.Contains("вид объектов") ||
             s.Contains("вид обьекта") ||
             s.Contains("виды объектов") ||
             s.Contains("виды недвижимости") ||
             s.Contains("вид и наименование имущества") ||
             s.Contains("вид недвижимости"));
        }

        private static bool HasOwnershipTypeString(this string s)
        {
            string clean = s.Replace("-", "").Replace(" ", "");
            return clean.Contains("видсобственности")
                || clean.Contains("видсобственкостн")
                || clean.Contains("видсобствеивостн");
        }
        private static bool HasStateString(this string s)
        {
            string clean = s.Replace("-", "").Replace(" ", "");
            return clean.Contains("пользовании");
        }
        private static bool HasOwnedString(this string s)
        {
            string clean = s.Replace("-", "").Replace(" ", "");
            return clean.Contains("собственности");
        }

        private static bool HasSquareString(this string s)
        {
            string clean = s.Replace("-", "").Replace(" ", "");
            return clean.Contains("площадь");
        }

        private static bool HasCountryString(this string s)
        {
            string clean = s.Replace("-", "").Replace(" ", "");
            return clean.Contains("страна") || clean.Contains("регион");
        }
        
        public static bool IsStateColumn(this string s)
        {
            return    !HasOwnedString(s)
                    && HasStateString(s);
        }

        public static bool IsOwnedColumn(this string s)
        {
            return       HasOwnedString(s)
                    &&  !HasStateString(s);
        }

        public static bool IsMixedColumn(this string s)
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
            return IsOwnedColumn(s) && HasOwnershipTypeString(s);
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
            return (IsStateColumn(s) && HasRealEstateTypeStr(s)) || s.Equals("Объекты недвижимости, находящиеся в вид объекта");
        }
        private static bool IsStatePropertyOwnershipType(this string s)
        {
            return HasStateString(s) && HasOwnershipTypeString(s);
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

        private static bool HasMainDeclarant(this string s)
        {
            return (s.Contains("служащего") || s.Contains("служащему"))
                && !HasChild(s) && !HasSpouse(s);
        }
        private static bool HasChild(this string s)
        {
            return s.Contains("детей") || s.Contains("детям");
        }
        private static bool HasSpouse(this string s)
        {
            return s.Contains("супруг");
        }
        private static bool IsMixedRealEstateDeclarant(this string s)
        {
            return IsMixedColumn(s) && HasRealEstateStr(s) && HasMainDeclarant(s) && !HasSpouse(s); 
        }
        private static bool IsMixedRealEstateChild(this string s)
        {
            return IsMixedColumn(s) && HasRealEstateStr(s) && HasChild(s) && !HasSpouse(s);
        }

        private static bool IsMixedRealEstateSpouse(this string s)
        {
            return IsMixedColumn(s) && HasRealEstateStr(s) && HasSpouse(s) && !HasChild(s);
        }

        private static bool IsMixedRealEstate(this string s)
        {
            // в этой колонке нет подколонок, все записано на естественном языке
            return IsMixedColumn(s) && HasRealEstateStr(s);
        }

        private static bool IsStateRealEstate(this string s)
        {
            // в этой колонке нет подколонок, все записано на естественном языке
            return IsStateColumn(s) && HasRealEstateStr(s);
        }
        private static bool IsOwnedRealEstate(this string s)
        {
            // в этой колонке нет подколонок, все записано на естественном языке
            return IsOwnedColumn(s) && HasRealEstateStr(s);
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
            string clean = s.Replace(" ", "").Replace("-", "").Replace("\n", "");
            return ((clean.Contains("транспорт") || clean.Contains("трнспорт") || clean.Contains("движимоеимущество")) &&
                    (!clean.Contains("источник")));
        }

        private static bool IsVehicleType(this string s)
        {
            string clean = s.Replace(" ", "").Replace("-", "").Replace("\n", "");
            return ((clean.Contains("транспорт") || clean.Contains("трнспорт") || clean.Contains("движимоеимущество")) &&
                    ((clean.Contains("вид") && !clean.Contains("марк"))));
        }

        private static bool IsVehicleModel(this string s)
        {
            string clean = s.Replace(" ", "").Replace("-", "").Replace("\n", "");
            return ((clean.Contains("транспорт") || clean.Contains("трнспорт") || clean.Contains("движимоеимущество")) &&
                    ((clean.Contains("марка") && !clean.Contains("вид"))));
        }

        private static bool IsDeclaredYearlyIncome(this string str)
        {
            string strLower = str.Replace(" ", "").Replace("-", "").Replace("\n", "");
            return (strLower.Contains("годовойдоход")
                    || strLower.StartsWith("сведенияодоходеза")
                    || strLower.Contains("годовогодохода")
                    || strLower.Contains("суммадохода") 
                    || strLower.Contains("декларированныйдоход")
                    || strLower.Contains("декларированногодохода")
                    || strLower.Contains("общаясуммадохода")
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

        private static bool IsComments(this string s)
        {
            string lowerS = s.ToLower().Replace(" ", "").Replace("-", "");
            return lowerS.Contains("примечани");
        }

        private static bool IsAcquiredProperty(this string s)
        {
            string strLower = s.Replace(" ", "").Replace("-", "");
            return strLower.Contains("приобретенногоимущества");
        }
        
        private static bool IsMoneySources(this string s)
        {
            string strLower = s.Replace(" ", "").Replace("-", "");
            return strLower.Contains("источникполучениясредств") || strLower.Contains("сточникиполучениясредств");
        }

        private static bool IsTransactionSubject(this string s)
        {
            string strLower = s.Replace(" ", "").Replace("-", "").ToLower();
            return strLower.Contains("предметсделки");
        }
        
    }
}
