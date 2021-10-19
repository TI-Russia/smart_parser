using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace SmartParser.Lib
{
    public class SmartParserExceptionBase : Exception
    {
        public SmartParserExceptionBase(string message) : base(message) { }
    }
    public class SmartParserException : SmartParserExceptionBase
    {
        public SmartParserException(string message) : base(message) { }
    }
    public class SmartParserFieldNotFoundException : SmartParserExceptionBase
    {
        public SmartParserFieldNotFoundException(string message) : base(message) { }
    }
    public class SmartParserRelativeWithoutPersonException : SmartParserExceptionBase
    {
        public SmartParserRelativeWithoutPersonException(string message) : base(message) { }
    }

}
