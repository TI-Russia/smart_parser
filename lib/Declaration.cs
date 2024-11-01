﻿using System;
using System.Collections.Generic;

namespace SmartParser.Lib
{
    public class Declaration
    {
        public List<PublicServant> PublicServants { get; set; } = new List<PublicServant>();
        public DeclarationProperties Properties { get; set; }

        // used only if DeclarationSerializer.SmartParserJsonFormat==SmartParserJsonFormatEnum.Disclosures
        public List<DeclarationProperties> NotFirstSheetProperties = new List<DeclarationProperties>();
        
        
        public void AddDeclarations(Declaration notFirstSheet)
        {
            NotFirstSheetProperties.Add(notFirstSheet.Properties);
            PublicServants.AddRange(notFirstSheet.PublicServants);
        } 
    }

    public class DeclarationSection
    {
        public string Name { get; set; }
        public int Row { get; set; }
    }

}
