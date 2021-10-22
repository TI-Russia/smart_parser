using StringHelpers;
using static SmartParser.Lib.DeclarationField;

using System;
using System.Text.RegularExpressions;

namespace SmartParser.Lib
{
    public static class HeaderHelpers
    {
        public static bool HasRealEstateStr(string str) => str
            .ToLowerInvariant()
            .RemoveCharacters('-', ' ')
            .ContainsAny("недвижим");
        public static bool IsNameDeclarationField(DeclarationField f)
        {
            return f == NameAndOccupationOrRelativeType || f == NameOrRelativeType;
        }

        public static DeclarationField TryGetField(string parentColumnTitle, string subColumnTitle)
        {
            string str;
            if (parentColumnTitle != null)
            {
                str = parentColumnTitle + " " + subColumnTitle;
            }
            else
            {
                parentColumnTitle = "";
                str = subColumnTitle;
            }
            str = NormalizeString(str);
            return str switch
            {
                _ when str.IsNumber() => Number,
                _ when IsIncomeYear(str) => IncomeYear,
                _ when IsNameAndOccupation(str) => NameAndOccupationOrRelativeType,
                _ when IsOccupationAndRelative(str) => OccupationOrRelativeType,
                _ when str.IsName() => NameOrRelativeType,
                _ when IsRelativeType(str) => RelativeTypeStrict,
                _ when IsOccupation(str) => Occupation,
                _ when str.IsDepartment() && !str.IsDeclaredYearlyIncome() => Department,

                _ when str.IsSpendingsField() => Spendings,

                _ when IsMixedRealEstateType(parentColumnTitle, subColumnTitle) => MixedRealEstateType,
                _ when str.IsMixedRealEstateSquare() && !str.IsMixedRealEstateCountry() => MixedRealEstateSquare,
                _ when str.IsMixedRealEstateCountry() && !str.IsMixedRealEstateSquare() => MixedRealEstateCountry,
                _ when str.IsMixedRealEstateOwnershipType() && !str.IsMixedRealEstateSquare() => MixedRealEstateOwnershipType,
                _ when str.IsMixedLandAreaSquare() => MixedLandAreaSquare,
                _ when str.IsMixedLivingHouseSquare() => MixedLivingHouseSquare,
                _ when str.IsMixedAppartmentSquare() => MixedAppartmentSquare,
                _ when str.IsMixedSummerHouseSquare() => MixedSummerHouseSquare,
                _ when str.IsMixedGarageSquare() => MixedGarageSquare,

                _ when IsOwnedRealEstateType(parentColumnTitle, subColumnTitle) => OwnedRealEstateType,
                _ when IsOwnedRealEstateOwnershipType(parentColumnTitle, subColumnTitle) => OwnedRealEstateOwnershipType,
                _ when IsOwnedRealEstateSquare(parentColumnTitle, subColumnTitle) => OwnedRealEstateSquare,
                _ when str.IsOwnedRealEstateCountry() => OwnedRealEstateCountry,

                _ when str.IsStatePropertyType() => StatePropertyType,
                _ when str.IsStatePropertySquare() => StatePropertySquare,
                _ when str.IsStatePropertyCountry() => StatePropertyCountry,
                _ when str.IsStatePropertyOwnershipType() => StatePropertyOwnershipType,

                _ when str.HasChild() && str.IsVehicle() && !(str.HasMainDeclarant() || str.HasSpouse()) => ChildVehicle,

                _ when str.HasSpouse() && str.IsVehicle() && !(str.HasMainDeclarant() || str.HasChild()) => SpouseVehicle,

                _ when str.HasMainDeclarant() && str.IsVehicle() => DeclarantVehicle,

                _ when IsVehicleType(parentColumnTitle, subColumnTitle) => VehicleType,
                _ when str.IsVehicleYear() => VehicleYear,

                _ when IsVehicleModel(parentColumnTitle, subColumnTitle) => VehicleModel,
                _ when subColumnTitle.IsVehicle() => DeclarationField.Vehicle,

                _ when str.IsDeclaredYearlyIncomeThousands() => str switch
                {
                    _ when str.HasChild() => ChildIncomeInThousands,
                    _ when str.HasSpouse() => SpouseIncomeInThousands,
                    _ when str.HasMainDeclarant() => DeclarantIncomeInThousands,
                    _ => DeclaredYearlyIncomeThousands,
                },

                _ when str.IsDeclaredYearlyIncome() => str switch
                {
                    _ when str.HasChild() && !(str.HasMainDeclarant() || str.HasSpouse()) => ChildIncome,
                    _ when str.HasSpouse() && !(str.HasMainDeclarant() || str.HasChild()) => SpouseIncome,
                    _ when str.HasMainDeclarant() => DeclarantIncome,
                    _ when HasOtherWord(str) => DeclaredYearlyOtherIncome,
                    _ => DeclaredYearlyIncome,
                },

                _ when str.IsMainWorkPositionIncome() => MainWorkPositionIncome,
                _ when str.IsDataSources() => DataSources,
                _ when str.IsComments() => Comments,

                _ when str.IsMixedRealEstateDeclarant() => DeclarantMixedColumnWithNaturalText,
                _ when str.IsMixedRealEstateSpouse() => SpouseMixedColumnWithNaturalText,
                _ when str.IsMixedRealEstateChild() => ChildMixedColumnWithNaturalText,

                _ when str.IsMixedRealEstate() => MixedColumnWithNaturalText,
                _ when str.IsOwnedRealEstate() => OwnedColumnWithNaturalText,
                _ when str.IsStateRealEstate() => StateColumnWithNaturalText,
                _ when HasCountryString(str) && HasRealEstateStr(str) => MixedRealEstateCountry,
                _ when HasRealEstateStr(str) => MixedColumnWithNaturalText,

                _ when str.IsAcquiredProperty() => AcquiredProperty,
                _ when str.IsTransactionSubject() => TransactionSubject,
                _ when str.IsMoneySources() => MoneySources,
                _ when str.IsMoneyOnBankAccounts() => MoneyOnBankAccounts,
                _ when str.IsSecuritiesField() => Securities,
                _ when str.IsStocksField() => Stocks,

                _ when str.HasSquareString() => MixedRealEstateSquare,
                _ when str.HasCountryString() => MixedRealEstateCountry,

                _ => None,
            };
        }

