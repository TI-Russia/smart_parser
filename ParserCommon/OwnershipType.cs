using System;

/*
https://declarator.org/api/own-type/

"В собственности",  + Ownership
"В пользовании",  +  InUse
"Безвозмездное пользование",  + InFreeUse
"Наём (аренда)",  + Lease
"Служебное жилье",  + ServiceHousing
"Фактическое предоставление", + ProvisionForUse
"Индивидуальная",   Individual
"Долевая собственность",  Shared
"Совместная собственность"  Joint
 */


namespace TI.Declarator.ParserCommon
{
    public enum OwnershipType
    {
        None = -1, 
        NotAnOwner = 0, // To Be Deleted
        Individual = 1, // "Индивидуальная"
        //Coop = 2,
        Joint = 2, // "Совместная собственность" 
        Shared = 3, // "Долевая собственность"
        InUse, // "В пользовании"
        Lease, // "Наём (аренда)"
        ServiceHousing, // "Служебное жилье"
        ProvisionForUse,  // "Фактическое предоставление"
        Ownership, // В собственности
        InFreeUse // "Безвозмездное пользование"
    }

    public static class OwnershipTypeMethods
    {
        public static bool IsOwner(this OwnershipType t)
        {
            switch (t)
            {
                case OwnershipType.Ownership:
                case OwnershipType.Individual:
                case OwnershipType.Joint:
                case OwnershipType.Shared:
                    return true;
                default:
                    return false;
            }
        }
        public static bool NotAnOwner(this OwnershipType t)
        {
            switch (t)
            {
                case OwnershipType.InUse:
                case OwnershipType.Lease:
                case OwnershipType.ServiceHousing:
                case OwnershipType.ProvisionForUse:
                    return true;
                default:
                    return false;
            }
        }
        public static string ToJsonString(this OwnershipType t)
        {
            switch (t)
            {
                case OwnershipType.Individual: return "Индивидуальная";
                case OwnershipType.Joint:  return "Совместная собственность";
                case OwnershipType.Shared: return "Долевая собственность";
                case OwnershipType.InUse:  return "В пользовании";
                case OwnershipType.Lease:  return "Наём (аренда)";
                case OwnershipType.ServiceHousing: return "Служебное жилье";
                case OwnershipType.ProvisionForUse: return "Фактическое предоставление";
                case OwnershipType.Ownership: return "В собственности";
                case OwnershipType.InFreeUse: return "Безвозмездное пользование";
                default:
                    throw new ArgumentOutOfRangeException("");

            }
    }
    }
}


