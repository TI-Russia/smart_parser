using System;
using System.Text.RegularExpressions;
using static TI.Declarator.ParserCommon.DeclarationField;

namespace TI.Declarator.ParserCommon
{
    public static class HeaderHelpers
    {
        public static bool HasRealEstateStr(string str) =>str
            .RemoveCharacters('-', ' ')
            .ContainsAny("недвижимости", "недвижимого", "иноенедвижимоеимущество(кв.м)");

        public static DeclarationField GetField(string str) => TryGetField(str) switch
        {
            None => throw new Exception($"Could not determine column type for header {str}."),
            DeclarationField value => value,
        };

        public static DeclarationField TryGetField(string str)
        { 
            str = NormalizeString(str);
            return str switch
            {
                _ when str.IsNumber()                                                           => Number,
                _ when str.IsNameAndOccupation()                                                => NameAndOccupationOrRelativeType,
                _ when str.IsName()                                                             => NameOrRelativeType,
                _ when str.IsRelativeType()                                                     => RelativeTypeStrict,
                _ when str.IsOccupation()                                                       => Occupation,
                _ when str.IsDepartment() && !str.IsDeclaredYearlyIncome()                      => Department,

                _ when str.IsSpendingsField()                                                   => Spendings,

                _ when str.IsMixedRealEstateType()                                              => MixedRealEstateType,
                _ when str.IsMixedRealEstateSquare() && !str.IsMixedRealEstateCountry()         => MixedRealEstateSquare,
                _ when str.IsMixedRealEstateCountry() && !str.IsMixedRealEstateSquare()         => MixedRealEstateCountry,
                _ when str.IsMixedRealEstateOwnershipType() && !str.IsMixedRealEstateSquare()   => MixedRealEstateOwnershipType,
                _ when str.IsMixedLandAreaSquare()                                              => MixedLandAreaSquare,
                _ when str.IsMixedLivingHouseSquare()                                           => MixedLivingHouseSquare,
                _ when str.IsMixedAppartmentSquare()                                            => MixedAppartmentSquare,
                _ when str.IsMixedSummerHouseSquare()                                           => MixedSummerHouseSquare,
                _ when str.IsMixedGarageSquare()                                                => MixedGarageSquare,

                _ when str.IsOwnedRealEstateType()                                              => OwnedRealEstateType,
                _ when str.IsOwnedRealEstateOwnershipType()                                     => OwnedRealEstateOwnershipType,
                _ when str.IsOwnedRealEstateSquare()                                            => OwnedRealEstateSquare,
                _ when str.IsOwnedRealEstateCountry()                                           => OwnedRealEstateCountry,

                _ when str.IsStatePropertyType()                                                => StatePropertyType,
                _ when str.IsStatePropertySquare()                                              => StatePropertySquare,
                _ when str.IsStatePropertyCountry()                                             => StatePropertyCountry,
                _ when str.IsStatePropertyOwnershipType()                                       => StatePropertyOwnershipType,

                _ when str.HasChild() && str.IsVehicle() && !(str.HasMainDeclarant() || str.HasSpouse()) => ChildVehicle,

                _ when str.HasSpouse() && str.IsVehicle() && !(str.HasMainDeclarant() || str.HasChild()) => SpouseVehicle,

                _ when str.HasMainDeclarant() && str.IsVehicle() => DeclarantVehicle,

                _ when str.IsVehicleType()                                                      => VehicleType,
                _ when str.IsVehicleModel()                                                     => VehicleModel,
                _ when str.IsVehicle()                                                          => DeclarationField.Vehicle,

                _ when str.IsDeclaredYearlyIncomeThousands() => str switch
                {
                    _ when str.HasChild()                                                       => ChildIncomeInThousands,
                    _ when str.HasSpouse()                                                      => SpouseIncomeInThousands,
                    _ when str.HasMainDeclarant()                                               => DeclarantIncomeInThousands,
                    _                                                                           => DeclaredYearlyIncomeThousands,
                },

                _ when str.IsDeclaredYearlyIncome() => str switch
                {
                    _ when str.HasChild() && !(str.HasMainDeclarant() || str.HasSpouse())       => ChildIncome,
                    _ when str.HasSpouse() && !(str.HasMainDeclarant() || str.HasChild())       => SpouseIncome,
                    _ when str.HasMainDeclarant()                                               => DeclarantIncome,
                    _                                                                           => DeclaredYearlyIncome,
                },

                _ when str.IsMainWorkPositionIncome()                                           => MainWorkPositionIncome,
                _ when str.IsDataSources()                                                      => DataSources,
                _ when str.IsComments()                                                         => Comments,

                _ when str.IsMixedRealEstateDeclarant()                                         => DeclarantMixedColumnWithNaturalText,
                _ when str.IsMixedRealEstateSpouse()                                            => SpouseMixedColumnWithNaturalText,
                _ when str.IsMixedRealEstateChild()                                             => ChildMixedColumnWithNaturalText,

                _ when str.IsMixedRealEstate()                                                  => MixedColumnWithNaturalText,
                _ when str.IsOwnedRealEstate()                                                  => OwnedColumnWithNaturalText,
                _ when str.IsStateRealEstate()                                                  => StateColumnWithNaturalText,
                _ when HasCountryString(str) && HasRealEstateStr(str)                           => MixedRealEstateCountry,
                _ when HasRealEstateStr(str)                                                    => MixedColumnWithNaturalText,

                _ when str.IsAcquiredProperty()                                                 => AcquiredProperty,
                _ when str.IsTransactionSubject()                                               => TransactionSubject,
                _ when str.IsMoneySources()                                                     => MoneySources,
                _ when str.IsMoneyOnBankAccounts()                                              => MoneyOnBankAccounts,
                _ when str.IsSecuritiesField()                                                  => Securities,
                _ when str.IsStocksField()                                                      => Stocks,

                _ when str.HasSquareString()                                                    => MixedRealEstateSquare,
                _ when str.HasCountryString()                                                   => MixedRealEstateCountry,

                _                                                                               => None,
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

        public static bool IsName(this string s)
        {
            var clean = s.RemoveCharacters(',', '-', '\n', ' ');
            return clean.StartsWithAny("лицаодоходах", "подающиесведения", "подающийсведения")
                    || clean.ContainsAny("фамилия", "фамилимя", "фио", ".иф.о.", "сведенияодепутате", "ф.и.о");
        }

        public static bool IsNameAndOccupation(this string s) =>
            (s.IsName() && s.IsOccupation())
            || s.OnlyRussianLowercase().Contains("замещаемаядолжностьстепеньродства");

        private static bool IsRelativeType(this string s) => s.ContainsAny("члены семьи", "степень родства") && !s.IsName();

        private static bool IsOccupation(this string s) => s
            .RemoveCharacters('-', ' ')
            .ContainsAny("должность", "должности", "должностей");

        private static bool IsDepartment(this string s) => s.ContainsAny("наименование организации", "ерриториальное управление в субъекте");

        private static bool IsMixedRealEstateOwnershipType(this string s) => s.IsMixedColumn() && HasOwnershipTypeString(s);

        public static string OnlyRussianLowercase(this string s) => Regex.Replace(s.ToLowerInvariant(), "[^а-яё]", string.Empty);

        private static bool HasRealEstateTypeStr(this string s) => s
            .OnlyRussianLowercase()
            .ContainsAny("видобъекта", "видобъектов", "видобьекта", "видимущества", "видыобъектов", "видынедвижимости", "видинаименованиеимущества", "виднедвижимости");

        private static bool HasOwnershipTypeString(this string s)
        {
            var clean = s.OnlyRussianLowercase();
            return Regex.Match(clean, "вид((собстве..ост)|(правана))").Success;
        }

        private static bool HasStateString(this string s) => s.OnlyRussianLowercase().Contains("пользовани");

        private static bool HasOwnedString(this string s) => s.OnlyRussianLowercase().ContainsAny("собственности", "принадлежащие");

        private static bool HasSquareString(this string s) => s.OnlyRussianLowercase().Contains("площадь");

        private static bool HasCountryString(this string s) => s.OnlyRussianLowercase().ContainsAny("страна", "регион");

        public static bool IsStateColumn(this string s) => !HasOwnedString(s) && HasStateString(s);

        public static bool IsOwnedColumn(this string s) => HasOwnedString(s) && !HasStateString(s);

        public static bool IsMixedColumn(this string s) => HasOwnedString(s) && HasStateString(s);

        private static bool IsOwnedRealEstateType(this string s) => IsOwnedColumn(s) && HasRealEstateTypeStr(s);

        private static bool IsOwnedRealEstateOwnershipType(this string s) => IsOwnedColumn(s) && HasOwnershipTypeString(s);

        private static bool IsOwnedRealEstateSquare(this string s) => IsOwnedColumn(s) && HasSquareString(s) && !s.Contains("вид");

        private static bool IsOwnedRealEstateCountry(this string s) => IsOwnedColumn(s) && HasCountryString(s);

        private static bool IsStatePropertyType(this string s) => (IsStateColumn(s) && HasRealEstateTypeStr(s)) || s.Equals("Объекты недвижимости, находящиеся в вид объекта");

        private static bool IsStatePropertyOwnershipType(this string s) => HasStateString(s) && HasOwnershipTypeString(s);

        private static bool IsStatePropertySquare(this string s) => IsStateColumn(s) && HasSquareString(s) && !s.Contains("вид");

        private static bool IsStatePropertyCountry(this string s) => IsStateColumn(s) && HasCountryString(s);

        private static bool IsMixedRealEstateType(this string s) => IsMixedColumn(s) && HasRealEstateTypeStr(s);

        private static bool HasMainDeclarant(this string s)
        {
            s = s.OnlyRussianLowercase();
            return s.ContainsAny("служащего", "служащему", "должностлицо", "должнослицо", "должностноелицо") && !HasChild(s) && !HasSpouse(s);
        }

        private static bool HasChild(this string s) => s.ContainsAny("детей", "детям");

        private static bool HasSpouse(this string s) => s.Contains("супруг");

        private static bool IsMixedRealEstateDeclarant(this string s) => IsMixedColumn(s) && HasRealEstateStr(s) && HasMainDeclarant(s) && !HasSpouse(s);

        private static bool IsMixedRealEstateChild(this string s) => IsMixedColumn(s) && HasRealEstateStr(s) && HasChild(s) && !HasSpouse(s);

        private static bool IsMixedRealEstateSpouse(this string s) => IsMixedColumn(s) && HasRealEstateStr(s) && HasSpouse(s) && !HasChild(s);

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
                && !clean.ContainsAny("источник", "недвижимоеимущество");
        }

        private static bool IsVehicleType(this string s)
        {
            var clean = s.OnlyRussianLowercase();
            return clean.ContainsAny("транспорт", "трнспорт", "движимоеимущество")
                && clean.Contains("вид") && !clean.Contains("марк");
        }

        private static bool IsVehicleModel(this string s)
        {
            var clean = s.OnlyRussianLowercase();
            return clean.ContainsAny("транспорт", "трнспорт", "движимоеимущество")
                && clean.Contains("марка") && !clean.Contains("вид");
        }

        private static bool IsDeclaredYearlyIncome(this string str)
        {
            var strLower = str.OnlyRussianLowercase();
            return strLower.ContainsAny("годовойдоход", "годовогодохода", "суммадохода", "суммадоходов", "декларированныйдоход", "декларированныйгодовой", "декларированногодохода", "декларированногогодовогодоход", "общаясуммадохода")
                || strLower.StartsWithAny("сведенияодоходеза", "доход");
        }

        private static bool IsMainWorkPositionIncome(this string str) => Regex.Match(str, @"сумма.*месту\s+работы").Success;

        private static bool IsDeclaredYearlyIncomeThousands(this string s) => s.IsDeclaredYearlyIncome() && s.Contains("тыс.");

        private static bool IsDataSources(this string s) => s.Contains("сведен");

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