        private static string NormalizeString(string str) =>
            string.Join(" ", str.ToLowerInvariant().Split(new char[] { ' ', '\n', '\t' }, StringSplitOptions.RemoveEmptyEntries))
            .RemoveStupidTranslit();

        public static bool IsNumber(this string str)
        {
            str = str.RemoveCharacters(' ');
            return str.StartsWith("№")
                   || str.ContainsAny("nп/п", "№п/п", "nпп")
                   || str.Replace("\\", "/").Equals("п/п", StringComparison.OrdinalIgnoreCase);
        }

        public static bool IsIncomeYear(string str)
        {
            str = str.OnlyRussianLowercase();
            return str.ContainsAny("отчетныйгод") && !str.IsDeclaredYearlyIncome();
                   ;
        }

        public static bool IsName(this string s)
        {
            var clean = s.RemoveCharacters(',', '-', '\n', ' ').ToLowerInvariant();
            return clean.StartsWithAny("лицаодоходах", "подающиесведения", "подающийсведения")
                    || clean.ContainsAny(
                        "фамилия", 
                        "фамилимя", 
                        "фио", 
                        ".иф.о.", 
                        "сведенияодепутате",
                        "сведенияолице",
                        "ф.и.о");
        }

        public static bool IsNameAndOccupation(string s)
        {
            return (s.IsName() && IsOccupation(s))
            || s.OnlyRussianLowercase().Contains("замещаемаядолжностьстепеньродства");
        }
        private static bool IsRelativeType(string s)
        {
            return s.ContainsAny("члены семьи", "степень родства") && !s.IsName();
        }

