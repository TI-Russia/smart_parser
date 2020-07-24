using System;
using System.Linq;
using System.Text.RegularExpressions;

namespace TI.Declarator.ParserCommon
{
    public static class HeaderHelpers
    {
        public static bool HasRealEstateStr(string str)
        {
            string strLower = str.ToLower().Replace("-", "");
            return strLower.Contains("недвижимости")
                || strLower.Contains("недвижимого")
                || strLower.Replace(" ", "").ToLower().Contains("иноенедвижимоеимущество(кв.м)");
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
            if (str.IsDepartment() && !str.IsDeclaredYearlyIncome()) { return DeclarationField.Department; }
            
            if (str.IsSpendingsField()) { return DeclarationField.Spendings; }

            if (str.IsMixedRealEstateType()) { return DeclarationField.MixedRealEstateType; }
            if (str.IsMixedRealEstateSquare() && !str.IsMixedRealEstateCountry()) { return DeclarationField.MixedRealEstateSquare; }
            if (str.IsMixedRealEstateCountry() && !str.IsMixedRealEstateSquare() ) { return DeclarationField.MixedRealEstateCountry; }
            if (str.IsMixedRealEstateOwnershipType() && !str.IsMixedRealEstateSquare()) { return DeclarationField.MixedRealEstateOwnershipType; }
            if (str.IsMixedLandAreaSquare()) { return DeclarationField.MixedLandAreaSquare; }
            if (str.IsMixedLivingHouseSquare()) { return DeclarationField.MixedLivingHouseSquare; }
            if (str.IsMixedAppartmentSquare()) { return DeclarationField.MixedAppartmentSquare; }
            if (str.IsMixedSummerHouseSquare()) { return DeclarationField.MixedSummerHouseSquare; }
            if (str.IsMixedGarageSquare()) { return DeclarationField.MixedGarageSquare; }
            
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

            if (str.IsMainWorkPositionIncome())
            {
                return DeclarationField.MainWorkPositionIncome;
            }
                
            if (str.IsDataSources()) { return DeclarationField.DataSources; }
            if (str.IsComments()) { return DeclarationField.Comments; }

            if (str.IsMixedRealEstateDeclarant()) { return DeclarationField.DeclarantMixedColumnWithNaturalText; }
            if (str.IsMixedRealEstateSpouse()) { return DeclarationField.SpouseMixedColumnWithNaturalText; }
            if (str.IsMixedRealEstateChild()) { return DeclarationField.ChildMixedColumnWithNaturalText; }

            if (str.IsMixedRealEstate()) { return DeclarationField.MixedColumnWithNaturalText; }
            if (str.IsOwnedRealEstate()) { return DeclarationField.OwnedColumnWithNaturalText; }
            if (str.IsStateRealEstate()) { return DeclarationField.StateColumnWithNaturalText; }
            if (HasCountryString(str) && HasRealEstateStr(str)) { return DeclarationField.MixedRealEstateCountry; }
            if (HasRealEstateStr(str)) { return DeclarationField.MixedColumnWithNaturalText; }

            if (str.IsAcquiredProperty()) { return DeclarationField.AcquiredProperty; }
            if (str.IsTransactionSubject()) { return DeclarationField.TransactionSubject; }
            if (str.IsMoneySources()) { return DeclarationField.MoneySources; }
            if (str.IsMoneyOnBankAccounts()) { return DeclarationField.MoneyOnBankAccounts; }
            if (str.IsSecuritiesField()) { return DeclarationField.Securities; }
            if (str.IsStocksField()) { return DeclarationField.Stocks; }

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
                   str.ToLower().Contains("№п/п") || 
                   str.ToLower().Replace("\\", "/").Equals("п/п") || 
                   str.ToLower().Contains("nпп");
        }

