using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Smart.Parser.Lib.Adapters.Exceptions
{
    public class AsposeCorruptedFileException : Exception
    {
        public AsposeCorruptedFileException(string message) : base(message)
        {
        }
    }
}
