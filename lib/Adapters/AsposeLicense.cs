using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Smart.Parser.Adapters
{
    public class AsposeLicense
    {
        public static void SetLicense(string file)
        {
            Aspose.Cells.License cell_license = new Aspose.Cells.License();
            Aspose.Words.License word_license = new Aspose.Words.License();
            cell_license.SetLicense(file);
            word_license.SetLicense(file);
            Licensed = true;
        }
        public static bool Licensed { set; get; } = false;
    }
}
