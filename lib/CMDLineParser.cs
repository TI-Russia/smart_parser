/* Lightweight C# Command line parser
 *
 * Author  : Christian Bolterauer
 * Date    : 8-Aug-2009
 * Version : 1.0
 * Changes : 
 * https://www.codeproject.com/Articles/39120/Lightweight-C-Command-Line-Parser
 */

using System;
using System.Collections;
using System.Globalization;
using System.Text;


/// <summary>
/// Command Line Parser. 
/// </summary>
/// <remarks>
///     supports:
///     - 'unlimited' number of alias names
///     - Options starting with '-' or '/' 
///     - String, Integer and Double parameter options
///     - option and parameter attached in one argument (e.g. -P=123 ) or as args pair (e.g. -P 123)
///     - handling differnt number decimal seperators
///     - provides usage message of available (registered) options
///</remarks>
/// 
namespace CMDLine
{
    /// <summary>
    /// Command Line Parser for creating and parsing command line options
    /// </summary>
    /// <remarks> Throws: MissingOptionException, DuplicateOptionException and if set InvalidOptionsException.
    /// </remarks>
    /// <seealso cref="Parse"/>
    /// <example> 
    ///   
    ///     //using CMDLine
    /// 
    ///     //create parser
    ///     CMDLineParser parser = new CMDLineParser();
    ///     
    ///     //add default help "-help",..
    ///     parser.AddHelpOption();
    ///      
    ///     //add Option to parse
    ///     CMDLineParser.Option DebugOption = parser.AddBoolSwitch("-Debug", "Print Debug information");
    ///     
    ///     //add Alias option name
    ///     DebugOption.AddAlias("/Debug");
    /// 
    ///     CMDLineParser.NumberOption NegNumOpt = parser.AddDoubleParameter("-NegNum", "A required negativ Number", true);
    ///     
    ///     try
    ///     {
    ///         //parse 
    ///         parser.Parse(args);
    ///     }
    ///     catch (CMDLineParser.CMDLineParserException e)
    ///     {
    ///         Console.WriteLine("Error: " + e.Message);
    ///         parser.HelpMessage();
    ///     }
    ///     parser.Debug();    
    ///    
    ///</example>
    public class CMDLineParser
    {
        private string[] _cmdlineArgs = null;
        private System.Collections.ArrayList SwitchesStore = null;
        private ArrayList _matchedSwitches = null;
        private ArrayList _unmatchedArgs = null;
        private ArrayList _invalidArgs = null;

        private CMDLineParser.Option _help = null;

        /// <summary>
        ///collect not matched (invalid) command line options as invalid args
        /// </summary>
        public bool collectInvalidOptions = true;
        /// <summary>
        ///throw an exception if not matched (invalid) command line options were detected
        /// </summary>
        public bool throwInvalidOptionsException = false;

        public bool isConsoleApplication = true;

