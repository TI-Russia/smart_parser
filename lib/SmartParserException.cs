using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Parser.Lib
{
    public class SmartParserException : Exception
    {
        public SmartParserException(string message) : base(message) { }
    }
    public class SmartParserFieldNotFoundException : Exception
    {
        public SmartParserFieldNotFoundException(string message) : base(message) { }
    }
    public class SmartParserRelativeWithoutPersonException : Exception
    {
        public SmartParserRelativeWithoutPersonException(string message) : base(message) { }
    }

}
