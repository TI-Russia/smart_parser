
using System.IO;

internal class TestUtil
{

    public static string GetTestDataPath()
    {
        return Path.GetFullPath(@"..\..\..\testdata\".Replace('\\', Path.DirectorySeparatorChar));
    }

}