        /// <summary>
        /// create a Command Line Parser for creating and parsing command line options
        /// </summary>
        public CMDLineParser()
        { }
        /// <summary>
        /// Add a default help switch "-help","-h","-?","/help"
        /// </summary>
        public Option AddHelpOption()
        {
            _help = this.AddBoolSwitch("-help", "Command line help");
            _help.AddAlias("-h");
            _help.AddAlias("-?");
            _help.AddAlias("/help");
            return (_help);
        }
        /// <summary>
        /// Parses the command line and sets the values of each registered switch 
        /// or parameter option.
        /// </summary>
        /// <param name="args">The arguments array sent to Main(string[] args)</param>
        /// <returns>'true' if all parsed options are valid otherwise 'false'</returns>
        /// <exception cref="MissingOptionException"></exception>
        /// <exception cref="DuplicateOptionException"></exception>
        /// <exception cref="InvalidOptionsException"></exception>
        public bool Parse(string[] args)
        {
            this.Clear();
            _cmdlineArgs = args;
            ParseOptions();
            if (_invalidArgs.Count > 0)
            {
                if (throwInvalidOptionsException)
                {
                    string iopts = "";
                    foreach (string arg in _invalidArgs)
                    {
                        iopts += "'" + arg + "';";
                    }
                    throw new InvalidOptionsException("Invalid command line argument(s): " + iopts);
                }
                return false;
            }
            else
            {
                return true;
            }
        }
        /// <summary>
        /// Reset Parser and values of registed options.
        /// </summary>
        public void Clear()
        {
            _matchedSwitches = null;
            _unmatchedArgs = null;
            _invalidArgs = null;

            if (SwitchesStore != null)
            {
                foreach (Option s in SwitchesStore)
                {
                    s.Clear();
                }
            }
        }
        /// <summary>
        /// Add (a custom) Option (Optional)
        /// </summary>
        /// <remarks> 
        /// To add instances (or subclasses) of 'CMDLineParser.Option'
        /// that implement: 
        /// <code>'public override object parseValue(string parameter)'</code>
        /// </remarks>
        /// <param name="opt">subclass from 'CMDLineParser.Option'</param>
        /// <seealso cref="AddBoolSwitch"/>
        /// <seealso cref="AddStringParameter"/>
        public void AddOption(Option opt)
        {
            CheckCmdLineOption(opt.Name);
            if (SwitchesStore == null)
                SwitchesStore = new System.Collections.ArrayList();
            SwitchesStore.Add(opt);
        }
        /// <summary>
        /// Add a basic command line switch. 
        /// (exist = 'true' otherwise 'false').
        /// </summary>
        public Option AddBoolSwitch(string name, string description)
        {
            Option opt = new Option(name, description, typeof(bool), false, false);
            AddOption(opt);
            return (opt);
        }
        /// <summary>
        /// Add a string parameter command line option.
        /// </summary>
        public Option AddStringParameter(string name, string description, bool required)
        {
            Option opt = new Option(name, description, typeof(string), true, required);
            AddOption(opt);
            return (opt);
        }
        /// <summary>
        /// Add a Integer parameter command line option.
        /// </summary>
        public NumberOption AddIntParameter(string name, string description, bool required)
        {
            NumberOption opt = new NumberOption(name, description, typeof(int), true, required);
            opt.NumberStyle = NumberStyles.Integer;
            AddOption(opt);
            return (opt);
        }
        /// <summary>
        /// Add a Double parameter command line option.
        /// </summary>
        public NumberOption AddDoubleParameter(string name, string description, bool required)
        {
            NumberOption opt = new NumberOption(name, description, typeof(double), true, required);
            opt.NumberStyle = NumberStyles.Float;
            AddOption(opt);
            return (opt);
        }
        /// <summary>
        /// Add a Double parameter command line option.
        /// </summary>
        public NumberOption AddDoubleParameter(string name, string description, bool required, NumberFormatInfo numberformat)
        {
            NumberOption opt = new NumberOption(name, description, typeof(double), true, required);
            opt.NumberFormat = numberformat;
            opt.parseDecimalSeperator = false;
            opt.NumberStyle = NumberStyles.Float | NumberStyles.AllowThousands;
            AddOption(opt);
            return (opt);
        }
        /// <summary>
        /// Check if name is a valid Option name
        /// </summary>
        /// <param name="name"></param>
        /// <exception cref="CMDLineParseException"></exception>
        private void CheckCmdLineOption(string name)
        {
            if (!isASwitch(name))
                throw new CMDLineParserException("Invalid Option:'" + name + "'::" + IS_NOT_A_SWITCH_MSG);
        }
        //
        protected const string IS_NOT_A_SWITCH_MSG = "The Switch name does not start with an switch identifier '-' or '/'  or contains space!";
        protected static bool isASwitch(string arg)
        {
            return ((arg.StartsWith("-") || arg.StartsWith("/")) & (!arg.Contains(" ")));
        }