        public static bool IsOccupation(string s) 
        {
            return s.RemoveCharacters('-', ' ').ToLowerInvariant()
            .ContainsAny("должность", "должности", "должностей");
        }
        public static bool IsOccupationAndRelative(string s)
        {
            return IsOccupation(s) && IsRelativeType(s);
        }

        private static bool IsDepartment(this string s) => s.ContainsAny("наименование организации", "ерриториальное управление в субъекте");

        private static bool IsMixedRealEstateOwnershipType(this string s) => s.IsMixedColumn() && HasOwnershipTypeString(s);

        private static bool HasRealEstateTypeStr(this string s) => s
            .OnlyRussianLowercase()
            .ContainsAny("видобъекта", "видобъектов", "видобьекта", "видимущества", "видыобъектов", "видынедвижимости", "видинаименованиеимущества", "виднедвижимости");

        private static bool HasOwnershipTypeString(this string s)
        {
            var clean = s.OnlyRussianLowercase();
            return Regex.Match(clean, "вид((собстве..ост)|(правана))").Success;
        }

        public static bool HasStateString(string s)
        {
            return s.OnlyRussianLowercase().Contains("пользовани");
        }

        public static bool HasOwnedString(string s)
        {
            return s.OnlyRussianLowercase().ContainsAny("собственности", "принадлежащие");
        }

        private static bool HasSquareString(this string s) => s.OnlyRussianLowercase().Contains("площадь");

        private static bool HasCountryString(this string s) => s.OnlyRussianLowercase().ContainsAny("страна", "регион");

        public static bool IsStateColumn(this string s) => !HasOwnedString(s) && HasStateString(s);

        public static bool IsOwnedColumn(this string s) => HasOwnedString(s) && !HasStateString(s);

        public static bool IsMixedColumn(this string s) => HasOwnedString(s) && HasStateString(s);

        private static bool IsOwnedRealEstateType(string parentColumnTitle, string subTitle) {
            if (subTitle.Length > 0 && (subTitle.HasSquareString() || subTitle.HasCountryString()))
            {
                // 4479_27.doc 
                return false;
            }
            var s = parentColumnTitle + " " + subTitle;
            if (s.IsOwnedColumn() && HasRealEstateTypeStr(s))
            {
                return true;
            }
            if (parentColumnTitle.IsOwnedColumn() && HasRealEstateStr(parentColumnTitle) 
                && subTitle.ToLower().StartsWith("вид") && !HasOwnershipTypeString(subTitle))
            {
                return true;
            }
            return false;
        }

        private static bool IsOwnedRealEstateOwnershipType(string parentColumnTitle, string subTitle) {
            if (subTitle.Length > 0 && (subTitle.HasSquareString() || subTitle.HasCountryString()))
            {
                // 4479_27.doc 
                return false;
            }
            var s = parentColumnTitle + " " + subTitle;
            return IsOwnedColumn(s) && HasOwnershipTypeString(s);
        }

        private static bool IsOwnedRealEstateSquare(string parentColumnTitle, string subTitle) {
            var s = parentColumnTitle + " " + subTitle;
            if (IsOwnedColumn(s) && HasRealEstateStr(s) && HasSquareString(s) && !s.Contains("вид"))
            {
                return true;
            }
            if (IsOwnedColumn(parentColumnTitle) && HasRealEstateStr(s)  && HasSquareString(subTitle))
            {
                return true;
            }
            return false;
        }

        private static bool IsOwnedRealEstateCountry(this string s)
        {
            return HasRealEstateStr(s) && IsOwnedColumn(s) && HasCountryString(s);
        }

