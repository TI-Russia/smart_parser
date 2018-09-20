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
            LogManager.Shutdown();

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
            BasicConfigurator.Configure(new IAppender[] { appender, consoleAppender });
            //BasicConfigurator.Configure(consoleAppender);


            log = LogManager.GetLogger("Smart.Parser");
        }

        public static void SetupLogFile(string logFileName)
        {
            XmlConfigurator.Configure();
            log4net.Repository.Hierarchy.Hierarchy h =
            (log4net.Repository.Hierarchy.Hierarchy)LogManager.GetRepository();
            foreach (IAppender a in h.Root.Appenders)
            {
                if (a is FileAppender)
                {
                    FileAppender fa = (FileAppender)a;

                    fa.AppendToFile = false;
                    fa.File = logFileName;
                    fa.ActivateOptions();
                    break;
                }
            }
        }

        public enum LogLevel
        {
            Debug = 0,
            Info,
            Error
        };
        static public void SetLoggingLevel(LogLevel level)
        {
            log4net.Core.Level[] levels = { log4net.Core.Level.Debug, log4net.Core.Level.Info, log4net.Core.Level.Error };
            ((log4net.Repository.Hierarchy.Hierarchy) LogManager.GetRepository()).Root.Level = levels[(int)level];
            ((log4net.Repository.Hierarchy.Hierarchy) LogManager.GetRepository()).RaiseConfigurationChanged(EventArgs.Empty);
        }
        public static ILog Log { get { return log; } }

        private static ILog log;
        static public void Info(string info, params object[] par)
        {
            log.Info(String.Format(info, par));
        }
        static public void Info(string info)
        {
            log.Info(String.Format(info));
        }
        static public void Error(string info, params object[] par)
        {
            string message = String.Format(info, par);
            log.Error(message);
            Errors.Add(message);
        }

        public static List<string> Errors { get; } = new List<string>();
    }
}