        private void ParseOptions()
        {
            _matchedSwitches = new ArrayList();
            _unmatchedArgs = new ArrayList();
            _invalidArgs = new ArrayList();

            if (_cmdlineArgs != null && SwitchesStore != null)
            {
                for (int idx = 0; idx < _cmdlineArgs.Length; idx++)
                {
                    string arg = _cmdlineArgs[idx];
                    bool found = false;
                    foreach (Option s in SwitchesStore)
                    {
                        if (compare(s, arg))
                        {
                            s.isMatched = found = true;
                            _matchedSwitches.Add(s);
                            idx = processMatchedSwitch(s, _cmdlineArgs, idx);
                        }
                    }
                    if (found == false) processUnmatchedArg(arg);
                }
                checkReqired();
            }
        }

        private void checkReqired()
        {
            foreach (Option s in SwitchesStore)
            {
                if (s.isRequired && (!s.isMatched))
                    throw new MissingRequiredOptionException("Missing Required Option:'" + s.Name + "'");
            }
        }

        private bool compare(Option s, string arg)
        {
            if (!s.needsValue)
            {
                foreach (string optname in s.Names)
                {
                    if (optname.Equals(arg))
                    {
                        s.Name = optname; //set name in case we match an alias name
                        return (true);
                    }
                }
                return false;
            }
            else
            {
                foreach (string optname in s.Names)
                {
                    if (arg.StartsWith(optname))
                    {
                        checkDuplicateAndSetName(s, optname);
                        return (true);
                    }
                }
                return false;
            }
        }

        private void checkDuplicateAndSetName(Option s, string optname)
        {
            if (s.isMatched && s.needsValue)
                throw new DuplicateOptionException("Duplicate: The Option:'" + optname + "' allready exists on the comand line as  +'" + s.Name + "'");
            else
            {
                s.Name = optname; //set name in case we match an alias name
            }
        }

        private int retrieveParameter(ref string parameter, string optname, string[] cmdlineArgs, int pos)
        {
            if (cmdlineArgs[pos].Length == optname.Length) // arg must be in next cmdlineArg
            {
                if (cmdlineArgs.Length > pos + 1)
                {
                    pos++; //change command line index to next cmdline Arg.
                    parameter = cmdlineArgs[pos];
                }
            }
            else
            {
                parameter = (cmdlineArgs[pos].Substring(optname.Length));
            }
            return pos;
        }

        protected int processMatchedSwitch(Option s, string[] cmdlineArgs, int pos)
        {
            //if help switch is matched give help .. only works for console apps
            if (s.Equals(_help))
            {
                if (isConsoleApplication)
                {
                    Console.Write(this.HelpMessage());
                }
            }
            //process bool switch
            if (s.Type == typeof(bool) && s.needsValue == false)
            {
                s.Value = true;
                return pos;
            }

            if (s.needsValue == true)
            {
                //retrieve parameter value and adjust pos
                string parameter = "";
                pos = retrieveParameter(ref parameter, s.Name, cmdlineArgs, pos);
                //parse option using 'IParsableOptionParameter.parseValue(parameter)'
                //and set parameter value
                try
                {
                    if (s.Type != null)
                    {
                        ((IParsableOptionParameter)s).Value = ((IParsableOptionParameter)s).parseValue(parameter);
                        return pos;
                    }
                }
                catch (Exception ex)
                {
                    throw new ParameterConversionException(ex.Message);
                }
            }
            //unsupported type ..
            throw new CMDLineParserException("Unsupported Parameter Type:" + s.Type);
        }