        private static bool IsStatePropertyType(this string s) => (IsStateColumn(s) && HasRealEstateTypeStr(s)) || s.Equals("Объекты недвижимости, находящиеся в вид объекта");

        private static bool IsStatePropertyOwnershipType(this string s) => HasStateString(s) && HasOwnershipTypeString(s);

        private static bool IsStatePropertySquare(this string s) => IsStateColumn(s) && HasSquareString(s) && !s.Contains("вид");

        private static bool IsStatePropertyCountry(this string s) => IsStateColumn(s) && HasCountryString(s);

        private static bool IsMixedRealEstateType(string parentColumnTitle, string subTitle)
        {
            var s = parentColumnTitle + " " + subTitle;
            if (s.IsMixedColumn() && HasRealEstateTypeStr(s))
            {
                return true;
            }
            if (parentColumnTitle.IsMixedColumn() && HasRealEstateStr(parentColumnTitle)
                && subTitle.ToLower().StartsWith("вид") && !HasOwnershipTypeString(subTitle))
            {
                return true;
            }
            return false;
        }

        private static bool HasMainDeclarant(this string s)
        {
            s = s.OnlyRussianLowercase();
            return s.ContainsAny("служащего", "служащему", "должностлицо", "должнослицо", "должностноелицо") && !HasChild(s) && !HasSpouse(s);
        }
        private static bool HasOtherWord(string s)
        {
            return s.ContainsAny("иные", "иного");
        }

        private static bool HasChild(this string s) => s.ContainsAny("детей", "детям", "дети");

        private static bool HasSpouse(this string s) => s.Contains("супруг");

        private static bool HasMixedRealEstateOrRealEstateWithoutOwnership(string s)
        {
            return HasRealEstateStr(s) && 
                (IsMixedColumn(s) || (!HasOwnedString(s) && !HasStateString(s)));
        }
        private static bool IsMixedRealEstateDeclarant(this string s)
        {
            return HasMixedRealEstateOrRealEstateWithoutOwnership(s) && HasMainDeclarant(s) && !HasSpouse(s);
        }

        private static bool IsMixedRealEstateChild(this string s)
        {
            return HasMixedRealEstateOrRealEstateWithoutOwnership(s) && HasChild(s) && !HasSpouse(s);
        }

        private static bool IsMixedRealEstateSpouse(this string s)
        {
            return HasMixedRealEstateOrRealEstateWithoutOwnership(s) && HasSpouse(s) && !HasChild(s);
        }

        // в этой колонке нет подколонок, все записано на естественном языке
        private static bool IsMixedRealEstate(this string s) => IsMixedColumn(s) && HasRealEstateStr(s);

        // в этой колонке нет подколонок, все записано на естественном языке
        private static bool IsStateRealEstate(this string s) => IsStateColumn(s) && HasRealEstateStr(s);

        // в этой колонке нет подколонок, все записано на естественном языке
        private static bool IsOwnedRealEstate(this string s) => IsOwnedColumn(s) && HasRealEstateStr(s);

        private static bool IsMixedRealEstateSquare(this string s) => IsMixedColumn(s) && HasSquareString(s);

        private static bool IsMixedRealEstateCountry(this string s) => IsMixedColumn(s) && HasCountryString(s);

        private static bool IsVehicle(this string s)
        {
            var clean = s.OnlyRussianLowercase();
            return clean.ContainsAny("транспорт", "трнспорт", "движимоеимущество")
                && !clean.ContainsAny("источник") && !HasRealEstateStr(clean);
        }

        private static bool IsVehicleYear(this string s)
        {
            var clean = s.OnlyRussianLowercase();
            return clean.ContainsAny("годвыпуска");
        }

        private static bool CheckVehicleString(string s)
        {
            var clean = s.OnlyRussianLowercase();
            return clean.ContainsAny("транспорт", "трнспорт", "движимоеимущество");
        }

