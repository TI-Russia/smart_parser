using log4net;
using log4net.Appender;
using log4net.Config;
using log4net.Layout;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Parser.Lib
{
    public class Logger
    {
        public static void Setup(string logFileName = "smart_parser.log")
        {
            var layout = new PatternLayout(@"%date %-5level %message%newline");
            var appender = new RollingFileAppender
            {
                File = logFileName,
                Layout = layout
            };
            var consoleAppender = new ConsoleAppender();
            consoleAppender.Layout = new log4net.Layout.PatternLayout(@"%date %-5level %message%newline");
            consoleAppender.Threshold = log4net.Core.Level.Debug;
            consoleAppender.ActivateOptions();
            var appender2 = new ColoredConsoleAppender();


            layout.ActivateOptions();
            appender.ActivateOptions();
            BasicConfigurator.Configure(new IAppender[]{ appender, consoleAppender });
            //BasicConfigurator.Configure(consoleAppender);


            log = LogManager.GetLogger("Smart.Parser");
        }

        private static ILog log;
        static public void Info(string info) { log.Info(info); }
    }
}