        protected void processUnmatchedArg(string arg)
        {
            if (collectInvalidOptions && isASwitch(arg)) //assuming an invalid comand line option
            {
                _invalidArgs.Add(arg); //collect first, throw Exception later if set..
            }
            else
            {
                _unmatchedArgs.Add(arg);
            }
        }
        /// <summary>
        /// String array of remaining arguments not identified as command line options
        /// </summary>
        public String[] RemainingArgs()
        {
            if (_unmatchedArgs == null) return null;
            return ((String[])_unmatchedArgs.ToArray(typeof(string)));
        }
        /// <summary>
        /// String array of matched command line options
        /// </summary>
        public String[] matchedOptions()
        {
            if (_matchedSwitches == null) return null;
            ArrayList names = new ArrayList();
            for (int s = 0; s < _matchedSwitches.Count; s++)
                names.Add(((Option)_matchedSwitches[s]).Name);
            return ((String[])names.ToArray(typeof(string)));
        }
        /// <summary>
        /// String array of not identified command line options
        /// </summary>
        public String[] invalidArgs()
        {
            if (_invalidArgs == null) return null;
            return ((String[])_invalidArgs.ToArray(typeof(string)));
        }
        /// <summary>
        /// Create usage: A formated help message with a list of registered command line options.
        /// </summary>
        public string HelpMessage()
        {
            const string indent = "  ";
            int ind = indent.Length;
            const int spc = 3;
            int len = 0;
            foreach (Option s in SwitchesStore)
            {
                foreach (string name in s.Names)
                {
                    int nlen = name.Length;
                    if (s.needsValue) nlen += (" [..]").Length;
                    len = Math.Max(len, nlen);
                }
            }
            string help = "\nCommand line options are:\n\n";
            bool req = false;
            foreach (Option s in SwitchesStore)
            {
                string line = indent + s.Names[0];
                if (s.needsValue) line += " [..]";
                while (line.Length < len + spc + ind)
                    line += " ";
                if (s.isRequired)
                {
                    line += "(*) ";
                    req = true;
                }
                line += s.Description;

                help += line + "\n";
                if (s.Aliases != null && s.Aliases.Length > 0)
                {
                    foreach (string name in s.Aliases)
                    {
                        line = indent + name;
                        if (s.needsValue) line += " [..]";
                        help += line + "\n";
                    }
                }
                help += "\n";
            }
            if (req) help += "(*) Required.\n";
            return help;
        }
        /// <summary>
        /// Print debug information of this CMDLineParser to the system console. 
        /// </summary>
        public void Debug()
        {
            Console.WriteLine();
            Console.WriteLine("\n------------- DEBUG CMDLineParser -------------\n");
            if (SwitchesStore != null)
            {
                Console.WriteLine("There are {0} registered switches:", SwitchesStore.Count);
                foreach (Option s in SwitchesStore)
                {
                    Console.WriteLine("Command : {0} : [{1}]", s.Names[0], s.Description);
                    Console.Write("Type    : {0} ", s.Type);
                    Console.WriteLine();

                    if (s.Aliases != null)
                    {
                        Console.Write("Aliases : [{0}] : ", s.Aliases.Length);
                        foreach (string alias in s.Aliases)
                            Console.Write(" {0}", alias);
                        Console.WriteLine();
                    }
                    Console.WriteLine("Required: {0}", s.isRequired);

                    Console.WriteLine("Value is: {0} \n",
                        s.Value != null ? s.Value : "(Unknown)");
                }
            }
            else
            {
                Console.WriteLine("There are no registered switches.");
            }

            if (_matchedSwitches != null)
            {

                if (_matchedSwitches.Count > 0)
                {
                    Console.WriteLine("\nThe following switches were found:");
                    foreach (Option s in _matchedSwitches)
                    {
                        Console.WriteLine("  {0} Value:{1}",
                            s.Name != null ? s.Name : "(Unknown)",
                            s.Value != null ? s.Value : "(Unknown)");
                    }
                }
                else
                {
                    Console.WriteLine("\nNo Command Line Options detected.");
                }
            }
            Console.Write(InvalidArgsMessage());
            Console.WriteLine("\n----------- DEBUG CMDLineParser END -----------\n");
        }