        private static bool CheckVehicleModel(string s)
        {
            var clean = s.OnlyRussianLowercase();
            return clean.ContainsAny("марка", "марки");
        }

        private static bool CheckVehicleType(string s)
        {
            var clean = s.OnlyRussianLowercase();
            return clean.ContainsAny("вид");
        }

        private static bool IsVehicleType(string parentColumnTitle, string subTitle)
        {
            var s = parentColumnTitle + " " + subTitle;
            if (CheckVehicleString(s) && CheckVehicleType(s) && !CheckVehicleModel(s))
            {
                return true;
            }
            if (CheckVehicleString(parentColumnTitle) && CheckVehicleType(subTitle) && !CheckVehicleModel(subTitle))
            {
                return true;
            }
            return false;
        }

        private static bool IsVehicleModel(string parentColumnTitle, string subTitle)
        {
            var s = parentColumnTitle + " " + subTitle;
            return (CheckVehicleString(s) && !CheckVehicleType(s) && CheckVehicleModel(s))
                || (CheckVehicleString(parentColumnTitle) && !CheckVehicleType(subTitle) && CheckVehicleModel(subTitle));
        }

        public static bool IsDeclaredYearlyIncome(this string str)
        {
            var strLower = str.OnlyRussianLowercase();
            return strLower.ContainsAny("годовойдоход", "годовогодохода", "суммадохода", "суммадоходов", 
                "декларированныйдоход", "декларированныйгодовой", "декларированногодохода", 
                "декларированногогодовогодоход", "общаясуммадохода", "общаясуммаза" )
                || strLower.StartsWithAny("сведенияодоходеза", "доход");
        }

        private static bool IsMainWorkPositionIncome(this string str) => Regex.Match(str, @"сумма.*месту\s+работы").Success;

        private static bool IsDeclaredYearlyIncomeThousands(this string s) => s.IsDeclaredYearlyIncome() && s.Contains("тыс.");

        private static bool IsDataSources(this string s) {
            var s1 = s.OnlyRussianLowercase();
            return s1.Contains("сведен") || s1.Contains("источниках");
        }

        private static bool IsComments(this string s) => s.OnlyRussianLowercase().Contains("примечани");

        private static bool IsAcquiredProperty(this string s) => s.OnlyRussianLowercase().Contains("приобретенногоимущества");

        private static bool IsMoneySources(this string s) => s.OnlyRussianLowercase().ContainsAny("источникполучениясредств", "сточникиполучениясредств");

        private static bool IsTransactionSubject(this string s) => s.OnlyRussianLowercase().Contains("предметсделки");

        private static bool IsMoneyOnBankAccounts(this string s)
        {
            var strLower = s.OnlyRussianLowercase();
            return strLower.Contains("денежныесредства") && strLower.ContainsAny("банках", "вкладах");
        }

        private static bool IsSecuritiesField(this string s) => s.OnlyRussianLowercase().Contains("ценныебумаги");

        private static bool IsSpendingsField(this string s)
        {
            var strLower = s.OnlyRussianLowercase();
            return strLower.Contains("расход") && !strLower.Contains("доход");
        }

        private static bool IsStocksField(this string s) => s.OnlyRussianLowercase().ContainsAll("участие", "организациях");

        private static bool IsMixedLandAreaSquare(this string s) => s.OnlyRussianLowercase().ContainsAll("земельныеучастки", "квм");

        private static bool IsMixedLivingHouseSquare(this string s) => s.OnlyRussianLowercase().ContainsAll("жилыедома", "квм");

        private static bool IsMixedAppartmentSquare(this string s) => s.OnlyRussianLowercase().ContainsAll("квартиры", "квм");

        private static bool IsMixedSummerHouseSquare(this string s) => s.OnlyRussianLowercase().ContainsAll("дачи", "квм");

        private static bool IsMixedGarageSquare(this string s) => s.OnlyRussianLowercase().ContainsAll("гаражи", "квм");
    }
}