        public static bool IsName(this string s)
        {
            string clean = s.Replace("-", "").Replace("\n", "").Replace(" ", "").ToLower();
            return (clean.Contains("фамилия") ||
                    clean.Contains("фамилимя") ||
                    clean.StartsWith("подающиесведения") ||
                    clean.StartsWith("подающийсведения") ||
                    clean.Contains("фио") ||
                    clean.Contains(".иф.о.") ||
                    clean.Contains("сведенияодепутате") ||
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
            return s.Contains("наименование организации") || s.Contains("ерриториальное управление в субъекте");
        }

        private static bool IsMixedRealEstateOwnershipType(this string s)
        {
            return s.IsMixedColumn() && HasOwnershipTypeString(s);
        }

        public static string OnlyRussianLowercase(this string s)
        {
            return Regex.Replace(s.ToLower(), "[^а-яё]", "");
        }

        private static bool HasRealEstateTypeStr(this string s)
        {
            string clean = s.OnlyRussianLowercase();
            return (clean.Contains("видобъекта") ||
                    clean.Contains("видобъектов") ||
                    clean.Contains("видобьекта") ||
                    clean.Contains("видыобъектов") ||
                    clean.Contains("видынедвижимости") ||
                    clean.Contains("видинаименование имущества") ||
                    clean.Contains("виднедвижимости"));
        }

        private static bool HasOwnershipTypeString(this string s)
        {
            string clean = s.OnlyRussianLowercase();
            return Regex.Match(clean, @"вид((собстве..ост)|(правана))").Success;
        }
        private static bool HasStateString(this string s)
        {
            string clean = s.OnlyRussianLowercase();
            return clean.Contains("пользовании");
        }
        private static bool HasOwnedString(this string s)
        {
            string clean = s.OnlyRussianLowercase();
            return clean.Contains("собственности");
        }

        private static bool HasSquareString(this string s)
        {
            string clean = s.OnlyRussianLowercase();
            return clean.Contains("площадь");
        }

        private static bool HasCountryString(this string s)
        {
            string clean = s.OnlyRussianLowercase();
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
            return IsOwnedColumn(s) &&  HasSquareString(s) && !s.Contains("вид");
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
            return IsStateColumn(s) && HasSquareString(s) && !s.Contains("вид");
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
            s = s.OnlyRussianLowercase();
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
            string clean = s.OnlyRussianLowercase();
            return ((clean.Contains("транспорт") || clean.Contains("трнспорт") || clean.Contains("движимоеимущество")) &&
                    !clean.Contains("источник") && !clean.Contains("недвижимоеимущество"));
        }

        private static bool IsVehicleType(this string s)
        {
            string clean = s.OnlyRussianLowercase();
            return ((clean.Contains("транспорт") || clean.Contains("трнспорт") || clean.Contains("движимоеимущество")) &&
                    ((clean.Contains("вид") && !clean.Contains("марк"))));
        }

        private static bool IsVehicleModel(this string s)
        {
            string clean = s.OnlyRussianLowercase();
            return ((clean.Contains("транспорт") || clean.Contains("трнспорт") || clean.Contains("движимоеимущество")) &&
                    ((clean.Contains("марка") && !clean.Contains("вид"))));
        }

        private static bool IsDeclaredYearlyIncome(this string str)
        {
            string strLower = str.OnlyRussianLowercase();
            return (strLower.Contains("годовойдоход")
                    || strLower.StartsWith("сведенияодоходеза")
                    || strLower.Contains("годовогодохода")
                    || strLower.Contains("суммадохода") 
                    || strLower.Contains("суммадоходов") 
                    || strLower.Contains("декларированныйдоход")
                    || strLower.Contains("декларированныйгодовой")
                    || strLower.Contains("декларированногодохода")
                    || strLower.Contains("декларированногогодовогодоход")
                    || strLower.Contains("общаясуммадохода")
                   );
        }

        private static bool IsMainWorkPositionIncome(this string str)
        {
            return Regex.Match(str, @"сумма.*месту\s+работы").Success;
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
            string lowerS = s.OnlyRussianLowercase();
            return lowerS.Contains("примечани");
        }

        private static bool IsAcquiredProperty(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("приобретенногоимущества");
        }
        
        private static bool IsMoneySources(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("источникполучениясредств") || strLower.Contains("сточникиполучениясредств");
        }

        private static bool IsTransactionSubject(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("предметсделки");
        }
        private static bool IsMoneyOnBankAccounts(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return (strLower.Contains("денежныесредства") && (
                strLower.Contains("банках") || strLower.Contains("вкладах")));
        }

        private static bool IsSecuritiesField(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("ценныебумаги");
        }
        
        private static bool IsSpendingsField(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("расход");
        }

        private static bool IsStocksField(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("участие") && strLower.Contains("организациях");
        }
        private static bool IsMixedLandAreaSquare(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("земельныеучастки") && strLower.Contains("квм");
        }
        private static bool IsMixedLivingHouseSquare(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("жилыедома") && strLower.Contains("квм");
        }
        private static bool IsMixedAppartmentSquare(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("квартиры") && strLower.Contains("квм");
        }
        private static bool IsMixedSummerHouseSquare(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("дачи") && strLower.Contains("квм");
        }
        private static bool IsMixedGarageSquare(this string s)
        {
            string strLower = s.OnlyRussianLowercase();
            return strLower.Contains("гаражи") && strLower.Contains("квм");
        }
    }
}