        private string InvalidArgsMessage()
        {
            const string indent = "  ";
            string msg = "";
            if (_invalidArgs != null)
            {
                msg += "\nThe following args contain invalid (unknown) options:";
                if (_invalidArgs.Count > 0)
                {
                    foreach (string s in _invalidArgs)
                    {
                        msg += "\n" + indent + s;
                    }
                }
                else
                {
                    msg += "\n" + indent + "- Non -";
                }
            }
            return msg + "\n";
        }
        /// <summary>
        /// Interface supporting parsing and setting of string parameter Values to objects
        /// </summary>
        private interface IParsableOptionParameter
        {
            /// <summary>
            /// parse string parameter to convert to an object
            /// </summary>
            /// <param name="parameter"></param>
            /// <returns>an object</returns>
            object parseValue(string parameter);
            /// <summary>
            /// Get or Set the value
            /// </summary>
            object Value { get; set; }
        }
        /// <summary>
        /// A comand line Option: A switch or a string parameter option.
        /// </summary>
        /// <remarks> Use AddBoolSwitch(..) or  AddStringParameter(..) (Factory) 
        /// Methods to create and store a new parsable 'CMDLineParser.Option'. 
        /// </remarks>
        public class Option : IParsableOptionParameter
        {
            private System.Collections.ArrayList _Names = null;
            private bool _matched = false;
            private string _name = "";
            private string _description = "";
            private object _value = null;
            private System.Type _switchType;
            private bool _needsVal = false;
            private bool _required = false;

            private Option() { }

            public Option(string name, string description, System.Type type, bool hasval, bool required)
            {
                _switchType = type;
                _needsVal = hasval;
                _required = required;
                Initialize(name, description);
            }

            private void Initialize(string name, string description)
            {
                _name = name;
                _description = description;
                _Names = new System.Collections.ArrayList();
                _Names.Add(name);
            }

            public void AddAlias(string alias)
            {
                if (!CMDLineParser.isASwitch(alias))
                    throw new CMDLineParserException("Invalid Option:'" + alias + "'::" + IS_NOT_A_SWITCH_MSG);

                if (_Names == null)
                    _Names = new System.Collections.ArrayList();
                _Names.Add(alias);
            }

            public void Clear()
            {
                _matched = false;
                _value = null;
            }

            //getters and setters
            public string Name
            {
                get { return _name; }
                set { _name = value; }
            }

            public string Description
            {
                get { return _description; }
                set { _description = value; }
            }
            /// <summary>
            /// Object Type of Option Value (e.g. typeof(int))
            /// </summary>
            public System.Type Type
            {
                get { return _switchType; }
            }

            public bool needsValue
            {
                get { return _needsVal; }
            }

            public bool isRequired
            {
                get { return _required; }
                set { _required = value; }
            }
            /// <summary>
            /// set to 'true' if Option has been detected on the command line
            /// </summary>
            public bool isMatched
            {
                get { return _matched; }
                set { _matched = value; }
            }

            public string[] Names
            {
                get { return (_Names != null) ? (string[])_Names.ToArray(typeof(string)) : null; }
            }

            public string[] Aliases
            {
                get
                {
                    if (_Names == null) return null;
                    ArrayList list = new ArrayList(_Names);
                    list.RemoveAt(0); //remove 'name' (first element) from the list to leave aliases only
                    return (string[])list.ToArray(typeof(string));
                }
            }

            public object Value
            {
                get { return (_value); }
                set { _value = value; }
            }

            #region IParsableOptionParameter Member
            /// <summary>
            /// Default implementation of parseValue: 
            /// Subclasses should override this method to provide a method for converting
            /// the parsed string parameter to its Object type
            /// </summary>
            /// <param name="parameter"></param>
            /// <returns>converted value</returns>
            /// <see cref="NumberOption.parseValue"/>
            public virtual object parseValue(string parameter)
            {
                //set string parameter
                if (Type == typeof(string) && needsValue == true)
                {
                    return (parameter);//string needs no parsing (conversion) to string...
                }
                else
                {
                    //throw Exception when parseValue has not been implemented by a subclass 
                    throw new Exception("Option is missing an method to convert the value.");
                }
            }
            #endregion
        }

        /// <summary>
        /// An command line option with a Number parameter.
        /// </summary>
        ///<remarks>
        /// To avoid unpredictable results on plattforms that use different 'Culture' settings 
        /// the default is set to 'invariant Culture' and parseDecimalSeperator=true;
        /// The number format can be changed for each CMDLineParser.NumberOption individually for
        /// more strict parsing.
        ///</remarks>
        public class NumberOption : Option
        {
            /// <summary>
            /// If set to true the parser tries to detect and set the Decimalseparetor ("." or ",")
            /// automaticly. (default=true)
            /// </summary>
            public bool parseDecimalSeperator = true;

            private NumberFormatInfo _numberformat = null;
            private NumberStyles _numberstyle;

            /// <summary>
            /// Get or Set the NumberFormat Information for parsing the parameter 
            /// </summary>
            public NumberFormatInfo NumberFormat
            {
                get { return _numberformat; }
                set { _numberformat = value; }
            }
            /// <summary>
            /// Get or Set the NumberStyle for parsing the parameter 
            /// </summary>
            public NumberStyles NumberStyle
            {
                get { return _numberstyle; }
                set { _numberstyle = value; }
            }

            public NumberOption(string name, string description, System.Type type, bool hasval, bool required)
                : base(name, description, type, hasval, required)
            {
                //use invariant Culture as default
                _numberformat = (new CultureInfo("", false)).NumberFormat;
            }

            public override object parseValue(string parameter)
            {
                // int parameter
                if (base.Type == typeof(int))
                {
                    return parseIntValue(parameter);
                }
                // double parameter
                if (base.Type == typeof(double))
                {
                    return parseDoubleValue(parameter);
                }
                throw new ParameterConversionException("Invalid Option Type: " + base.Type);
            }
            //
            private int parseIntValue(string parameter)
            {
                try
                {
                    return (System.Int32.Parse(parameter, _numberstyle, _numberformat));
                }
                catch (Exception e)
                {
                    throw new ParameterConversionException("Invalid Int Parameter:" + parameter + " - " + e.Message);
                }
            }
            //
            private double parseDoubleValue(string parameter)
            {
                if (parseDecimalSeperator) SetIdentifiedDecimalSeperator(parameter);
                try
                {
                    return (System.Double.Parse(parameter, _numberstyle, _numberformat));
                }
                catch (Exception e)
                {
                    throw new ParameterConversionException("Invalid Double Parameter:" + parameter + " - " + e.Message);
                }
            }
            //
            private void SetIdentifiedDecimalSeperator(string parameter)
            {
                if (_numberformat.NumberDecimalSeparator == "." && parameter.Contains(",") && !(parameter.Contains(".")))
                {
                    _numberformat.NumberDecimalSeparator = ",";
                    if (_numberformat.NumberGroupSeparator == ",") _numberformat.NumberGroupSeparator = ".";
                }
                else
                {
                    if (_numberformat.NumberDecimalSeparator == "," && parameter.Contains(".") && !(parameter.Contains(",")))
                    {
                        _numberformat.NumberDecimalSeparator = ".";
                        if (_numberformat.NumberGroupSeparator == ".") _numberformat.NumberGroupSeparator = ",";
                    }
                }
            }
        }
        /// <summary>
        /// Command line parsing Exception.
        /// </summary>
        public class CMDLineParserException : Exception
        {
            public CMDLineParserException(string message)
                : base(message)
            { }
        }
        /// <summary>
        /// Thrown when required option was not detected
        /// </summary>
        public class MissingRequiredOptionException : CMDLineParserException
        {
            public MissingRequiredOptionException(string message)
                : base(message)
            { }
        }
        /// <summary>
        /// Thrown when invalid (not registered) options have been detected
        /// </summary>
        public class InvalidOptionsException : CMDLineParserException
        {
            public InvalidOptionsException(string message)
                : base(message)
            { }
        }
        /// <summary>
        /// Thrown when duplicate option was detected
        /// </summary>
        public class DuplicateOptionException : CMDLineParserException
        {
            public DuplicateOptionException(string message)
                : base(message)
            { }
        }
        /// <summary>
        /// Thrown when parameter value conversion to specified type failed 
        /// </summary>
        public class ParameterConversionException : CMDLineParserException
        {
            public ParameterConversionException(string message)
                : base(message)
            { }
        }
    }

}
